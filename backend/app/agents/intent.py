import asyncio
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.models.output import IntentOutput, IntentType, IntentSlots, InputType
from app.services.prompts import INTENT_PROMPT, SUMMARIZER_PROMPT
from app.agents.models.state import TravelState
from app.utils.llm_factory import LLMFactory


async def _update_summary(state: TravelState) -> str:
    """
    기존 summary_message와 최근 대화 내역을 합쳐 누적 요약을 업데이트합니다.
    intent_node 시작 시점에 호출되므로, 이전 턴까지의 대화가 요약됩니다.
    """
    summary_message = state.get("summary_message", "")
    messages = state.get("messages", [])
    
    # 메시지가 없으면 요약할 것이 없음
    if not messages:
        return summary_message or ""
    
    # 기존 요약이 없고 메시지도 적으면 스킵
    if not summary_message and len(messages) < 2:
        return ""
    
    # 최근 대화 내역 (마지막 턴의 Human + AI)
    recent = messages[-2:] if len(messages) >= 2 else messages
    recent_text = "\n".join([f"{m.type}: {m.content[:500]}" for m in recent])
    
    llm = LLMFactory.get_llm(temperature=0)
    prompt = ChatPromptTemplate.from_template(SUMMARIZER_PROMPT)
    chain = prompt | llm
    
    result = await chain.ainvoke({
        "summary_message": summary_message or "아직 대화 요약 없음",
        "recent_messages": recent_text
    })
    
    new_summary = result.content
    print(f"[Intent] Summary updated: {new_summary[:100]}...")
    return new_summary


async def intent_node(state: TravelState):
    """
    사용자 의도 분석 Agent
    - DB 접근 없이, state에 주입된 prefs_info를 그대로 사용
    - 대화 요약(summary_message)도 여기서 누적 업데이트
    - 요약과 의도 분석을 병렬로 실행하여 지연 최소화
    """
    print("--- Intent Agent ---")

    # API 레이어에서 주입된 사용자 선호도 정보 사용
    prefs_info = state.get("prefs_info", "특별한 선호도 정보 없음")

    user_input = state.get("user_input")
    image_path = state.get("image_path")
    
    if not user_input:
        # 요약은 순차로 처리 (빠른 경로)
        updated_summary = await _update_summary(state)
        if image_path:
             return {
                "intents": [IntentType.IMAGE_SIMILAR],
                "primary_intent": IntentType.IMAGE_SIMILAR,
                "slots": IntentSlots(input_type=InputType.IMAGE),
                "summary_query": "이미지 검색",
                "summary_message": updated_summary,
                "prefs_info": prefs_info
             }
        return state

    # 최근 10개 메시지만 사용
    messages = state.get("messages", [])[-10:]

    # LLM 및 Structured Output 설정
    llm = LLMFactory.get_llm()
    structured_llm = llm.with_structured_output(IntentOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", INTENT_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{user_input}")
    ])

    chain = prompt | structured_llm

    # 요약 업데이트와 의도 분석을 병렬로 실행 (서로 독립적)
    updated_summary, result = await asyncio.gather(
        _update_summary(state),
        chain.ainvoke({"messages": messages, "user_input": user_input})
    )

    print("Intent Result : ", result)

    # State에 결과 저장
    return {
        "intents": result.intents,
        "primary_intent": result.primary_intent,
        "slots": result.slots,
        "summary_query": result.summary_query,
        "summary_message": updated_summary,
        "prefs_info": prefs_info
    }



