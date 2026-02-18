from langgraph.graph import StateGraph, END
from app.agents.models.state import TravelState
from app.agents.grapy_route import route_by_intent

# Import Agent Nodes
from app.agents.intent import intent_node
from app.agents.planner import planner_node
from app.agents.retriever import retriever_node
from app.agents.executor import executor_node


def workflow():
    # Initialize Graph
    graph = StateGraph(TravelState)
    
    # Add Nodes
    graph.add_node("intent", intent_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("executor", executor_node)
    
    # Define Edges (Linear Flow)
    # planner -> context -> retriever -> budget -> executor -> END
    graph.set_entry_point("intent")
    graph.add_conditional_edges(
        "intent",
        route_by_intent,
    )
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "executor")
    graph.add_edge("executor", END)
    
    return graph


if __name__ == '__main__':
    graph = workflow()
    app = graph.compile()
    print("[INFO] Travel Agent Graph Compiled Successfully")
    
    # Optional: Test run if executed directly
    # inputs = {"user_input": "I want to go to Jeju next week with my friend for healing."}
    # result = app.invoke(inputs)
    # print(result.get("answer"))
