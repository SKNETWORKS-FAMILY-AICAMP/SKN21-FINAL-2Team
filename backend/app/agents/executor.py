import os
import base64
import math
import mimetypes
import re
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.state import TravelState, get_effective_user_input
from app.agents.models.output import IntentType, IntentLocation
from app.agents.prompts.executor_prompt import EXECUTOR_PROMPT, EXECUTOR_TRIP_PLANNING_PROMPT, EXECUTOR_AUTO_START_PROMPT, EXECUTOR_MISSING_INFO_PROMPT, EXECUTOR_GENERAL_PROMPT
from app.utils.common import build_naver_map_url, dprint, dpprint
from app.models.enums import LanguageType

_LANGUAGE_INSTRUCTION: dict[str, str] = {
    LanguageType.en: "IMPORTANT: Respond entirely in English. However, keep all place names in their original Korean.",
    LanguageType.ko: "",
    LanguageType.ja: "IMPORTANT: 必ず日本語で回答してください。ただし、장소명はすべて元の韓国語表記のまま維持してください。",
    LanguageType.zh: "IMPORTANT: 请务必用中文回答。但是，所有장소명必须保持原始韩文不变。",
}

def _get_language_suffix(language) -> str:
    key = language if isinstance(language, LanguageType) else LanguageType(language) if language else LanguageType.ko
    return _LANGUAGE_INSTRUCTION.get(key, "")
from app.core.llm_streaming import collect_streamed_text
from app.utils.place_id import get_contenttypeid
from app.utils.geocoder import GeoCoder
from app.agents.models.state import IntentSlots
from app.agents.models.place import PlaceInfo

def _extract_place_names_from_answer(answer_text: str) -> list[str]:
    """
    답변 텍스트에서 장소명 추출.
    """
    link_names = re.findall(r"\[([^\]]+)\]\(https?://[^)]+\)", answer_text)
    bold_names = re.findall(r"\*\*([^*]+)\*\*", answer_text)
    # 링크명 우선, 볼드명은 보완 (중복 제거는 dict.fromkeys로)
    return list(dict.fromkeys(n.strip() for n in (link_names + bold_names) if n.strip()))


def _normalize_place_name(value: str) -> str:
    value = (value or "").strip().lower()
    return re.sub(r"\s+", "", value)


def _extract_previously_recommended_place_names(messages: List[BaseMessage]) -> list[str]:
    names: list[str] = []
    for message in messages or []:
        if not isinstance(message, AIMessage):
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str):
            names.extend(_extract_place_names_from_answer(content))
    return list(dict.fromkeys(name for name in names if name))


def _build_candidate_place_pairs(candidates: List[Dict[str, Any]]) -> List[tuple[Dict[str, Any], PlaceInfo]]:
    """
    유효한 candidate만 PlaceInfo와 함께 반환한다.
    """
    result: list[tuple[Dict[str, Any], PlaceInfo]] = []
    for c in (candidates or []):
        payload = c.get("payload", {}) or {}
        name = (payload.get("place") or payload.get("title") or payload.get("name") or "").strip()
        address = (payload.get("addr") or payload.get("road_address") or "").strip()

        # 좌표: mapx/mapy 우선, 없으면 geo.lon/geo.lat 폴백
        geo = payload.get("geo") or {}
        longitude = payload.get("mapx") or geo.get("lon")
        latitude = payload.get("mapy") or geo.get("lat")

        if not name or not address or not longitude or not latitude:
            continue

        result.append((
            c,
            PlaceInfo(
                contenttypeid=get_contenttypeid(c) or "",
                name=name,
                address=address,
                image_path=payload.get("image") or "",
                map_url=build_naver_map_url(name, float(latitude), float(longitude)),
                longitude=float(longitude),
                latitude=float(latitude),
            ),
        ))
    return result


