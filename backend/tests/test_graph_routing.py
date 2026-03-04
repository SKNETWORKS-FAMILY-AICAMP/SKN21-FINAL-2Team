from app.agents.grapy_route import route_by_missing


def test_route_by_missing_routes_to_executor_missing_when_any_missing():
    result = route_by_missing({"missing_slots": ["location"]})
    assert result.node == "executor_missing"


def test_route_by_missing_routes_to_retriever_when_no_missing():
    result = route_by_missing({"missing_slots": []})
    assert result.node == "retriever"
