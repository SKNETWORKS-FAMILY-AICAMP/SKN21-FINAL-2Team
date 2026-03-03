from types import SimpleNamespace

import pytest

from app.retrieval.place import (
    PHOTOS_COLLECTION,
    PLACES_COLLECTION,
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
