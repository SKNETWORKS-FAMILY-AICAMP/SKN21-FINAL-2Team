from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.models.output import IntentOutput, IntentType, IntentSlots, InputType
from app.services.prompts import INTENT_PROMPT
from app.agents.models.state import TravelState
from app.utils.llm_factory import LLMFactory


async def intent_node(state: TravelState):
    """
    사용자 의도 분석 Agent
    - DB 접근 없이, state에 주입된 prefs_info를 그대로 사용
    """
    print("--- Intent Agent ---")

    # API 레이어에서 주입된 사용자 선호도 정보 사용
    prefs_info = state.get("prefs_info", "특별한 선호도 정보 없음")
    
    # LLM 및 Structured Output 설정
    llm = LLMFactory.get_llm()
    structured_llm = llm.with_structured_output(IntentOutput)

    user_input = state.get("user_input")
    image_path = state.get("image_path")
    
    if not user_input:
        if image_path:
             # 텍스트 없이 이미지만 있는 경우 -> 이미지 검색/장소 문의로 처리
             return {
                "intents": [IntentType.IMAGE_SIMILAR],
                "primary_intent": IntentType.IMAGE_SIMILAR,
                "slots": IntentSlots(input_type=InputType.IMAGE),
                "prefs_info": prefs_info
             }
        return state

    # 최근 10개 메시지만 사용
    messages = state.get("messages", [])[-10:]

    prompt = ChatPromptTemplate.from_messages([
        ("system", INTENT_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{user_input}")
    ])

    chain = prompt | structured_llm
    result = await chain.ainvoke({
        "messages": messages, 
        "user_input": user_input
    })

    print("Intent Result : ", result)

    # State에 결과 저장
    return {
        "intents": result.intents,
        "primary_intent": result.primary_intent,
        "slots": result.slots,
        "prefs_info": prefs_info
    }

