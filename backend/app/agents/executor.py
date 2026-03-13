import urllib.parse
import os
import base64
import mimetypes
import concurrent.futures
import re
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.agents.models.state import TravelState, get_effective_user_input
from app.agents.models.output import IntentType
from app.agents.prompts.executor_prompt import EXECUTOR_PROMPT, EXECUTOR_MISSING_INFO_PROMPT, EXECUTOR_GENERAL_PROMPT
from app.core.llm_factory import LLMFactory
from app.utils.common import parse_payload, getattr_safe
from app.core.llm_streaming import collect_streamed_text
from app.utils.place_id import get_place_id


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", (value or "")).lower()


def _infer_selected_ids_from_answer(answer_text: str, candidates: List[Dict[str, Any]]) -> List[str]:
    if not answer_text or not candidates:
        return []

    inferred_ids: List[str] = []

    # 1) Markdown 링크 텍스트 우선 매칭: [장소명](...)
    link_names = re.findall(r"\[([^\]]+)\]\(https?://[^)]+\)", answer_text)
    for raw_name in link_names:
        name_key = _normalize_text(raw_name)
        for c in candidates:
            payload = c.get("payload", {}) or {}
            candidate_name = payload.get("title") or payload.get("name") or ""
            if not candidate_name:
                continue
            candidate_key = _normalize_text(candidate_name)
            if name_key and (name_key in candidate_key or candidate_key in name_key):
                cid = get_place_id(c)
                if cid and cid not in inferred_ids:
                    inferred_ids.append(cid)
                break

    # 2) 링크가 없으면 본문 장소명 포함 여부로 매칭
    if not inferred_ids:
        answer_key = _normalize_text(answer_text)
        for c in candidates:
            payload = c.get("payload", {}) or {}
            candidate_name = payload.get("title") or payload.get("name") or ""
            candidate_key = _normalize_text(candidate_name)
            if candidate_key and candidate_key in answer_key:
                cid = get_place_id(c)
                if cid and cid not in inferred_ids:
                    inferred_ids.append(cid)

    return inferred_ids

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

def _build_web_context(query: str, slots: Optional[Dict[str, Any]] = None, timeout_sec: float = 3.0) -> str:
    # Fallback: candidates가 비어있으면 Tavily 웹 검색으로 보완
    web_context = ""
    print("[Executor] No candidates — trying Tavily fallback")
    try:
        tavily = LLMFactory.get_tavily()
        if not query:
             query = "한국 여행 추천" # 쿼리가 비어있을 경우 기본값 설정
        
        search_query = query
        if slots:
            location = getattr_safe(slots, "location")
            if location:
                search_query = f"{location} 여행 {query}"
        # Tavily 응답 지연 시 executor 전체 대기를 막기 위해 타임아웃 적용
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(tavily.invoke, search_query)
            web_results = future.result(timeout=timeout_sec)
        if web_results:
            web_lines = ["## 웹 검색 결과 (참고 정보)"]
            for r in web_results:
                if isinstance(r, dict):
                    web_lines.append(f"- {r.get('content', '')[:200]}")
                else:
                    web_lines.append(f"- {str(r)[:200]}")
            web_context = "\n".join(web_lines)
            print(f"[Executor] Tavily fallback results: {len(web_results)}")
    except concurrent.futures.TimeoutError:
        print(f"[Executor] Tavily fallback timeout after {timeout_sec:.1f}s")
    except Exception as e:
        print(f"[Executor] Tavily fallback failed: {e}")

    return web_context


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
    messages = state.get("messages", [])[-10:]
    prefs_info = state.get("prefs_info", "")
    primary_intent = state.get("primary_intent")
    slots = state.get("slots")
    image_path = state.get("input_image") # 이미지 경로 가져오기
    follow_up_questions = state.get("follow_up_questions", [])

    if not candidate_pool:
        candidate_pool = candidates

    web_context = None
    place_context = None
    itinerary_context = None
    if not candidates:
        print("[Executor] No candidates — trying Tavily fallback")
        web_context = _build_web_context(user_input, slots)
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

    # candidates 부족 시 안내 메시지 추가
    data_notice = ""
    if not candidates and not web_context:
        data_notice = "\n⚠️ 참고: 검색 결과가 없어 일반 지식을 기반으로 답변합니다. 정보의 정확도가 다소 낮을 수 있으니 확인 부탁드려요."
    elif candidates is not None and len(candidates) < 3:
        data_notice = "\n※ 검색 결과가 제한적이어서 추가 장소가 필요하시면 더 구체적으로 말씀해 주세요."

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
        data_notice=data_notice,
        slots_info=slots_info,
        prefs_info=prefs_info,
        web_context=web_context or "",
        context_block=context_block or "",
    )

    prompt_messages = [SystemMessage(content=system_prompt), *messages]
    if image_path:
        prompt_messages.append(HumanMessage(content=content_blocks))
    else:
        prompt_messages.append(HumanMessage(content=user_input))

    # astream을 사용하여 토큰 단위 스트리밍 (custom event로 SSE 레이어에 전달)
    full_content = await collect_streamed_text(llm, prompt_messages, config=config)

    # ID 태그 추출 ([IDs: id1, id2, ...]) - 공백/대소문자 변형 허용
    selected_ids = []
    
    tag_match = re.search(r"\[\s*ids?\s*:\s*([^\]]+)\]", full_content, flags=re.IGNORECASE)
    if tag_match:
        ids_str = tag_match.group(1)
        # 쉼표로 구분된 ID들 추출
        selected_ids = [s.strip() for s in ids_str.split(',') if s.strip()]
        # 답변에서 태그 제거
        cleaned_answer = re.sub(r"\[\s*ids?\s*:\s*.*?\]", "", full_content, flags=re.IGNORECASE).strip()
    else:
        cleaned_answer = full_content.strip()

    if not selected_ids:
        selected_ids = _infer_selected_ids_from_answer(cleaned_answer, candidate_pool)

    # 후보 풀에 존재하지 않는 ID는 제거
    valid_candidate_ids = set()
    for c in candidate_pool:
        payload = c.get("payload", {}) if isinstance(c, dict) else {}
        cid = get_place_id(c)
        if cid:
            valid_candidate_ids.add(cid)

    invalid_ids = [cid for cid in selected_ids if cid not in valid_candidate_ids]
    selected_ids = [cid for cid in selected_ids if cid in valid_candidate_ids]

    # LLM 태그가 모두 무효하면 텍스트 기반 fallback 재시도
    if not selected_ids:
        selected_ids = _infer_selected_ids_from_answer(cleaned_answer, candidate_pool)
        selected_ids = [cid for cid in selected_ids if cid in valid_candidate_ids]

    if invalid_ids:
        print(f"[Executor] Invalid selected IDs filtered: {invalid_ids}")

    print(f"[Executor] Selected IDs: {selected_ids}")
    print(f"[Executor] Answer length: {len(cleaned_answer)}")

    return {"messages": AIMessage(content=cleaned_answer), "answer": cleaned_answer, "selected_ids": selected_ids}


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
