from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages
from app.agents.models.output import IntentType, IntentSlots, PlannerNeedType
from app.agents.models.place import PlaceInfo
from langchain_core.messages import BaseMessage

class TravelState(TypedDict, total=False):
    _node_name: str

    # input data
    user_id: int  # User ID만 전달 (intent에서 DB 조회)
    room_id: int
    prefs_info: str

    input_lat: float | None
    input_lon: float | None
    input_address: str | None  # 사용자 현재 위치
    input_image: str | None    # 사용자 입력 이미지
    semantic_input_image: str | None  # intent_node에서 describe_image로 분석한 이미지 설명

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
    input_tags: List[str]
    
    # planner
    itinerary: List[Dict[str, Any]]         # 시간순/일차별 정렬된 데이터
    pinned_places: List[Dict[str, Any]]     # auto_start 선택 장소 (반드시 일정에 포함)
    is_auto_start: bool                     # auto_start 엔드포인트에서 시작된 요청 여부
    
    # geocoder
    location_anchor_lat: float | None         # LANDMARK_DICTIONARY 또는 Naver API로 확정된 anchor 위도
    location_anchor_lon: float | None         # anchor 경도
    location_anchor_radius_m: float | None    # anchor 검색 반경(m)

    # retriever
    candidate_k: int
    final_k: int
    rerank_max_k: int
    candidate_pool: List[Dict[str, Any]]      # 검색된 TopK 후보 풀
    candidates: List[Dict[str, Any]]          # 최종 노출용 TopN 후보
    shown_place_ids: List[str]                # 대화 전체에서 이미 노출된 장소 ID 누적 목록
    retrieval_diagnostics: Dict[str, Any]     # 채널별 hit/점수/순위 진단 정보
    selection_mode: str                       # deterministic | explore
    retriever_retry_count: int                # 그래프 레벨 재검색 횟수 (0=초회, 1=재시도)

    # web_search (Qdrant 결과 없을 때 fallback)
    web_search_places: List[Any]              # web_search_node가 찾은 PlaceInfo 목록
    web_search_context: str | None            # web_search_node 결과 텍스트 컨텍스트

    # final
    follow_up_questions: List[str]          # LLM이 생성한 후속 질문 목록   
    missing_slots: List[PlannerNeedType]    # 다음 단계 진행을 위해 추가로 사용자에게 물어봐야 하는 slot 목록 (필수 정보들만 재질문)
    answer: str
    place_info_list: List[PlaceInfo]        # executor가 구성한 장소 정보 목록 (Qdrant/Tavily 통합)


def get_effective_user_input(state: TravelState) -> str:
    return (state.get("update_user_input") or state.get("user_input") or "").strip()

def get_slots_info(state: TravelState) -> str:
    slots_info = ""
    slots = state.get("slots")

    if slots:
        slots_dict = slots.model_dump() if hasattr(slots, 'model_dump') else (slots.dict() if hasattr(slots, 'dict') else slots)
        slots_info = "\n".join(f"- {k}: {v}" for k, v in slots_dict.items() if v is not None)

    return slots_info
