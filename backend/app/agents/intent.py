from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.models.output import IntentOutput, IntentType, IntentSlots, InputType
from app.services.prompts import INTENT_PROMPT
from app.agents.models.state import TravelState
from app.utils.llm_factory import LLMFactory
from app.agents.models.output import CategoryType

async def intent_node(state: TravelState):
    """
    사용자 의도 분석 Agent
    - DB 접근 없이, state에 주입된 prefs_info를 그대로 사용
    - 대화 요약(summary_message)도 여기서 누적 업데이트
    - 요약과 의도 분석을 병렬로 실행하여 지연 최소화
    """
    print("--- Intent Agent ---")

    # API 레이어에서 주입된 사용자 선호도 정보 사용
    print(f"[Intent] state keys: {list(state.keys())}")
    prefs_info = state.get("prefs_info", "[DEBUG] PREFS_INFO_MISSING_IN_STATE")

    user_input = state.get("user_input")
    image_path = state.get("image_path")
    summary_title = state.get("summary_title", "제목 없음")
    summary_message = state.get("summary_message", "아직 대화 요약 없음")
    
    if not user_input:
        if image_path:
             return {
                "intents": [IntentType.IMAGE_SIMILAR],
                "primary_intent": IntentType.IMAGE_SIMILAR,
                "slots": IntentSlots(input_type=InputType.IMAGE),
                "summary_title": "이미지 검색",
                "summary_message": "이미지 기반 장소 검색 요청",
             }
        return {
            "intents": [IntentType.GENERAL],
            "primary_intent": IntentType.GENERAL,
        }

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

    print(f"[Intent] Prefs info from state: {prefs_info}")
    result = await chain.ainvoke({
            "messages": messages, 
            "user_input": user_input, 
            "prefs_info": prefs_info,
            "category_desc": CategoryType.description(),
            "summary_title": summary_title,
            "summary_message": summary_message
        })

    print("Intent Result : ", result)

    # State에 결과 저장
    return {
        "intents": result.intents,
        "primary_intent": result.primary_intent,
        "slots": result.slots,
        "update_user_input": result.update_user_input,
        "summary_title": result.summary_title,
        "summary_message": result.summary_message,
        "prefs_info": prefs_info,
    }