def _collect_recommended_places(
    answer_text: str,
    places: List[PlaceInfo],
    minimum_count: int = 2,
    maximum_count: int = 3,
    deprioritized_names: List[str] | None = None,
) -> List[PlaceInfo]:
    """답변 텍스트에 실제로 언급된 장소만 반환한다. 미언급 장소는 절대 포함하지 않는다."""
    if not places:
        return []

    normalized_to_place = {
        _normalize_place_name(place.name): place
        for place in places
        if place.name
    }

    recommended: list[PlaceInfo] = []
    for name in _extract_place_names_from_answer(answer_text):
        place = normalized_to_place.get(_normalize_place_name(name))
        if place and all(place.name != existing.name for existing in recommended):
            recommended.append(place)

    return recommended[:maximum_count]


def _answer_mentions_unknown_places(answer_text: str, places: List[PlaceInfo]) -> bool:
    """답변에서 추출한 장소명 중 과반수가 후보군 밖이면 True.
    ONE unknown(오탈자·약칭 등)이 있어도 나머지가 알려진 장소면 허용한다."""
    extracted_names = _extract_place_names_from_answer(answer_text)
    if not extracted_names:
        return False

    normalized_known_names = {
        _normalize_place_name(place.name)
        for place in places
        if place.name
    }
    unknown_count = sum(
        1 for name in extracted_names
        if _normalize_place_name(name) not in normalized_known_names
    )
    # 과반수가 모르는 장소일 때만 할루시네이션으로 판단
    return unknown_count > len(extracted_names) / 2


def _build_minimum_recommendation_suffix(
    recommended_places: List[PlaceInfo],
    candidates: List[Dict[str, Any]],
) -> str:
    if not recommended_places:
        return ""

    intro_by_name: dict[str, str] = {}
    for candidate in candidates or []:
        payload = candidate.get("payload", {}) or {}
        name = (payload.get("place") or payload.get("title") or payload.get("name") or "").strip()
        if not name:
            continue
        introduction = (
            candidate.get("introduction")
            or payload.get("introduction")
            or payload.get("llm_text")
            or ""
        )
        intro_by_name[_normalize_place_name(name)] = str(introduction).strip()

    lines = ["", "추천드릴 곳은 다음 2~3곳입니다."]
    for place in recommended_places:
        intro = intro_by_name.get(_normalize_place_name(place.name), "")
        summary = intro[:120].strip()
        if len(intro) > 120:
            summary += "..."
        if place.map_url and place.map_url != "Unknown":
            place_label = f"[{place.name}]({place.map_url})"
        else:
            place_label = place.name
        detail_parts = [part for part in [place.address, summary] if part]
        if detail_parts:
            lines.append(f"{place_label}은 {', '.join(detail_parts)} 기준으로 추천드립니다.")
        else:
            lines.append(f"{place_label}을 추천드립니다.")
    return "\n\n".join(lines)


