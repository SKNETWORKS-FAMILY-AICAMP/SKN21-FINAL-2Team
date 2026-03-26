from app.core.retrieval.place import PlaceRetriever
from app.utils.config import BOOST_WEIGHT, FUSED_SCORE_MAX, MAX_BOOST_SUM, RRF_SCORE_MAX


def test_fuse_and_boost_returns_absolute_normalized_scores():
    retriever = PlaceRetriever.__new__(PlaceRetriever)

    score_map = {
        "p1": {
            "score": 0.04,
            "payload": {"title": "테스트 카페", "addr": "서울특별시 마포구"},
            "matches": {"text_semantic"},
        },
        "p2": {
            "score": 0.02,
            "payload": {"title": "다른 카페", "addr": "서울특별시 서대문구"},
            "matches": {"bm25_lexical"},
        },
    }

    retriever._extract_query_addr_tokens = lambda _query: []
    retriever._keyword_match_bonus = lambda **_kwargs: 0.02
    retriever._location_text_bonus = lambda **_kwargs: 0.01
    retriever._geo_proximity_bonus = lambda **_kwargs: 0.0
    retriever._payload_addr_tokens = lambda _payload: []
    retriever._addr_sparse_bonus = lambda **_kwargs: 0.0
    retriever._tag_match_bonus = lambda **_kwargs: 0.0

    results = retriever._fuse_and_boost(
        score_map=score_map,
        query="마포 카페",
        preferred_location="마포구",
        categories=None,
        input_tags=None,
        prox_lat=None,
        prox_lon=None,
    )

    assert [item["id"] for item in results] == ["p1", "p2"]

    expected_boost = 0.03
    expected_p1_score = min(1.0, (0.04 + BOOST_WEIGHT * expected_boost) / FUSED_SCORE_MAX)
    expected_p2_score = min(1.0, (0.02 + BOOST_WEIGHT * expected_boost) / FUSED_SCORE_MAX)

    assert results[0]["first_stage_score"] == round(0.04 / RRF_SCORE_MAX, 4)
    assert results[1]["first_stage_score"] == round(0.02 / RRF_SCORE_MAX, 4)
    assert results[0]["score"] == round(expected_p1_score, 4)
    assert results[1]["score"] == round(expected_p2_score, 4)
    assert results[0]["score_boost_total"] == round(expected_boost / MAX_BOOST_SUM, 4)
    assert results[1]["score_boost_total"] == round(expected_boost / MAX_BOOST_SUM, 4)


def test_fuse_and_boost_caps_absolute_normalized_scores_at_one():
    retriever = PlaceRetriever.__new__(PlaceRetriever)

    score_map = {
        "p1": {
            "score": 0.5,
            "payload": {"title": "고득점 장소", "addr": "서울특별시 강남구"},
            "matches": set(),
        }
    }

    retriever._extract_query_addr_tokens = lambda _query: []
    retriever._keyword_match_bonus = lambda **_kwargs: 1.0
    retriever._location_text_bonus = lambda **_kwargs: 0.0
    retriever._geo_proximity_bonus = lambda **_kwargs: 0.0
    retriever._payload_addr_tokens = lambda _payload: []
    retriever._addr_sparse_bonus = lambda **_kwargs: 0.0
    retriever._tag_match_bonus = lambda **_kwargs: 0.0

    results = retriever._fuse_and_boost(
        score_map=score_map,
        query="강남",
        preferred_location=None,
        categories=None,
        input_tags=None,
        prox_lat=None,
        prox_lon=None,
    )

    assert results[0]["score"] == 1.0
    assert results[0]["first_stage_score"] == 1.0
    assert results[0]["score_boost_total"] == round(min(1.0, 1.0 / MAX_BOOST_SUM), 4)
