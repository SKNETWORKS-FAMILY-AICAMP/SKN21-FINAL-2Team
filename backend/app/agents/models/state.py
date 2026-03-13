from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages
from app.agents.models.output import IntentType, IntentSlots, PlannerNeedType
from langchain_core.messages import BaseMessage

class TravelState(TypedDict, total=False):
    _node_name: str

    # input data
    user_id: int  # User ID만 전달 (intent에서 DB 조회)
    room_id: int

    input_lat: float | None
    input_long: float | None
    input_image: str | None

    # 대화 관리
    user_input: str
    messages: Annotated[List[BaseMessage], add_messages]
    
    # intent
    intents: List[IntentType]
    primary_intent: IntentType
    slots: IntentSlots
    update_user_input: str | None
    summary_title: str
    summary_message: str
    user_preferences: Dict[str, Any]           # 선호도 조사
    prefs_info: str
    
    # planner
    itinerary: List[Dict[str, Any]]         # 시간순/일차별 정렬된 데이터
    
    # retriever
    candidate_k: int
    final_k: int
    rerank_max_k: int
    candidate_pool: List[Dict[str, Any]]      # 검색된 TopK 후보 풀
    candidates: List[Dict[str, Any]]          # 최종 노출용 TopN 후보
    retrieval_diagnostics: Dict[str, Any]     # 채널별 hit/점수/순위 진단 정보
    selection_mode: str                       # deterministic | explore

    # final
    follow_up_questions: List[str]          # LLM이 생성한 후속 질문 목록   
    missing_slots: List[PlannerNeedType]                # 다음 단계 진행을 위해 추가로 사용자에게 물어봐야 하는 slot 목록 (필수 정보들만 재질문)
    answer: str
    selected_ids: List[str]                 # LLM이 최종 답변에서 선택한 장소들의 contentid 목록


def get_effective_user_input(state: TravelState) -> str:
    return (state.get("update_user_input") or state.get("user_input") or "").strip()
