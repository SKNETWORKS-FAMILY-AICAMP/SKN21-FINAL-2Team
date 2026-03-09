import asyncio
from types import SimpleNamespace

from qdrant_client.models import FieldCondition, Filter, IsEmptyCondition, MatchAny

from app.retrieval.place import PlaceRetriever, _build_compact_text
from app.utils.config import get_retrieval_params


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


def test_build_compact_text_uses_title_category_addr_only():
    payload = {
        "title": "강남 맛집",
        "contenttypeid": "음식점",
        "addr": "서울 강남구",
        "description": "긴 설명",
        "llm_text": "더 긴 설명",
    }

    compact = _build_compact_text(payload)

    assert compact == "강남 맛집 음식점 서울 강남구"
    assert "설명" not in compact


def test_bm25_lexical_scores_only_given_candidates():
    retriever = object.__new__(PlaceRetriever)
    retriever.normalize_category = lambda category: category

    candidates = [
        SimpleNamespace(id=1, payload={"title": "강남 맛집", "contenttypeid": "음식점", "addr": "서울 강남구"}),
        SimpleNamespace(id=2, payload={"title": "제주 카페", "contenttypeid": "음식점", "addr": "제주"}),
    ]

    out = asyncio.run(
        retriever._search_bm25_lexical(
            query="강남 맛집",
            category=None,
            candidate_points=candidates,
            candidate_k=2,
            pool_limit=2,
        )
    )

    assert len(out) >= 1
    assert out[0]["id"] == 1


def test_build_category_filter_uses_normalized_and_raw_category_with_or_matching():
    retriever = object.__new__(PlaceRetriever)

    query_filter = retriever._build_category_filter("맛집")

    assert isinstance(query_filter, Filter)
    assert len(query_filter.must) == 1
    category_filter = query_filter.must[0]
    assert isinstance(category_filter, FieldCondition)
    assert category_filter.key == "contenttypeid"
    assert isinstance(category_filter.match, MatchAny)
    assert set(category_filter.match.any) == {"음식점", "맛집"}


def test_build_category_filter_falls_back_to_raw_category_when_not_normalized():
    retriever = object.__new__(PlaceRetriever)

    query_filter = retriever._build_category_filter("브런치")

    assert isinstance(query_filter, Filter)
    assert len(query_filter.must) == 1
    category_filter = query_filter.must[0]
    assert isinstance(category_filter, FieldCondition)
    assert category_filter.key == "contenttypeid"
    assert isinstance(category_filter.match, MatchAny)
    assert set(category_filter.match.any) == {"브런치"}


def test_build_category_filter_adds_must_not_when_has_image_true():
    retriever = object.__new__(PlaceRetriever)

    query_filter = retriever._build_category_filter("맛집", has_image=True)

    assert isinstance(query_filter, Filter)
    assert len(query_filter.must) == 1
    assert len(query_filter.must_not) == 1
    assert isinstance(query_filter.must_not[0], IsEmptyCondition)


def test_payload_matches_category_accepts_raw_category_field_fallback():
    retriever = object.__new__(PlaceRetriever)

    assert retriever._payload_matches_category({"category": "브런치"}, "브런치") is True
    assert retriever._payload_matches_category({"contenttypeid": "브런치"}, "브런치") is True
    assert retriever._payload_matches_category({"contenttypeid": "음식점"}, "맛집") is True
    assert retriever._payload_matches_category({"category": "카페"}, "맛집") is False


