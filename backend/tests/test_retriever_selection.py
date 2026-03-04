from app.agents.retriever import _candidate_category, _pick_candidates


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
