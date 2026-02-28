from langgraph.types import Send

from app.agents.models.state import TravelState
from app.agents.models.output import IntentType

def route_by_intent(state: TravelState):
    next_node = 'retriever'
    
    if state['primary_intent'] == IntentType.TRIP_PLANNING:
        next_node = 'planner'

    return Send(next_node,{
        **state,
        '_node_name': next_node
    })


def route_by_missing(state: TravelState):
    next_node = 'retriever'
    missing = state.get('missing_slots', [])
    
    if len(missing) > 2:
        next_node = 'executor_missing'

    return Send(next_node,{
        **state,
        '_node_name': next_node
    })