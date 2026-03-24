from app.agents.models.state import TravelState
from app.agents.models.output import IntentType


def route_by_intent(state: TravelState):
    """intent 노드 이후 라우팅.

    - TRIP_PLANNING  → planner
    - GENERAL/chitchat → executor_general
    - 그 외(여행 관련) → geocoder (위치 anchor 확인 후 retriever)

    복합 의도(multi-intent) 처리:
    - intents 리스트에 TRIP_PLANNING이 포함된 경우 planner 우선
      (예: "K-pop 댄스 클래스 찾아서 일정에 넣어줘" → [PLACE_INQUIRY, TRIP_PLANNING])
    """
    primary_intent = state["primary_intent"]
    intents = state.get("intents") or []

    # GENERAL은 항상 우선 차단 (안전 처리)
    if primary_intent == IntentType.GENERAL:
        return "executor_general"

    # 복합 의도: intents 리스트에 TRIP_PLANNING이 있으면 planner로 라우팅
    if IntentType.TRIP_PLANNING in intents:
        return "planner"

    return "geocoder"


def route_by_missing(state: TravelState):
    """planner 노드 이후 라우팅.

    - missing_slots 있음 → executor_missing (재질문)
    - missing_slots 없음 → geocoder (pinned_places geo 확보 + 위치 anchor 확인)
      * is_auto_start=True: geocoder → executor (retriever 건너뜀)
      * is_auto_start=False: geocoder → retriever → executor
    """
    missing = state.get("missing_slots", [])
    if len(missing) > 0:
        return "executor_missing"

    return "geocoder"


def route_after_geocoder(state: TravelState):
    """geocoder 노드 이후 라우팅.

    - is_auto_start=True → executor (retriever 건너뜀: pinned_places geo만 확보 후 초안 응답)
    - 그 외 → retriever
    """
    if state.get("is_auto_start"):
        return "executor"
    return "retriever"


def route_after_retriever(state: TravelState):
    """retriever 실행 후 라우팅.

    retriever_retry_count 는 retriever_node 에서 매 실행 후 +1 되어 반환된다.
    ─ count=1 : 초회 완료 → 재시도 가능
    ─ count=2 : 재시도 완료 → 결과 없으면 web_search 로 넘김
    """
    candidates = state.get("candidates") or []
    retry_count = int(state.get("retriever_retry_count") or 0)

    if candidates:
        return "executor"

    if retry_count <= 1:
        # 초회(count=1)이고 결과 없음 → 확장 반경으로 재시도
        print(f"[Route] retriever returned 0 candidates (retry_count={retry_count}), routing back to retriever")
        return "retriever"

    # 재시도 후에도 결과 없음 → Naver Local Search fallback
    print(f"[Route] retriever returned 0 candidates after retry (retry_count={retry_count}), routing to web_search")
    return "web_search"