def _build_place_context(candidates: List[Dict[str, Any]]) -> tuple[list[PlaceInfo], str, str]:
    """candidates 리스트를 LLM에 전달할 컨텍스트 문자열로 변환.
    Returns: (place_info_list, place_context_str, candidate_names_str)
    """
    if not candidates:
        return [], "", "없음"

    candidate_place_pairs = _build_candidate_place_pairs(candidates)
    lines = ["## 검색된 장소 정보"]
    name_lines: list[str] = []
    for i, (c, info) in enumerate(candidate_place_pairs, 1):
        payload = c.get("payload", {})

        # 소개글: 우선순위 순서대로 첫 번째 non-empty 값 사용
        introduction = (
            payload.get("llm_text") or payload.get("introduction")
            or c.get("introduction") or payload.get("summary") or payload.get("description") or ""
        )
        tags = payload.get("tags") or []
        start_d = payload.get("start_date", "")
        end_d   = payload.get("end_date", "")

        # JSON 대신 사람이 읽기 쉬운 구조화 텍스트로 변환 (LLM이 그대로 출력하는 현상 방지)
        block = [f"### {i}. {info.name}"]
        block.append(f"- 주소: {info.address}")
        if info.map_url:
            block.append(f"- 지도: {info.map_url}")
        if introduction:
            block.append(f"- 소개: {introduction}")
        if tags:
            block.append(f"- 태그: {', '.join(str(t) for t in tags)}")

        # payload 필드 → 한국어 레이블 매핑. 순서가 곧 컨텍스트 출력 순서.
        # 필드 추가/제거 시 이 딕셔너리만 수정하면 됨.
        _PAYLOAD_FIELD_LABELS: dict[str, str] = {
            "usetime":    "이용시간",
            "restdate":   "휴무일",
            "parking":    "주차",
            "tel":        "전화",
            "subway_info": "대중교통",
            "website":    "웹사이트",
            "fee":        "입장료",
            "period":     "기간",
            "pet_raw":    "반려동물",
        }

        # 매핑 테이블 기반 단순 필드 처리
        for field, label in _PAYLOAD_FIELD_LABELS.items():
            value = payload.get(field, "")
            if value:
                block.append(f"- {label}: {value}")

        # 날짜 범위는 두 필드를 합쳐야 하므로 별도 처리
        if start_d or end_d:
            block.append(f"- 일정: {start_d} ~ {end_d}")

        lines.append("\n".join(block))
        name_lines.append(f"{i}. {info.name}")

    candidate_names_str = "\n".join(name_lines) if name_lines else "없음"
    return [info for _, info in candidate_place_pairs], "\n\n".join(lines), candidate_names_str


def _build_planner_itinerary_str(itinerary: List[Dict[str, Any]]) -> str:
    """planner가 생성한 raw itinerary를 executor에 전달할 backbone 텍스트로 변환."""
    if not itinerary:
        return "없음"

    # day별로 그룹핑 (입력 순서 유지)
    days: dict[int, list] = {}
    for item in itinerary:
        day = int(item.get("day", 1) or 1)
        days.setdefault(day, []).append(item)

    lines = []
    for day in sorted(days.keys()):
        lines.append(f"{day}일차:")
        for item in days[day]:
            time_slot = item.get("time_slot", "")
            activity = item.get("activity", "")
            search_query = item.get("search_query", "")
            prefix = f"  - [{time_slot}] " if time_slot else "  - "
            lines.append(f"{prefix}{activity} (장소 키워드: {search_query})")
    return "\n".join(lines)


def _build_itinerary_context(candidates: List[Dict[str, Any]]) -> str:
    """TRIP_PLANNING일 때, itinerary 연결 정보가 있는 candidates를 일정 형태로 구성"""
    has_itinerary_info = any(c.get("itinerary_day") for c in candidates)
    if not has_itinerary_info:
        return ""

    # 일차/시간대별로 그룹핑
    schedule = {}
    for c in candidates:
        day = c.get("itinerary_day", 1)
        time_slot = c.get("itinerary_time_slot", "")
        activity = c.get("itinerary_activity", "")
        key = (day, time_slot)
        if key not in schedule:
            schedule[key] = {"activity": activity, "places": []}
        schedule[key]["places"].append(c)

    lines = ["## 일정별 검색 결과"]
    for (day, time_slot), info in sorted(schedule.items()):
        lines.append(f"\n### {day}일차 - {time_slot}")
        lines.append(f"활동: {info['activity']}")
        for p in info["places"]:
            payload = p.get("payload", {}) if "payload" in p else p
            name = payload.get("place") or payload.get("title") or payload.get("name") or p.get("title", "")
            query = name or payload.get("addr") or payload.get("road_address") or p.get("address", "")
            
            try:
                lat = float(payload.get("mapy") or p.get("lat") or 0.0)
                lon = float(payload.get("mapx") or p.get("lon") or 0.0)
            except (TypeError, ValueError):
                lat, lon = 0.0, 0.0

            map_url = build_naver_map_url(query, lat, lon)
            lines.append(f"- [{name}]({map_url})" if map_url else f"- {name}")

    return "\n".join(lines)


