import pytest
from types import SimpleNamespace

from app.agents.models.output import InputType, IntentType
from app.agents.retriever import _candidate_category, _pick_candidates, _resolve_search_scope, retriever_node
from app.utils.config import get_retrieval_params


def test_candidate_category_prefers_contenttypeid():
    candidate = {
        "payload": {
            "contenttypeid": "음식점",
            "category": "관광지",
        }
    }
    assert _candidate_category(candidate) == "음식점"


def test_pick_candidates_deterministic_is_stable():
    candidates = [
        {"id": "1", "score": 0.9, "payload": {"contenttypeid": "음식점"}},
        {"id": "2", "score": 0.8, "payload": {"contenttypeid": "관광지"}},
        {"id": "3", "score": 0.7, "payload": {"contenttypeid": "문화시설"}},
        {"id": "4", "score": 0.6, "payload": {"contenttypeid": "음식점"}},
    ]

    out1 = _pick_candidates(candidates, final_k=3, top_pool=4, selection_mode="deterministic")
    out2 = _pick_candidates(candidates, final_k=3, top_pool=4, selection_mode="deterministic")

    assert [c["id"] for c in out1] == [c["id"] for c in out2]


def test_resolve_search_scope_trip_planning_is_place_only():
    scope = _resolve_search_scope(
        primary_intent=IntentType.TRIP_PLANNING,
        slots=SimpleNamespace(input_type=InputType.BOTH),
        image_path="/tmp/a.jpg",
    )
    assert scope == "place_only"


def test_resolve_search_scope_image_query_uses_photo_only():
    scope = _resolve_search_scope(
        primary_intent=IntentType.PLACE_INQUIRY,
        slots=SimpleNamespace(input_type=InputType.IMAGE),
        image_path="/tmp/a.jpg",
    )
    assert scope == "photo_only"


def test_resolve_search_scope_without_image_falls_back_place_only():
    scope = _resolve_search_scope(
        primary_intent=IntentType.IMAGE_SIMILAR,
        slots=SimpleNamespace(input_type=InputType.IMAGE),
        image_path=None,
    )
    assert scope == "place_only"


def test_retrieval_profile_serving_defaults():
    params = get_retrieval_params("serving")
    assert params["candidate_k"] == 20
    assert params["top_k"] == 5
    assert params["rerank_max_k"] == 8


def test_retrieval_profile_evaluation_defaults():
    params = get_retrieval_params("evaluation")
    assert params["candidate_k"] == 60
    assert params["top_k"] == 10
    assert params["rerank_max_k"] == 30


@pytest.mark.asyncio
async def test_retriever_node_dedup_uses_payload_contentid(monkeypatch):
    async def _fake_general_search(*_args, **_kwargs):
        return [
            {"id": "photo-uuid-1", "score": 0.95, "payload": {"contentid": "100", "contenttypeid": "음식점"}},
            {"id": "100", "score": 0.90, "payload": {"contentid": "100", "contenttypeid": "음식점"}},
            {"id": "200", "score": 0.80, "payload": {"contentid": "200", "contenttypeid": "관광지"}},
        ]

    monkeypatch.setattr("app.agents.retriever._search_for_general", _fake_general_search)

    state = {
        "user_input": "추천해줘",
        "primary_intent": IntentType.PLACE_INQUIRY,
        "candidate_k": 5,
        "final_k": 3,
        "rerank_max_k": 5,
    }

    result = await retriever_node(state)
    assert len(result["candidates"]) == 2
    ids = {str((c.get("payload") or {}).get("contentid", "")).strip() for c in result["candidates"]}
    assert ids == {"100", "200"}
