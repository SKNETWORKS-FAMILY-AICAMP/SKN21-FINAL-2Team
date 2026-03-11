from langgraph.types import Send

from app.agents.models.state import TravelState
from app.agents.models.output import IntentType

def route_by_intent(state: TravelState):
    next_node = 'retriever'
    
    if state['primary_intent'] == IntentType.TRIP_PLANNING:
        next_node = 'planner'
    elif state['primary_intent'] == IntentType.GENERAL:
        next_node = 'executor_general'

    return next_node


def route_by_missing(state: TravelState):
    next_node = 'retriever'
    missing = state.get('missing_slots', [])
    
    # 누락 슬롯이 1개라도 있으면 검색/추천으로 진행하지 않고 재질문 우선
    if len(missing) > 0:
        next_node = 'executor_missing'

    return next_node
