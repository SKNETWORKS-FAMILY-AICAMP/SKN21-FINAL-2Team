from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.models.output import IntentOutput, IntentType, IntentSlots, InputType
from app.services.prompts import INTENT_PROMPT
from app.agents.models.state import TravelState
from app.utils.llm_factory import LLMFactory

from app.models.user import User


def _build_user_preferences(user: User) -> Dict[str, Any]:
    """
    DB에서 사용자 선호도 가져오기
    """
    lines = []
    
    if user.with_yn:
        lines.append("- 👫 동행인이 있는 여행을 좋아합니다.")
    if user.dog_yn:
        lines.append("- 🐶 **반려견 동반 여행**을 선호합니다. 애견 동반 가능한 장소를 우선 추천해주세요.")
    if user.vegan_yn:
        lines.append("- 🥗 **비건(채식)** 식단을 선호합니다. 비건 메뉴가 있는 식당을 찾아주세요.")
    if user.actor_prefer:
        lines.append(f"- 🎬 좋아하는 배우: **{user.actor_prefer}** (관련 촬영지, 명소 추천 시 강조)")
    if user.movie_prefer:
        lines.append(f"- 🎥 좋아하는 영화: **{user.movie_prefer}** (촬영지 방문 희망)")
    if user.drama_prefer:
        lines.append(f"- 📺 좋아하는 드라마: **{user.drama_prefer}** (드라마 촬영지 방문 희망)")
    if user.celeb_prefer:
        lines.append(f"- ⭐ 좋아하는 셀럽: **{user.celeb_prefer}**")
    if user.variety_prefer:
        lines.append(f"- 📺 좋아하는 예능: **{user.variety_prefer}** (관련 촬영지 추천)")
    
    return "\n".join(lines) if lines else "특별한 선호도 정보 없음"


def intent_node(state: TravelState):
    """
    사용자 의도 분석 Agent
    """
    print("--- Intent Agent ---")

    # DB에서 사용자 프로필 가져오기
    user = state.get("user")
    prefs_info = _build_user_preferences(user)
    
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
    result = chain.invoke({
        "messages": messages, 
        "user_input": user_input
    })

    print("Intent Result : ", result)

    # State에 결과 저장
    # llm 결과와 db 프로필을 모두 포함
    return {
        "intents": result.intents,
        "primary_intent": result.primary_intent,
        "slots": result.slots,
        "prefs_info": prefs_info
    }

