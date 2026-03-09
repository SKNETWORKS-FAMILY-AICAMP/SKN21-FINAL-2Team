from types import SimpleNamespace

import pytest

from app.retrieval.place import (
    PHOTOS_COLLECTION,
    PLACES_COLLECTION,
    PlaceRetriever,
    _extract_place_id,
    _fetch_photo_urls_by_contentids,
    retrieval_place,
)
from app.schemas.chat import ChatMessageCreate


def test_extract_place_id_uses_contentid_for_photo_points():
    photo_point = SimpleNamespace(id="photo-uuid", payload={"contentid": "1234"})
    place_point = SimpleNamespace(id=5678, payload={"contentid": "5678"})

    assert _extract_place_id(photo_point, PHOTOS_COLLECTION) == 1234
    assert _extract_place_id(place_point, PLACES_COLLECTION) == 5678


@pytest.mark.asyncio
async def test_retrieval_place_returns_empty_when_retriever_init_fails(monkeypatch):
    from app.retrieval.place import PlaceRetriever

    def _raise_init_error():
        raise RuntimeError("init error")

    monkeypatch.setattr(PlaceRetriever, "get_instance", staticmethod(_raise_init_error))

    message = ChatMessageCreate(message="테스트", room_id=1)
    context, results = await retrieval_place(message)

    assert context is None
    assert results == []


@pytest.mark.asyncio
async def test_fetch_photo_urls_by_contentids_batches_and_groups():
    point1 = SimpleNamespace(payload={"contentid": "1", "image_url": "https://img/1-a.jpg"})
    point2 = SimpleNamespace(payload={"contentid": "1", "image_url": "https://img/1-b.jpg"})
    point3 = SimpleNamespace(payload={"contentid": "2", "image_url": "https://img/2-a.jpg"})
    point4 = SimpleNamespace(payload={"contentid": "2", "image_url": "https://img/2-a.jpg"})  # duplicate

    def fake_scroll(**kwargs):
        return [point1, point2, point3, point4], None

    retriever = SimpleNamespace(client=SimpleNamespace(scroll=fake_scroll))
    photo_map = await _fetch_photo_urls_by_contentids(retriever, [1, 2], per_place=3)

    assert photo_map["1"] == ["https://img/1-a.jpg", "https://img/1-b.jpg"]
    assert photo_map["2"] == ["https://img/2-a.jpg"]


def test_keyword_match_bonus_boosts_when_title_in_query():
    retriever = PlaceRetriever.__new__(PlaceRetriever)
    payload = {"title": "성수족발", "addr": "서울특별시 성동구 아차산로7길 7"}

    bonus = retriever._keyword_match_bonus("성수족발 왜 유명해?", payload)

    assert bonus >= 0.18


def test_keyword_match_bonus_boosts_when_district_matches_address():
    retriever = PlaceRetriever.__new__(PlaceRetriever)
    payload = {"title": "어떤카페", "addr": "서울특별시 성북구 성북로 10"}

    bonus = retriever._keyword_match_bonus("성북동 조용한 카페 추천", payload)

    assert bonus >= 0.06


def test_location_text_bonus_boosts_when_slots_location_matches_payload():
    retriever = PlaceRetriever.__new__(PlaceRetriever)
    payload = {"title": "한강뷰 카페", "addr": "서울특별시 마포구 망원동 123-1"}

    bonus = retriever._location_text_bonus("망원동", payload)

    assert bonus > 0.0


def test_geo_proximity_bonus_gives_higher_score_to_nearby_place():
    retriever = PlaceRetriever.__new__(PlaceRetriever)
    near_payload = {"title": "가까운장소", "lat": 37.5666, "lng": 126.9781}
    far_payload = {"title": "먼장소", "lat": 37.4949, "lng": 127.0276}

    near_bonus = retriever._geo_proximity_bonus(
        payload=near_payload,
        anchor_lat=37.5665,
        anchor_lng=126.9780,
    )
    far_bonus = retriever._geo_proximity_bonus(
        payload=far_payload,
        anchor_lat=37.5665,
        anchor_lng=126.9780,
    )

    assert near_bonus > far_bonus
    assert near_bonus > 0.0


def test_addr_sparse_bonus_respects_exact_and_stem_weights():
    retriever = PlaceRetriever.__new__(PlaceRetriever)

    bonus = retriever._addr_sparse_bonus(
        query_addr_tokens=["성북동", "성북", "21-18"],
        payload_addr_tokens=["서울특별시", "성북동", "21-18"],
        max_boost=0.20,
        exact_weight=0.04,
        stem_weight=0.02,
    )

    assert bonus == pytest.approx(0.10, rel=1e-6)


def test_payload_coordinates_prefers_geo_field():
    retriever = PlaceRetriever.__new__(PlaceRetriever)

    lat, lng = retriever._payload_coordinates(
        {
            "geo": {"lat": 37.56, "lon": 126.97},
            "mapy": "1.0",
            "mapx": "1.0",
        }
    )

    assert lat == pytest.approx(37.56, rel=1e-6)
    assert lng == pytest.approx(126.97, rel=1e-6)