_SEOUL_BBOX = {"lat_min": 37.413, "lat_max": 37.701, "lon_min": 126.734, "lon_max": 127.269}


def _in_seoul_bbox(lat: float, lon: float) -> bool:
    return (
        _SEOUL_BBOX["lat_min"] <= lat <= _SEOUL_BBOX["lat_max"]
        and _SEOUL_BBOX["lon_min"] <= lon <= _SEOUL_BBOX["lon_max"]
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_image_data_url(image_path: str) -> str:
    """이미지 경로가 로컬 파일이면 base64 데이터 URL로 변환, 아니면 그대로 반환"""
    if not image_path:
        return ""
    
    if image_path.startswith(("http://", "https://", "data:image")):
        return image_path
    
    # 로컬 파일 경로인 경우
    if os.path.exists(image_path):
        try:
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/jpeg"
            
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime_type};base64,{encoded}"
        except Exception as e:
            dprint(f"[Executor] Failed to encode local image {image_path}: {e}")
            return image_path
            
    return image_path


def _build_missing_context(missing_slots: List[str]) -> str:
    """missing_slots가 있으면, 해당 슬롯에 대한 질문을 생성"""
    if not missing_slots:
        return ""
    
    lines = ["## 추가 정보 필요"]
    for slot in missing_slots:
        lines.append(f"- {slot}")
    
    return "\n".join(lines)


async def _build_location_context(
    slots: Optional[IntentSlots],
    input_address: Optional[str] = None,
) -> str:
    # 사용자 위치 컨텍스트 구성 (geocoder_node에서 미리 reverse geocoding된 주소 사용)
    user_location_context = ""

    if input_address:
        user_location_context = f"- 사용자 현재 위치: {input_address}"

    if slots and slots.location and slots.location.name:
        address = ""
        if slots.location.lat and slots.location.lon:
            address = await GeoCoder.get_address(slots.location.lat, slots.location.lon)
        user_location_context += f"\n- 사용자 관심 장소: {slots.location.name} ({address})"

    return user_location_context


