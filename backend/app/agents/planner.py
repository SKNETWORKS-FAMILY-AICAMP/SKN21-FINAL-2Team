from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.models.state import TravelState
from app.services.prompts import PLANNER_PROMPT
from app.utils.llm_factory import LLMFactory
from app.agents.models.output import PlannerOutput

async def planner_node(state: TravelState):
    """
    여행 계획을 생성하는 Agent
    - 대화의 흐름과 사용자의 input을 분석해 장소 검색을 하기 위해서 어떤 정보들이 필요한지 llm이 결정해서 state에 저장한다.
    """
    print("--- Planner Agent ---")

    user_input = state.get("user_input", "")
    messages = state.get("messages", [])[-10:]
    slots = state.get("slots")
    prefs_info = state.get("prefs_info", {})

    if not user_input:
        return state

    # 슬롯 정보를 텍스트로 변환
    slots_info = ""
    if slots:
        slots_dict = slots.model_dump() if hasattr(slots, 'model_dump') else (slots.dict() if hasattr(slots, 'dict') else slots)
        slots_info = "\n".join(f"- {k}: {v}" for k, v in slots_dict.items() if v is not None)

    # LLM으로 여행 일정 초안 생성
    llm = LLMFactory.get_llm(temperature=0.3)
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", PLANNER_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", (
            "사용자 입력: {user_input}\n\n"
            "슬롯 정보:\n{slots_info}\n\n"
            "사용자 선호도:\n{prefs_info}"
        ))
    ])

    chain = prompt | structured_llm

    try:
        result = await chain.ainvoke({
            "messages": messages,
            "user_input": user_input,
            "slots_info": slots_info or "없음",
            "prefs_info": prefs_info or "없음",
        })

        print(f"[Planner] itinerary_count={len(result.itinerary)}, missing_slots={result.missing_slots}")

        # 일정을 dict 리스트로 변환
        itinerary = [item.model_dump() for item in result.itinerary]

        # 부족한 정보가 있으면 LLM이 생성한 자연스러운 후속 질문 사용
        missing_slots = result.missing_slots
        if missing_slots and result.followup_question:
            return {
                "itinerary": itinerary,
                "missing_slots": missing_slots,
                "answer": result.followup_question,
            }

        return {
            "itinerary": itinerary,
            "missing_slots": [],
        }

    except Exception as e:
        print(f"[Planner] Error: {e}")
        return {
            "itinerary": [],
            "missing_slots": ["location", "duration"],
        }