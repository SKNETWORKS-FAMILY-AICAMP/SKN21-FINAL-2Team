from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.models.output import IntentOutput, IntentType, IntentSlots, InputType
from app.agents.prompts.prompts import INTENT_PROMPT
from app.agents.models.state import TravelState
from app.core.llm_factory import LLMFactory
from app.agents.models.output import CategoryType
from app.utils.geocoder import NormalizedLocation
from app.utils.common import in_seoul_bbox

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
    image_path = state.get("input_image")
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
            "category_desc": CategoryType.description(),
            "summary_title": summary_title,
            "summary_message": summary_message,
        })

    print("Intent Result : ", result)

    primary_intent = result.primary_intent
    update_user_input = result.update_user_input or ""

    # --- 표준 장소 후처리: LLM 반환 location을 서버에서 최종 정규화 ---
    # 조건 기준: canonical_matched 여부 (이름 변경 여부 X)
    # → LLM이 canonical key와 동일한 이름을 반환해도 lat/lon이 환각일 수 있으므로
    #   사전 매칭이 성공한 경우 항상 사전 좌표로 덮어쓴다.
    slots = result.slots
    if slots and slots.location:
        if slots.location.name:
            norm = NormalizedLocation.normalize_location(slots.location.name)
            if norm.canonical_matched and norm.lat is not None:
                # 사전 매칭 성공 → 이름·좌표 모두 사전 값으로 확정
                if norm.normalized_location and norm.normalized_location != slots.location.name:
                    slots.location.name = norm.normalized_location
                slots.location.lat = norm.lat
                slots.location.lon = norm.lon
                print(
                    f"[Intent] location resolved from LANDMARK_DICTIONARY: {slots.location.name!r} "
                    f"lat={norm.lat} lon={norm.lon} (canonical_matched=True)"
                )

        if slots.location.lat and slots.location.lon:
            if not in_seoul_bbox(slots.location.lat, slots.location.lon):
                # 좌표가 서울 밖에 있으면 일반 검색으로 변경
                primary_intent = IntentType.GENERAL
    
    # State에 결과 저장
    return {
        "intents": result.intents,
        "primary_intent": primary_intent,
        "slots": slots,
        "update_user_input": update_user_input,
        "summary_title": result.summary_title,
        "summary_message": result.summary_message,
        "input_tags": result.input_tags,
        "prefs_info": prefs_info,
        "candidates": [],
        "candidate_pool": [],
        "place_info_list": [],
    }