def test_search_hybrid_caps_rerank_top_k_to_serving_profile():
    retriever = object.__new__(PlaceRetriever)
    retriever._build_category_filter = lambda category=None, has_image=False: None
    retriever.text_model = SimpleNamespace(encode=lambda text: [0.1, 0.2, 0.3])
    retriever.vision_model = SimpleNamespace(encode=lambda text: [0.1, 0.2, 0.3])
    retriever.client = SimpleNamespace(
        query_points=lambda **kwargs: SimpleNamespace(
            points=[
                SimpleNamespace(
                    id=1,
                    payload={"contentid": "1", "title": "A", "contenttypeid": "음식점", "addr": "서울"},
                    score=0.3,
                )
            ]
        )
    )

    captured = {"top_k": None}

    async def _fake_rerank(query, candidates, top_k):
        captured["top_k"] = top_k
        for idx, c in enumerate(candidates, start=1):
            c["final_rank"] = idx
            c["rerank_score"] = 0.0
        return candidates[:top_k]

    retriever._rerank_candidates = _fake_rerank

    out = asyncio.run(
        retriever.search_hybrid(
            query="강남 맛집",
            limit=5,
            candidate_k=30,
            enable_bm25=False,
            enable_rerank=True,
            rerank_top_k=30,
            search_scope="place_only",
        )
    )

    assert captured["top_k"] == get_retrieval_params("serving")["rerank_max_k"]
    assert len(out) == 1


def test_search_nearby_uses_geo_filter_when_enabled(monkeypatch):
    retriever = object.__new__(PlaceRetriever)
    captured = {"scroll_filter": None}

    def _fake_scroll(**kwargs):
        captured["scroll_filter"] = kwargs.get("scroll_filter")
        point = SimpleNamespace(
            id=1,
            payload={"geo": {"lat": 37.5666, "lon": 126.9781}, "title": "A"},
        )
        return [point], None

    retriever.client = SimpleNamespace(scroll=_fake_scroll)
    monkeypatch.setattr("app.retrieval.place.ENABLE_GEO_FILTER", True)

    out = retriever.search_nearby(37.5665, 126.9780, limit=3, radius_km=5.0)

    assert captured["scroll_filter"] is not None
    assert len(out) == 1
    assert out[0]["id"] == 1


def test_search_nearby_falls_back_when_geo_filter_fails(monkeypatch):
    retriever = object.__new__(PlaceRetriever)
    calls = {"count": 0}

    def _fake_scroll(**kwargs):
        calls["count"] += 1
        if kwargs.get("scroll_filter") is not None:
            raise RuntimeError("geo filter error")
        point = SimpleNamespace(
            id=2,
            payload={"mapy": "37.5667", "mapx": "126.9782", "title": "B"},
        )
        return [point], None

    retriever.client = SimpleNamespace(scroll=_fake_scroll)
    monkeypatch.setattr("app.retrieval.place.ENABLE_GEO_FILTER", True)

    out = retriever.search_nearby(37.5665, 126.9780, limit=3, radius_km=5.0)

    assert calls["count"] == 2
    assert len(out) == 1
    assert out[0]["id"] == 2


def test_search_hybrid_includes_qdrant_sparse_channel_when_enabled(monkeypatch):
    retriever = object.__new__(PlaceRetriever)
    retriever._build_category_filter = lambda category=None, has_image=False: None
    retriever.text_model = SimpleNamespace(encode=lambda text: [0.1, 0.2, 0.3])
    retriever.vision_model = SimpleNamespace(encode=lambda text: [0.1, 0.2, 0.3])
    calls = {"using": []}

    def _fake_query_points(**kwargs):
        calls["using"].append(kwargs.get("using"))
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id=1,
                    payload={"contentid": "1", "title": "A", "contenttypeid": "음식점", "addr_tokens": ["강남구", "강남"]},
                    score=0.3,
                )
            ]
        )

    retriever.client = SimpleNamespace(query_points=_fake_query_points)

    monkeypatch.setattr("app.retrieval.place.ENABLE_QDRANT_SPARSE", True)

    out = asyncio.run(
        retriever.search_hybrid(
            query="강남구 맛집",
            limit=5,
            candidate_k=10,
            enable_bm25=False,
            enable_rerank=False,
            search_scope="place_only",
        )
    )

    assert "text_sparse" in calls["using"]
    assert any("qdrant_sparse" in c.get("match_types", []) for c in out)
