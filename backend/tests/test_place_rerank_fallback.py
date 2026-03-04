import asyncio

from app.retrieval.place import PlaceRetriever


def test_bm25_like_score_positive_for_matching_terms():
    retriever = object.__new__(PlaceRetriever)
    score = retriever._bm25_like_score(
        "강남 맛집",
        {
            "title": "강남 맛집 가게",
            "contenttypeid": "음식점",
            "addr": "서울특별시 강남구",
            "description": "맛집 추천",
        },
    )
    assert score > 0


def test_rerank_fallback_sets_final_rank_without_model():
    retriever = object.__new__(PlaceRetriever)
    retriever._reranker = None
    retriever._reranker_load_attempted = True

    candidates = [
        {"id": "1", "payload": {"title": "A"}, "score": 0.9},
        {"id": "2", "payload": {"title": "B"}, "score": 0.8},
    ]

    out = asyncio.run(retriever._rerank_candidates("질문", candidates, top_k=2))

    assert len(out) == 2
    assert out[0]["final_rank"] == 1
    assert out[1]["final_rank"] == 2
    assert out[0]["rerank_score"] is None
