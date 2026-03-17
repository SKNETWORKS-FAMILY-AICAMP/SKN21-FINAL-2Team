"""
LangGraph 파이프라인 SSE 이벤트 발화 검증 테스트

실제 그래프를 stub 노드로 컴파일하고 astream_events를 실행해서
on_chain_start / on_chain_end 이벤트가 각 노드마다 정상적으로 발화하는지 확인한다.
"""

import pytest
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.models.state import TravelState
from app.agents.models.output import IntentType
from app.agents.grapy_route import route_by_intent, route_after_retriever


# ──────────────────────────────────────────────
# Stub 노드 — 실제 LLM/DB 호출 없이 최소한의 상태만 반환
# ──────────────────────────────────────────────

async def stub_intent(state: TravelState):
    return {
        "primary_intent": IntentType.PLACE_INQUIRY,
        "intents": [IntentType.PLACE_INQUIRY],
        "update_user_input": "홍대 카페 추천",
        "summary_title": "홍대 카페",
        "summary_message": "홍대 카페 추천 요청",
        "input_tags": ["홍대", "카페"],
        "context_place": None,
        "place_info_list": [],
    }

async def stub_geocoder(state: TravelState):
    return {
        "location_anchor_lat": 37.5563,
        "location_anchor_lon": 126.9236,
        "location_anchor_radius_m": 1000.0,
        "input_address": None,
    }

async def stub_retriever(state: TravelState):
    retry_count = int(state.get("retriever_retry_count") or 0) + 1
    return {
        "candidates": [{"name": "테스트 카페", "score": 0.9}],
        "candidate_pool": [],
        "retrieval_diagnostics": {},
        "retriever_retry_count": retry_count,
    }

async def stub_executor(state: TravelState):
    return {
        "answer": "홍대 카페 추천드립니다.",
        "place_info_list": [],
    }

async def stub_executor_general(state: TravelState):
    return {
        "answer": "일반 답변입니다.",
        "place_info_list": [],
    }

async def stub_executor_missing(state: TravelState):
    return {
        "answer": "추가 정보가 필요합니다.",
        "place_info_list": [],
    }

async def stub_planner(state: TravelState):
    return {
        "itinerary": [],
        "missing_slots": [],
    }

async def stub_web_search(state: TravelState):
    return {
        "web_search_places": [],
        "web_search_context": "웹 검색 결과 없음",
        "candidates": [],
    }


def build_stub_graph():
    graph = StateGraph(TravelState)
    graph.add_node("intent", stub_intent)
    graph.add_node("planner", stub_planner)
    graph.add_node("geocoder", stub_geocoder)
    graph.add_node("retriever", stub_retriever)
    graph.add_node("web_search", stub_web_search)
    graph.add_node("executor", stub_executor)
    graph.add_node("executor_missing", stub_executor_missing)
    graph.add_node("executor_general", stub_executor_general)

    graph.set_entry_point("intent")
    graph.add_conditional_edges("intent", route_by_intent)
    from app.agents.grapy_route import route_by_missing
    graph.add_conditional_edges("planner", route_by_missing)
    graph.add_edge("geocoder", "retriever")
    graph.add_conditional_edges("retriever", route_after_retriever)
    graph.add_edge("web_search", "executor")
    graph.add_edge("executor", END)
    graph.add_edge("executor_missing", END)
    graph.add_edge("executor_general", END)

    return graph.compile(checkpointer=MemorySaver())


def _resolve_node_name(event: dict) -> str | None:
    """on_chain_start/end 이벤트에서 langgraph 노드 이름 추출"""
    metadata = event.get("metadata") or {}
    node = metadata.get("langgraph_node")
    if isinstance(node, str) and node:
        return node
    tags = event.get("tags") or []
    for tag in tags:
        if isinstance(tag, str) and tag.startswith("langgraph:node:"):
            return tag[len("langgraph:node:"):]
    return None


async def collect_step_events(graph_app, inputs: dict, config: dict) -> list[dict]:
    """astream_events에서 on_chain_start/end 노드 이벤트만 수집.

    라우팅 함수(route_by_intent 등)는 이전 노드의 langgraph_node 메타데이터를 갖고
    발화하므로 event["name"] == node_name 조건으로 실제 노드 이벤트만 필터링한다.
    """
    graph_nodes = {name for name in graph_app.nodes if not name.startswith("__")}
    events = []
    async for event in graph_app.astream_events(inputs, config=config, version="v2"):
        kind = event.get("event", "")
        if kind not in ("on_chain_start", "on_chain_end"):
            continue
        node_name = _resolve_node_name(event)
        event_func_name = event.get("name", "")
        # 실제 노드 이벤트만 수집 (라우팅 함수 이벤트 제외)
        if node_name and node_name in graph_nodes and event_func_name == node_name:
            events.append({"kind": kind, "node": node_name})
    return events


