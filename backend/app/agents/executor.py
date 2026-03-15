import urllib.parse
import os
import base64
import mimetypes
import concurrent.futures
import math
import re
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.agents.models.state import TravelState, get_effective_user_input
from app.agents.models.output import IntentType, PlaceInfo
from app.agents.prompts.executor_prompt import EXECUTOR_PROMPT, EXECUTOR_MISSING_INFO_PROMPT, EXECUTOR_GENERAL_PROMPT
from app.core.llm_factory import LLMFactory
from app.utils.common import parse_payload, getattr_safe
from app.core.llm_streaming import collect_streamed_text
from app.utils.place_id import get_place_id
from app.utils.config import TAVILY_IMAGE_SCORE_THRESHOLD

def _in_seoul_bbox(lat: float, lng: float) -> bool:
    # 서울 행정 경계 bounding box
    _SEOUL_BBOX = {
        "lat_min": 37.413,
        "lat_max": 37.701,
        "lng_min": 126.734,
        "lng_max": 127.269,
    }
    return (
        _SEOUL_BBOX["lat_min"] <= lat <= _SEOUL_BBOX["lat_max"]
        and _SEOUL_BBOX["lng_min"] <= lng <= _SEOUL_BBOX["lng_max"]
    )

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 WGS84 좌표 간 거리(km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _is_seoul_result(r: Any) -> bool:
    """Tavily 결과 dict에 서울 관련 키워드가 포함되어 있는지 확인."""
    if not isinstance(r, dict):
        return False
    text = " ".join([
        r.get("content", ""),
        r.get("title", ""),
        r.get("url", ""),
    ])
    return "서울" in text or "Seoul" in text or "seoul" in text


def _extract_place_names_from_answer(answer_text: str) -> list[str]:
    """답변 텍스트에서 장소명 추출 (마크다운 링크 → 볼드 텍스트 순)."""
    names = re.findall(r"\[([^\]]+)\]\(https?://[^)]+\)", answer_text)
    if not names:
        names = re.findall(r"\*\*([^*]+)\*\*", answer_text)
    return list(dict.fromkeys(n.strip() for n in names if n.strip()))


def _build_place_info_from_candidates(
    candidates: List[Dict[str, Any]],
    answer_text: str = "",
) -> List[PlaceInfo]:
    """candidates 중 답변에 언급된 장소만 PlaceInfo로 변환."""
    result = []
    for c in (candidates or []):
        payload = c.get("payload", {}) or {}
        name = (payload.get("place") or payload.get("title") or payload.get("name") or "").strip()
        if answer_text and name and name not in answer_text:
            continue
        address = (payload.get("addr") or payload.get("road_address") or "").strip()
        try:
            lng = float(payload.get("mapx") or 0)
            lat = float(payload.get("mapy") or 0)
        except (TypeError, ValueError):
            lng = lat = 0.0
        valid_coords = math.isfinite(lng) and math.isfinite(lat) and not (lng == 0.0 and lat == 0.0)
        if not name or (not address and not valid_coords):
            continue
        result.append(PlaceInfo(
            place_id=get_place_id(c) or "",
            name=name,
            address=address,
            image_path=payload.get("image") or "",
            map_url=payload.get("map_url", ""),
            longitude=lng,
            latitude=lat,
        ))
    return result


_DEFAULT_LOCATION_RADIUS_KM = 3.0


def _build_tavily_place_info(
    answer_text: str,
    images: list[str] | None = None,
    timeout_sec: float = 2.0,
    slots=None,
) -> List[PlaceInfo]:
    """Tavily 기반 답변에서 장소명 파싱 → GeoCoder.search_places()로 좌표/주소 획득."""
    from app.utils.geocoder import GeoCoder, LANDMARK_DICTIONARY

    # slots.location 기반 anchor 좌표 및 반경 결정
    anchor_lat: Optional[float] = None
    anchor_lng: Optional[float] = None
    anchor_radius_km: float = _DEFAULT_LOCATION_RADIUS_KM
    anchor_name: str = ""

    if slots:
        location = getattr_safe(slots, "location")
        if location:
            loc_lat = getattr_safe(location, "lat")
            loc_lng = getattr_safe(location, "long")
            loc_name = (getattr_safe(location, "name") or "").strip()
            if loc_lat and loc_lng:
                anchor_lat = float(loc_lat)
                anchor_lng = float(loc_lng)
                anchor_name = loc_name
                entry = LANDMARK_DICTIONARY.get(loc_name)
                if entry and entry.get("radius_m"):
                    anchor_radius_km = entry["radius_m"] / 1000.0
            elif loc_name:
                try:
                    geocoder_tmp = GeoCoder()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(geocoder_tmp.geocoder, loc_name)
                        geo = future.result(timeout=timeout_sec)
                    if geo:
                        anchor_lat = float(geo.get("lat") or 0) or None
                        anchor_lng = float(geo.get("lng") or geo.get("long") or 0) or None
                        anchor_name = loc_name
                except Exception as e:
                    print(f"[Executor] anchor geocode failed for '{loc_name}': {e}")

    names = _extract_place_names_from_answer(answer_text)
    images = images or []
    result = []
    geocoder = GeoCoder()
    for idx, name in enumerate(names):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(geocoder.search_places, name, 1)
                places = future.result(timeout=timeout_sec)
            if not places:
                continue
            p = places[0]
            lat = float(p.get("lat") or p.get("latitude") or 0)
            lng = float(p.get("lng") or p.get("longitude") or 0)
            address = (p.get("road_address") or p.get("jibun_address") or p.get("address") or "").strip()
            if not name or (not address and not (lat and lng)):
                continue

            if lat and lng and not _in_seoul_bbox(lat, lng):
                print(f"[Executor] Tavily place '{name}' out of Seoul bbox ({lat}, {lng}) — skipped")
                continue

            if anchor_lat and anchor_lng and lat and lng:
                dist_km = _haversine_km(anchor_lat, anchor_lng, lat, lng)
                if dist_km > anchor_radius_km:
                    print(f"[Executor] Tavily place '{name}' too far from '{anchor_name}' ({dist_km:.2f}km > {anchor_radius_km:.2f}km) — skipped")
                    continue

            map_url = f"https://map.naver.com/v5/search/{name}?c=15.00,{lng},{lat},0,dh"
            image_path = images[idx] if idx < len(images) else ""

            result.append(PlaceInfo(
                place_id="",
                name=name,
                address=address,
                image_path=image_path,
                map_url=map_url,
                longitude=lng,
                latitude=lat,
            ))
        except Exception as e:
            print(f"[Executor] Tavily geocode failed for '{name}': {e}")
    return result


def _build_place_context(candidates: List[Dict[str, Any]]) -> str:
    """candidates 리스트를 LLM에 전달할 컨텍스트 문자열로 변환"""
    if not candidates:
        return ""

    lines = ["## 검색된 장소 정보"]
    for i, c in enumerate(candidates, 1):
        payload = c.get("payload", {})
        lat = float(payload.get("mapy", "0"))
        lng = float(payload.get("mapx", "0"))

        # 네이버 지도 링크 생성
        title = payload.get("place") or payload.get("title") or ""
        contentid = get_place_id(c) or ""
        
        if title:
            encoded = urllib.parse.quote(title)
            payload['map_url'] = f"https://map.naver.com/v5/search/{encoded}?c=15.00,{lng},{lat},0,dh"

        map_url = payload.get("map_url", "Unknown")

        # payload에서 빈값/불필요 필드 제거 후 JSON string
        payload_str = parse_payload(payload)

        line = (
            f"{i}. (ID: {contentid}) / 지도링크: {map_url}\n"
            f"   {payload_str}"
        )
        lines.append(line)

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
            name = p.get("title", "")
            query = name or p.get("address", "")
            map_url = f"https://map.naver.com/v5/search/{urllib.parse.quote(query)}" if query else ""
            lines.append(f"- [{name}]({map_url})" if map_url else f"- {name}")

    return "\n".join(lines)

def _clean_tavily_results(raw_results: list, score_threshold: float = 0.3) -> list[dict]:
    """Tavily 결과 정제: score 필터 → 서울 키워드 필터 → URL 중복 제거 → 내용 정규화."""
    import html
    seen_urls: set[str] = set()
    cleaned = []
    for r in raw_results:
        if not isinstance(r, dict):
            continue
        # score 기준 미달 제거
        score = r.get("score") or 0.0
        if score < score_threshold:
            continue
        # 서울 관련 결과만 허용
        if not _is_seoul_result(r):
            continue
        # URL 중복 제거
        url = (r.get("url") or "").strip()
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        # content 정제: HTML 엔티티 디코딩 + 공백 정규화
        raw_content = r.get("content") or ""
        raw_content = html.unescape(raw_content)
        raw_content = re.sub(r"<[^>]+>", "", raw_content)          # HTML 태그 제거
        raw_content = re.sub(r"\s+", " ", raw_content).strip()    # 공백 정규화
        if not raw_content:
            continue
        cleaned.append({
            "title": (r.get("title") or "").strip(),
            "url": url,
            "content": raw_content[:300],
            "score": score,
            "images": r.get("images") or [],
        })
    return cleaned


def _build_web_context(input_tags: list[str], slots: Optional[Dict[str, Any]] = None, timeout_sec: float = 7.0) -> tuple[str, list[str]]:
    # Fallback: candidates가 비어있으면 Tavily 웹 검색으로 보완
    web_context = ""
    print("[Executor] No candidates — trying Tavily fallback")

    tavily = LLMFactory.get_tavily()

    tags = ", ".join(input_tags) if input_tags else ""

    location = getattr_safe(slots, "location") if slots else None
    loc_name = getattr_safe(location, "name") if location else None
    if loc_name:
        search_query = f"서울 {loc_name} 여행 {tags}".strip(", ")
    else:
        search_query = f"서울 여행 {tags}".strip()

    # ThreadPoolExecutor + shutdown(wait=False) 로 진짜 타임아웃 보장
    # with 블록 방식은 shutdown(wait=True)가 되어 timeout 후에도 블로킹 발생
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(tavily.invoke, search_query)
        web_results = future.result(timeout=timeout_sec)
    except concurrent.futures.TimeoutError:
        print(f"[Executor] Tavily fallback timeout after {timeout_sec:.1f}s")
        executor.shutdown(wait=False)
        return web_context, []
    except Exception as e:
        print(f"[Executor] Tavily fallback failed: {e}")
        executor.shutdown(wait=False)
        return web_context, []
    else:
        executor.shutdown(wait=False)

    cleaned = _clean_tavily_results(web_results)
    print(f"[Executor] Tavily raw={len(web_results)} → cleaned(Seoul)={len(cleaned)}")
    if not cleaned:
        return web_context, []

    # score 높은 순 정렬 후 임계값 이상인 결과에서만 이미지 수집
    sorted_results = sorted(cleaned, key=lambda r: r["score"], reverse=True)
    tavily_images = [
        img
        for r in sorted_results
        if r["score"] >= TAVILY_IMAGE_SCORE_THRESHOLD
        for img in r["images"]
        if img
    ]

    web_lines = ["## 웹 검색 결과 (참고 정보)"]
    for r in cleaned:
        title = f"[{r['title']}] " if r["title"] else ""
        web_lines.append(f"- {title}{r['content']}")
    web_context = "\n".join(web_lines)
    return web_context, tavily_images


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
            print(f"[Executor] Failed to encode local image {image_path}: {e}")
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

async def executor_node(state: TravelState, config=None):
    """
    여행 계획을 최종적으로 확정하는 노드
    - 검증: 영업시간, 예약 필요 여부 확인
    - 링크 생성: 네이버 지도 링크 생성
    - 최종 답변 생성
    """
    print("--- Executor Agent ---")

    candidates = state.get("candidates")
    candidate_pool = state.get("candidate_pool")
    user_input = get_effective_user_input(state)
    input_tags = state.get("input_tags", [])
    messages = state.get("messages", [])[-10:]
    prefs_info = state.get("prefs_info", "")
    primary_intent = state.get("primary_intent")
    slots = state.get("slots")
    image_path = state.get("input_image")
    input_lat = state.get("input_lat")
    input_long = state.get("input_long")
    follow_up_questions = state.get("follow_up_questions", [])

    # 사용자 위치 컨텍스트 구성 (GPS 위치 우선, 없으면 slots.location 사용)
    user_location_context = ""
    if input_lat and input_long:
        try:
            from app.utils.geocoder import GeoCoder
            geo = GeoCoder().reverse_geocoder(input_lat, input_long)
            road = (geo.get("road_address") or "").strip() if geo else ""
            addr = road or f"위도 {input_lat}, 경도 {input_long}"
        except Exception:
            addr = f"위도 {input_lat}, 경도 {input_long}"
        user_location_context = f"- 사용자 현재 위치: {addr}\n- 현재 위치에서 가까운 장소를 우선 추천하세요."
    elif slots:
        location = getattr_safe(slots, "location")
        if location and getattr_safe(location, "name"):
            loc_name = getattr_safe(location, "name")
            user_location_context = f"- 사용자 요청 지역: {loc_name}\n- 해당 지역 내 또는 인근 장소를 우선 추천하세요."

    if not candidate_pool:
        candidate_pool = candidates

    web_context = None
    tavily_images: list[str] = []
    place_context = None
    itinerary_context = None
    if not candidates:
        print("[Executor] No candidates — trying Tavily fallback")
        web_context, tavily_images = _build_web_context(input_tags, slots)
    else:
        print(f"candidate_pool : {len(candidate_pool)}")
        print(f"candidates : {len(candidates)}")

        # 컨텍스트 구성
        place_context = _build_place_context(candidates)
        # print(f"[Executor] Place context: {place_context}")
        itinerary_context = _build_itinerary_context(candidates) if primary_intent == IntentType.TRIP_PLANNING else None

    # 슬롯 정보 텍스트
    slots_info = ""
    if slots:
        slots_dict = slots.model_dump() if hasattr(slots, 'model_dump') else (slots.dict() if hasattr(slots, 'dict') else slots)
        slots_info = "\n".join(f"- {k}: {v}" for k, v in slots_dict.items() if v is not None)

    # 최종 답변 생성
    context_block = "\n\n".join(filter(None, [place_context, itinerary_context]))

    llm = LLMFactory.get_llm(temperature=0.5)

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

    system_prompt = EXECUTOR_PROMPT.format(
        slots_info=slots_info,
        user_location_context=user_location_context,
        prefs_info=prefs_info,
        web_context=web_context or "",
        context_block=context_block or "",
        follow_up_questions=follow_up_questions,
    )

    prompt_messages = [SystemMessage(content=system_prompt), *messages]
    if image_path:
        prompt_messages.append(HumanMessage(content=content_blocks))
    else:
        prompt_messages.append(HumanMessage(content=user_input))

    # astream을 사용하여 토큰 단위 스트리밍 (custom event로 SSE 레이어에 전달)
    full_content = await collect_streamed_text(llm, prompt_messages, config=config)

    cleaned_answer = full_content.strip()
    print(f"[Executor] Answer length: {len(cleaned_answer)}")

    # PlaceInfo 목록 구성 (Qdrant path: candidates 기반, Tavily path: 답변 파싱 + 지오코딩)
    if candidates:
        place_info_list = _build_place_info_from_candidates(candidates, cleaned_answer)
    else:
        place_info_list = _build_tavily_place_info(cleaned_answer, tavily_images, slots=slots)

    print(f"[Executor] place_info_list: {len(place_info_list)} items")

    return {
        "messages": AIMessage(content=cleaned_answer),
        "answer": cleaned_answer,
        "place_info_list": place_info_list,
    }


async def executor_missing_node(state: TravelState, config=None):
    """
    여행 계획에서 부족한 정보를 재질문하는 node
    """
    print("--- Executor Missing Agent ---")

    # missing_slots가 있으면 (planner의 재질문) 바로 반환
    missing_slots = state.get("missing_slots", [])
    user_input = get_effective_user_input(state)
    messages = state.get("messages", [])[-10:]
    prefs_info = state.get("prefs_info", "")
    slots = state.get("slots")
    follow_up_questions = state.get("follow_up_questions", [])

    print(f"[Executor] Missing slots: {missing_slots}")
    missing_context = _build_missing_context(missing_slots)
    
    human_message = HumanMessage(content="여행 계획을 위한 추가 정보가 필요합니다. 아래 정보를 참고하여 질문해주세요.")

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXECUTOR_MISSING_INFO_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        human_message
    ])

    llm = LLMFactory.get_llm(temperature=0.5)
    prompt_value = prompt.invoke({
        "messages": messages,
        "user_input": user_input,
        "slots_info": slots,
        "prefs_info": prefs_info,
        "missing_info": missing_context,
        "follow_up_questions": follow_up_questions,
    })

    full_content = await collect_streamed_text(llm, prompt_value, config=config)

    answer = full_content.strip()
    print(f"[Executor] Answer generated (length={len(answer)})")

    return {"messages": AIMessage(content=answer), "answer": answer}


async def executor_general_node(state: TravelState, config=None):
    """
    일상 대화 node
    """
    print("--- Executor General Agent ---")

    user_input = get_effective_user_input(state)
    messages = state.get("messages", [])[-10:]
    prefs_info = state.get("prefs_info", "")
    slots = state.get("slots")
    follow_up_questions = state.get("follow_up_questions", [])

    # 슬롯 정보 텍스트
    slots_info = ""
    if slots:
        slots_dict = slots.model_dump() if hasattr(slots, 'model_dump') else (slots.dict() if hasattr(slots, 'dict') else slots)
        slots_info = "\n".join(f"- {k}: {v}" for k, v in slots_dict.items() if v is not None)

    llm = LLMFactory.get_llm(temperature=0.7)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXECUTOR_GENERAL_PROMPT),
    ])

    prompt_value = prompt.invoke({
        "messages": messages,
        "user_input": user_input,
        "slots_info": slots_info,
        "prefs_info": prefs_info,
        "follow_up_questions": follow_up_questions,
    })

    full_content = await collect_streamed_text(llm, prompt_value, config=config)

    answer = full_content.strip()
    print(f"[Executor General] Answer generated (length={len(answer)})")

    return {"messages": AIMessage(content=answer), "answer": answer}
