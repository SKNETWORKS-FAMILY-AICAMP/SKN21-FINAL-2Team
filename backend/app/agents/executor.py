import urllib.parse
import os
import base64
import mimetypes
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.agents.models.state import TravelState
from app.agents.models.output import IntentType
from app.services.prompts import EXECUTOR_PROMPT, EXECUTOR_MISSING_INFO_PROMPT
from app.utils.llm_factory import LLMFactory

def _build_place_context(candidates: List[Dict[str, Any]]) -> str:
    """candidates 리스트를 LLM에 전달할 컨텍스트 문자열로 변환"""
    if not candidates:
        return ""

    if len(candidates) == 0:
        return ""

    lines = ["## 검색된 장소 정보"]
    for i, c in enumerate(candidates, 1):
        payload = c.get("payload", {})
        lat = float(payload.get("mapy", "0"))
        lng = float(payload.get("mapx", "0"))

        # 네이버 지도 링크 생성
        query = payload.get("title")
        
        if query:
            encoded = urllib.parse.quote(query)
            payload['map_url'] = f"https://map.naver.com/v5/search/{encoded}?c=15.00,{lng},{lat},0,dh"

        line = f"{i}. **{payload}**"

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

def _build_web_context(query: str, slots: Optional[Dict[str, Any]] = None) -> str:
    # Fallback: candidates가 비어있으면 Tavily 웹 검색으로 보완
    web_context = ""
    print("[Executor] No candidates — trying Tavily fallback")
    try:
        tavily = LLMFactory.get_tavily()
        if not query:
             query = "한국 여행 추천" # 쿼리가 비어있을 경우 기본값 설정
        
        search_query = query
        if slots:
            location = slots.location if hasattr(slots, 'location') else (slots.get("location") if isinstance(slots, dict) else None)
            if location:
                search_query = f"{location} 여행 {query}"
        web_results = tavily.invoke(search_query)
        if web_results:
            web_lines = ["## 웹 검색 결과 (참고 정보)"]
            for r in web_results:
                if isinstance(r, dict):
                    web_lines.append(f"- {r.get('content', '')[:200]}")
                else:
                    web_lines.append(f"- {str(r)[:200]}")
            web_context = "\n".join(web_lines)
            print(f"[Executor] Tavily fallback results: {len(web_results)}")
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

async def executor_node(state: TravelState):
    """
    여행 계획을 최종적으로 확정하는 노드
    - 검증: 영업시간, 예약 필요 여부 확인
    - 링크 생성: 네이버 지도 링크 생성
    - 최종 답변 생성
    """
    print("--- Executor Agent ---")

    candidates = state.get("candidates", [])
    user_input = state.get("user_input", "")
    messages = state.get("messages", [])[-10:]
    prefs_info = state.get("prefs_info", {})
    primary_intent = state.get("primary_intent")
    slots = state.get("slots")
    image_path = state.get("image_path") # 이미지 경로 가져오기

    # 컨텍스트 구성
    place_context = _build_place_context(candidates)
    itinerary_context = _build_itinerary_context(candidates) if primary_intent == IntentType.TRIP_PLANNING else None

    # Fallback: candidates가 비어있으면 Tavily 웹 검색으로 보완
    web_context = None
    if len(candidates) == 0:
        print("[Executor] No candidates — trying Tavily fallback")
        web_context = _build_web_context(user_input, slots)

    # 슬롯 정보 텍스트
    slots_info = ""
    if slots:
        slots_dict = slots.model_dump() if hasattr(slots, 'model_dump') else (slots.dict() if hasattr(slots, 'dict') else slots)
        slots_info = "\n".join(f"- {k}: {v}" for k, v in slots_dict.items() if v is not None)

    # candidates 부족 시 안내 메시지 추가
    data_notice = ""
    if candidates is None and web_context is None:
        data_notice = "\n⚠️ 참고: 검색 결과가 없어 일반 지식을 기반으로 답변합니다. 정보의 정확도가 다소 낮을 수 있으니 확인 부탁드려요."
    elif candidates is not None and len(candidates) < 3:
        data_notice = "\n※ 검색 결과가 제한적이어서 추가 장소가 필요하시면 더 구체적으로 말씀해 주세요."

    # 최종 답변 생성
    context_block = "\n\n".join(filter(None, [place_context, itinerary_context, web_context]))

    llm = LLMFactory.get_llm(temperature=0.5)

    # HumanMessage 구성 (멀티모달 지원)
    content_blocks = []
    
    # 텍스트 추가
    if user_input:
        content_blocks.append({"type": "text", "text": f"사용자 입력: {user_input}"})
    else:
        # 텍스트가 없어도 이미지가 있으면 안내 문구 추가
        if image_path:
             content_blocks.append({"type": "text", "text": "사용자가 이미지를 보냈습니다. 이 이미지를 분석해서 어울리는 장소를 추천해주세요."})

    # 이미지 추가
    if image_path:
        image_url = _get_image_data_url(image_path)
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
    
    # content_blocks가 비어있으면(텍스트도 없고 이미지도 없음) 처리
    if not content_blocks:
          content_blocks.append({"type": "text", "text": "사용자 입력이 없습니다."})

    human_message = HumanMessage(content=content_blocks)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXECUTOR_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        human_message
    ])

    prompt_value = prompt.invoke({
        "messages": messages,
        "user_input": user_input,
        "slots_info": slots_info,
        "prefs_info": prefs_info,
        "context_block": context_block,
        "data_notice": data_notice,
    })

    # astream을 사용하여 토큰 단위 스트리밍 (astream_events가 자동 캡처)
    full_content = ""
    async for chunk in llm.astream(prompt_value):
        if chunk.content:
            full_content += chunk.content

    answer = full_content
    print(f"[Executor] Answer generated (length={len(answer)})")

    return {"messages": AIMessage(content=answer), "answer": answer}


async def executor_missing_node(state: TravelState):
    """
    여행 계획에서 부족한 정보를 재질문하는 node
    """
    print("--- Executor Missing Agent ---")

    # missing_slots가 있으면 (planner의 재질문) 바로 반환
    missing_slots = state.get("missing_slots", [])

    print(f"[Executor] Missing slots: {missing_slots}")
    missing_context = _build_missing_context(missing_slots)
    
    human_message = HumanMessage(content="여행 계획을 위한 추가 정보가 필요합니다. 아래 정보를 참고하여 질문해주세요.")

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXECUTOR_MISSING_INFO_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        human_message
    ])

    llm = LLMFactory.get_llm(temperature=0.3)
    response = await llm.ainvoke(prompt.invoke({
        "messages": state.get("messages")[-10:],
        "user_input": state.get("user_input"),
        "slots_info": state.get("slots"),
        "prefs_info": state.get("prefs_info"),
        "missing_info": missing_context,
    }))

    answer = response.content
    print(f"[Executor] Answer generated (length={len(answer)})")

    return {"messages": AIMessage(content=answer), "answer": answer}