async def executor_node(state: TravelState, config: RunnableConfig | None = None):
    """
    최종 답변 생성
    """
    dprint("--- Executor Agent ---")
    try:
        await adispatch_custom_event("pipeline_step", {"node": "executor", "status": "start"})
    except RuntimeError:
        pass

    candidates = state.get("candidates")
    candidate_pool = state.get("candidate_pool")
    user_input = get_effective_user_input(state)
    input_tags = state.get("input_tags", [])
    messages = state.get("messages", [])[-6:]
    prefs_info = state.get("prefs_info", "")
    primary_intent = state.get("primary_intent")
    slots: Optional[IntentSlots] = state.get("slots")
    image_path = state.get("input_image")
    input_lat = state.get("input_lat")
    input_lon = state.get("input_lon")
    follow_up_questions = state.get("follow_up_questions", [])
    previous_recommendations = _extract_previously_recommended_place_names(messages)

    # ====================================
    # 장소 정보 리스트가 없으면 Tavily 검색으로 보완
    if not candidate_pool:
        candidate_pool = candidates

    if not slots:
        slots = IntentSlots(location=IntentLocation(name="서울", lat=0, lon=0))

    web_context = None
    place_context = None
    itinerary_context = None
    fallback_places = []
    candidate_places = []
    candidate_names = "없음"
    if not candidates:
        # web_search_node가 미리 검색해 놓은 결과를 state에서 읽는다.
        dprint("[Executor] No candidates — reading web_search results from state")
        fallback_places = state.get("web_search_places") or []
        web_context = state.get("web_search_context") or ""
        if not fallback_places:
            dprint("[Executor] web_search_places empty — no fallback results available")
    else:
        dprint(f"candidate_pool : {len(candidate_pool)}")
        dprint(f"candidates : {len(candidates)}")
        dpprint(candidates)

        # 컨텍스트 구성
        candidate_places, place_context, candidate_names = _build_place_context(candidates)
        itinerary_context = _build_itinerary_context(candidates) if primary_intent == IntentType.TRIP_PLANNING else None
    # ====================================


    # 슬롯 정보 텍스트 =======================
    if slots and slots.categories:
        prefs_info += f"\n- 사용자 관심 카테고리 : {', '.join(slots.categories)}"

    # 위치 정보 ============================
    # 사용자 위치 컨텍스트 구성 (GPS 위치 우선, 없으면 slots.location 사용)
    location_context = await _build_location_context(slots, input_address=state.get("input_address"))


    # HumanMessage 구성 (멀티모달 지원)
    content_blocks = []
    
    if image_path:
        # 텍스트가 없어도 이미지가 있으면 안내 문구 추가
        if len(user_input) == 0:
            user_input = "사용자가 이미지를 보냈습니다. 이 이미지를 분석해서 어울리는 장소를 추천해주세요."
        content_blocks.append({"type": "text", "text": user_input})

        image_url = _get_image_data_url(image_path)
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
    else:
        content_blocks.append({"type": "text", "text": f"{user_input}"})
    
    # content_blocks가 비어있으면(텍스트도 없고 이미지도 없음) 처리
    if not content_blocks:
          content_blocks.append({"type": "text", "text": "사용자 입력이 없습니다."})

    if primary_intent == IntentType.TRIP_PLANNING:
        raw_itinerary = state.get("itinerary") or []
        planner_itinerary_str = _build_planner_itinerary_str(raw_itinerary)
        if state.get("is_auto_start"):
            # auto_start: retriever 건너뜀 → 가벼운 초안 응답 전용 프롬프트
            system_prompt = EXECUTOR_AUTO_START_PROMPT.format(
                prefs_info=prefs_info,
                planner_itinerary=planner_itinerary_str,
            )
        else:
            system_prompt = EXECUTOR_TRIP_PLANNING_PROMPT.format(
                prefs_info=prefs_info,
                location_context=location_context,
                candidate_names=candidate_names,
                place_context=place_context or "없음",
                itinerary_context=itinerary_context or "없음",
                planner_itinerary=planner_itinerary_str,
                follow_up_questions=follow_up_questions,
            )
    else:
        system_prompt = EXECUTOR_PROMPT.format(
            prefs_info=prefs_info,
            location_context=location_context,
            candidate_names=candidate_names,
            place_context=place_context or "없음",
            itinerary_context=itinerary_context or "없음",
            web_context=web_context or "없음",
            follow_up_questions=follow_up_questions,
            previous_recommendations=", ".join(previous_recommendations) if previous_recommendations else "없음",
        )

    lang_suffix = _get_language_suffix(state.get("language"))
    if lang_suffix:
        system_prompt += f"\n\n{lang_suffix}"

    # state의 messages에는 이미 현재 턴 HumanMessage가 포함되어 있음(chat API에서 invoke 시 추가).
    # 이미지 등 멀티모달을 위해 현재 턴은 content_blocks로 한 번만 보내고, 과거 대화만 history로 사용.
    history = messages[:-1] if messages else []
    prompt_messages = [SystemMessage(content=system_prompt), *history, HumanMessage(content=content_blocks)]
    
    # astream을 사용하여 토큰 단위 스트리밍 (custom event로 SSE 레이어에 전달)
    full_content = await collect_streamed_text(
        temperature=0.2,
        prompt_value=prompt_messages,
        config=config,
    )

    cleaned_answer = full_content.strip()
    dprint(f"[Executor] Answer length: {len(cleaned_answer)}")

    # PlaceInfo 목록 구성 (Qdrant path: candidates 기반, Tavily path: 답변 파싱 + 지오코딩)
    if candidates:
        place_info_list = _collect_recommended_places(
            cleaned_answer,
            candidate_places,
            deprioritized_names=previous_recommendations,
        )
        if _answer_mentions_unknown_places(cleaned_answer, candidate_places):
            place_info_list = []
    else:
        place_info_list = _collect_recommended_places(
            cleaned_answer,
            fallback_places,
            deprioritized_names=previous_recommendations,
        )

    dprint(f"[Executor] place_info_list: {len(place_info_list)} items")

    return {
        "messages": AIMessage(content=cleaned_answer),
        "answer": cleaned_answer,
        "place_info_list": place_info_list,
    }