# ──────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_events_place_inquiry_path():
    """PLACE_INQUIRY 경로: intent → geocoder → retriever → executor 순으로 이벤트 발화 확인"""
    graph_app = build_stub_graph()
    inputs = TravelState(
        user_input="홍대 카페 추천해줘",
        messages=[],
        prefs_info="",
        summary_title="새 채팅",
        summary_message="",
        candidates=[],
        candidate_pool=[],
        retrieval_diagnostics={},
        answer="",
    )
    config = {"configurable": {"thread_id": "test-place-inquiry"}}
    events = await collect_step_events(graph_app, inputs, config)

    start_nodes = [e["node"] for e in events if e["kind"] == "on_chain_start"]
    done_nodes  = [e["node"] for e in events if e["kind"] == "on_chain_end"]

    print(f"\n[TEST] on_chain_start 순서: {start_nodes}")
    print(f"[TEST] on_chain_end  순서: {done_nodes}")

    # 핵심: intent → geocoder → retriever → executor 순으로 start 이벤트 발화
    assert "intent"   in start_nodes, "intent on_chain_start 누락"
    assert "geocoder" in start_nodes, "geocoder on_chain_start 누락"
    assert "retriever" in start_nodes, "retriever on_chain_start 누락"
    assert "executor" in start_nodes, "executor on_chain_start 누락"

    # 순서 검증
    idx = {node: start_nodes.index(node) for node in ["intent", "geocoder", "retriever", "executor"]}
    assert idx["intent"]   < idx["geocoder"],  "intent이 geocoder보다 먼저여야 함"
    assert idx["geocoder"] < idx["retriever"], "geocoder가 retriever보다 먼저여야 함"
    assert idx["retriever"] < idx["executor"], "retriever가 executor보다 먼저여야 함"

    # done 이벤트도 각 노드마다 존재해야 함
    assert "intent"   in done_nodes, "intent on_chain_end 누락"
    assert "geocoder" in done_nodes, "geocoder on_chain_end 누락"
    assert "retriever" in done_nodes, "retriever on_chain_end 누락"
    assert "executor" in done_nodes, "executor on_chain_end 누락"


@pytest.mark.asyncio
async def test_pipeline_events_general_path():
    """GENERAL 경로: intent → executor_general (geocoder/retriever 스킵)"""
    graph_app = build_stub_graph()

    # intent가 GENERAL을 반환하도록 stub 교체
    async def stub_intent_general(state: TravelState):
        return {
            "primary_intent": IntentType.GENERAL,
            "intents": [IntentType.GENERAL],
            "update_user_input": "안녕",
            "summary_title": "인사",
            "summary_message": "",
            "input_tags": [],
            "context_place": None,
            "place_info_list": [],
        }

    # 그래프를 GENERAL intent stub으로 재빌드
    graph = StateGraph(TravelState)
    graph.add_node("intent", stub_intent_general)
    graph.add_node("planner", stub_planner)
    graph.add_node("geocoder", stub_geocoder)
    graph.add_node("retriever", stub_retriever)
    graph.add_node("web_search", stub_web_search)
    graph.add_node("executor", stub_executor)
    graph.add_node("executor_missing", stub_executor_missing)
    graph.add_node("executor_general", stub_executor_general)
    graph.set_entry_point("intent")
    graph.add_conditional_edges("intent", route_by_intent)
    from app.agents.grapy_route import route_by_missing
    graph.add_conditional_edges("planner", route_by_missing)
    graph.add_edge("geocoder", "retriever")
    graph.add_conditional_edges("retriever", route_after_retriever)
    graph.add_edge("web_search", "executor")
    graph.add_edge("executor", END)
    graph.add_edge("executor_missing", END)
    graph.add_edge("executor_general", END)
    app = graph.compile(checkpointer=MemorySaver())

    inputs = TravelState(
        user_input="안녕",
        messages=[],
        prefs_info="",
        summary_title="새 채팅",
        summary_message="",
        candidates=[],
        candidate_pool=[],
        retrieval_diagnostics={},
        answer="",
    )
    config = {"configurable": {"thread_id": "test-general"}}
    events = await collect_step_events(app, inputs, config)

    start_nodes = [e["node"] for e in events if e["kind"] == "on_chain_start"]
    print(f"\n[TEST] GENERAL 경로 on_chain_start 순서: {start_nodes}")

    assert "intent" in start_nodes
    assert "executor_general" in start_nodes
    assert "geocoder" not in start_nodes, "GENERAL 경로에서 geocoder가 실행되면 안 됨"
    assert "retriever" not in start_nodes, "GENERAL 경로에서 retriever가 실행되면 안 됨"

    idx = {node: start_nodes.index(node) for node in ["intent", "executor_general"]}
    assert idx["intent"] < idx["executor_general"]
