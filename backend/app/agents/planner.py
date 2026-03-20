from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.state import TravelState, get_effective_user_input, get_slots_info
from app.agents.prompts.prompts import PLANNER_PROMPT
from app.core.llm_factory import LLMFactory
from app.agents.models.output import PlannerOutput
from app.utils.common import dprint


def build_current_itinerary_context(itinerary: List[Dict[str, Any]] | None) -> str:
    """
    기존 itinerary를 LLM 프롬프트에 넣기 쉬운 텍스트로 변환한다.

    Args:
        itinerary: state에 저장된 기존 여행 일정 목록.

    Returns:
        일차 기준으로 정렬된 일정 요약 문자열. 일정이 없으면 "없음"을 반환한다.
    """
    if not itinerary:
        return "없음"

    def _sort_key(item: Dict[str, Any]) -> tuple[int, str]:
        return (
            int(item.get("day", 1) or 1),
            str(item.get("activity", "")),
        )

    lines: List[str] = []
    for item in sorted(itinerary, key=_sort_key):
        day = item.get("day", 1)
        time_slot = item.get("time_slot", "")
        activity = item.get("activity", "")
        category = item.get("category", "")
        search_query = item.get("search_query", "")
        slot_label = f" [{time_slot}]" if time_slot else ""
        lines.append(
            f"{day}일차{slot_label} - {activity} / 카테고리: {category} / 검색어: {search_query}"
        )

    return "\n".join(lines)


async def planner_node(state: TravelState):
    """
    여행 계획을 생성하는 Agent
    - 대화의 흐름과 사용자의 input을 분석해 장소 검색을 하기 위해서 어떤 정보들이 필요한지 llm이 결정해서 state에 저장한다.
    """
    dprint("--- Planner Agent ---")
    await adispatch_custom_event("pipeline_step", {"node": "planner", "status": "start"})

    user_input = get_effective_user_input(state)
    user_lat = state.get("input_lat")
    user_lon = state.get("input_lon")
    messages = state.get("messages", [])[-6:]
    slots_info = get_slots_info(state)
    prefs_info = state.get("prefs_info", "")
    current_itinerary = build_current_itinerary_context(state.get("itinerary"))
    summary_message = state.get("summary_message")

    pinned_places = state.get("pinned_places") or []
    if pinned_places:
        pinned_lines = [
            f"- {p.get('name', '이름없음')} (주소: {p.get('address', '')})"
            for p in pinned_places
        ]
        pinned_places_info = "\n".join(pinned_lines)
    else:
        pinned_places_info = "없음"

    if not user_input:
        return state

    try:
        # LLM으로 여행 일정 초안 생성
        llm = LLMFactory.get_llm(temperature=0.7)
        structured_llm = llm.with_structured_output(PlannerOutput)

        prompt = ChatPromptTemplate.from_messages([
            ("system", PLANNER_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{user_input}")
        ])

        chain = prompt | structured_llm

        result = await chain.ainvoke({
            "summary_message": summary_message or "없음",
            "messages": messages,
            "user_input": user_input,
            "user_geo": f"위도: {user_lat}, 경도: {user_lon}",
            "slots_info": slots_info or "없음",
            "prefs_info": prefs_info,
            "current_itinerary": current_itinerary,
            "pinned_places_info": pinned_places_info,
        })

        dprint(f"[Planner] itinerary_count={len(result.itinerary)}, missing_slots={result.missing_slots}")

        # Enum 값을 문자열로 직렬화하여 retriever 필터와 타입을 맞춘다.
        itinerary = [item.model_dump(mode="json") for item in result.itinerary]

        # 부족한 정보가 있으면 LLM이 생성한 자연스러운 후속 질문 사용
        state_dict = {"itinerary": itinerary}

        if result.missing_slots:
            state_dict["missing_slots"] = result.missing_slots
        
        if result.followup_question:
            followup_questions = state.get("follow_up_questions", [])
            followup_questions.append(result.followup_question)
            state_dict["follow_up_questions"] = followup_questions

        return state_dict

    except Exception as e:
        dprint(f"[Planner] Error: {e}")
        return {
            "itinerary": [],
            "missing_slots": [],
        }