async def executor_missing_node(state: TravelState, config: RunnableConfig | None = None):
    """
    여행 계획에서 부족한 정보를 재질문하는 node
    """
    dprint("--- Executor Missing Agent ---")
    try:
        await adispatch_custom_event("pipeline_step", {"node": "executor_missing", "status": "start"})
    except RuntimeError:
        pass

    # missing_slots가 있으면 (planner의 재질문) 바로 반환
    missing_slots = state.get("missing_slots", [])
    user_input = get_effective_user_input(state)
    messages = state.get("messages", [])[-6:]
    prefs_info = state.get("prefs_info", "")
    slots = state.get("slots")
    follow_up_questions = state.get("follow_up_questions", [])

    dprint(f"[Executor] Missing slots: {missing_slots}")
    missing_context = _build_missing_context(missing_slots)

    human_message = HumanMessage(content="여행 계획을 위한 추가 정보가 필요합니다. 아래 정보를 참고하여 질문해주세요.")

    lang_suffix = _get_language_suffix(state.get("language"))
    missing_system_prompt = EXECUTOR_MISSING_INFO_PROMPT + (f"\n\n{lang_suffix}" if lang_suffix else "")

    prompt = ChatPromptTemplate.from_messages([
        ("system", missing_system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        human_message
    ])

    prompt_value = prompt.invoke({
        "messages": messages,
        "user_input": user_input,
        "slots_info": slots,
        "prefs_info": prefs_info,
        "missing_info": missing_context,
        "follow_up_questions": follow_up_questions,
    })

    full_content = await collect_streamed_text(
        temperature=0.5,
        prompt_value=prompt_value,
        config=config,
    )

    answer = full_content.strip()
    dprint(f"[Executor] Answer generated (length={len(answer)})")

    return {"messages": AIMessage(content=answer), "answer": answer}


async def executor_general_node(state: TravelState, config: RunnableConfig | None = None):
    """
    일상 대화 node
    """
    dprint("--- Executor General Agent ---")
    try:
        await adispatch_custom_event("pipeline_step", {"node": "executor_general", "status": "start"})
    except RuntimeError:
        pass

    user_input = get_effective_user_input(state)
    messages = state.get("messages", [])[-6:]
    prefs_info = state.get("prefs_info", "")
    slots = state.get("slots")
    follow_up_questions = state.get("follow_up_questions", [])

    # 슬롯 정보 텍스트
    if slots and slots.categories:
        prefs_info += f"\n- 사용자 관심 카테고리 : {', '.join(slots.categories)}"

    location_context = await _build_location_context(slots, input_address=state.get("input_address"))

    lang_suffix = _get_language_suffix(state.get("language"))
    general_system_prompt = EXECUTOR_GENERAL_PROMPT + (f"\n\n{lang_suffix}" if lang_suffix else "")

    prompt = ChatPromptTemplate.from_messages([
        ("system", general_system_prompt),
    ])

    prompt_value = prompt.invoke({
        "messages": messages,
        "user_input": user_input,
        "location_context": location_context,
        "prefs_info": prefs_info,
        "follow_up_questions": follow_up_questions,
    })

    full_content = await collect_streamed_text(
        temperature=0.7,
        prompt_value=prompt_value,
        config=config,
    )

    answer = full_content.strip()
    dprint(f"[Executor General] Answer generated (length={len(answer)})")

    return {"messages": AIMessage(content=answer), "answer": answer}
