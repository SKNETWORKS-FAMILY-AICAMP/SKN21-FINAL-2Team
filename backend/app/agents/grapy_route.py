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