from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages
from app.agents.models.output import IntentType, IntentSlots
from langchain_core.messages import BaseMessage
from app.models.user import User

class TravelState(TypedDict, total=False):
    _node_name: str

    # input data
    user: User
    room_id: int
    latitude: float | None
    longitude: float | None
    image_path: str | None

    # 대화 관리
    user_input: str
    messages: Annotated[List[BaseMessage], add_messages]
    
    # intent
    intents: List[IntentType]
    primary_intent: IntentType
    slots: IntentSlots
    user_preferences: Dict[str, Any]           # 선호도 조사
    prefs_info: str
    
    # planner
    itinerary: List[Dict[str, Any]]         # 시간순/일차별 정렬된 데이터
    
    # retriever
    candidates: List[Dict[str, Any]]      # 검색된 장소 및 식당 리스트

    # final
    missing_slots: List[str]                # 다음 단계 진행을 위해 추가로 사용자에게 물어봐야 하는 slot 목록 (필수 정보들만 재질문)
    answer: str
