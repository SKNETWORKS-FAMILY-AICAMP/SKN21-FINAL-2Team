from types import SimpleNamespace

import pytest

from app.retrieval.place import PHOTOS_COLLECTION, PLACES_COLLECTION, PlaceRetriever, retrieval_place
from app.schemas.chat import ChatMessageCreate


def test_extract_place_id_uses_contentid_for_photo_points():
    photo_point = SimpleNamespace(id="photo-uuid", payload={"contentid": "1234"})
    place_point = SimpleNamespace(id=5678, payload={"contentid": "5678"})

    assert PlaceRetriever.get_instance()._extract_place_id(photo_point, PHOTOS_COLLECTION) == 1234
    assert PlaceRetriever.get_instance()._extract_place_id(place_point, PLACES_COLLECTION) == 5678


@pytest.mark.asyncio
async def test_retrieval_place_returns_empty_when_retriever_init_fails(monkeypatch):
    def _raise_init_error():
        raise RuntimeError("init error")

    monkeypatch.setattr(PlaceRetriever, "get_instance", staticmethod(_raise_init_error))

    message = ChatMessageCreate(message="테스트", room_id=1)
    context, results = await retrieval_place(message)

    assert context is None
    assert results == []
