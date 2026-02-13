from langgraph.graph import StateGraph, END
from backend.app.schemas.agent_state import State

def workflow():
    graph = StateGraph(State)
    return graph

if __name__ == '__main__':
    graph = workflow()
    app = graph.compile()
