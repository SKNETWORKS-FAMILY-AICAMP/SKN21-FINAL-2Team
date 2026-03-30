"""Tests for app.utils.qdrant_utils.scroll_random_places"""
from unittest.mock import MagicMock, patch

import pytest

from app.utils.qdrant_utils import scroll_random_places


def _make_point(point_id: int, title: str, addr: str, image: str):
    """테스트용 Qdrant ScoredPoint 대체 객체 생성."""
    p = MagicMock()
    p.id = point_id
    p.payload = {"title": title, "addr": addr, "image": image}
    return p


# ── 정상 케이스 ────────────────────────────────────────────────────────────────

def test_returns_formatted_results():
    """정상 포인트가 있으면 contentid/name/address/image 키를 반환해야 한다."""
    mock_client = MagicMock()
    points = [
        _make_point(1, "경복궁", "서울 종로구", "http://img/1.jpg"),
        _make_point(2, "북촌한옥마을", "서울 종로구", "http://img/2.jpg"),
        _make_point(3, "인사동", "서울 종로구", "http://img/3.jpg"),
    ]
    mock_client.scroll.return_value = (points, None)

    with patch("app.utils.qdrant_utils.to_client_image_url", side_effect=lambda x: x):
        result = scroll_random_places(mock_client, "관광지", limit=3, collection_name="places")

    assert len(result) == 3
    ids = {r["contentid"] for r in result}
    assert ids == {"1", "2", "3"}
    for item in result:
        assert "name" in item
        assert "address" in item
        assert "image" in item


def test_limit_is_respected():
    """limit보다 많은 포인트가 있어도 limit 수만큼만 반환해야 한다."""
    mock_client = MagicMock()
    points = [_make_point(i, f"장소{i}", f"주소{i}", "") for i in range(10)]
    mock_client.scroll.return_value = (points, None)

    with patch("app.utils.qdrant_utils.to_client_image_url", side_effect=lambda x: x):
        result = scroll_random_places(mock_client, "음식점", limit=3, collection_name="places")

    assert len(result) == 3


def test_returns_empty_when_no_points():
    """Qdrant에 포인트가 없으면 빈 리스트를 반환해야 한다."""
    mock_client = MagicMock()
    mock_client.scroll.return_value = ([], None)

    result = scroll_random_places(mock_client, "관광지", limit=3, collection_name="places")

    assert result == []


def test_returns_empty_on_exception():
    """Qdrant 연결 오류가 나도 빈 리스트를 반환해야 한다 (예외 전파 안 됨)."""
    mock_client = MagicMock()
    mock_client.scroll.side_effect = Exception("connection error")

    result = scroll_random_places(mock_client, "관광지", limit=3, collection_name="places")

    assert result == []


def test_uses_address_fallback():
    """addr 키가 없으면 address 키로 폴백해야 한다."""
    mock_client = MagicMock()
    p = MagicMock()
    p.id = 1
    p.payload = {"title": "테스트 장소", "address": "부산 해운대구", "image": ""}
    mock_client.scroll.return_value = ([p], None)

    with patch("app.utils.qdrant_utils.to_client_image_url", side_effect=lambda x: x):
        result = scroll_random_places(mock_client, "관광지", limit=1, collection_name="places")

    assert result[0]["address"] == "부산 해운대구"


def test_uses_default_address_when_missing():
    """addr/address 키가 모두 없으면 '주소 정보 없음'을 반환해야 한다."""
    mock_client = MagicMock()
    p = MagicMock()
    p.id = 1
    p.payload = {"title": "알 수 없는 장소"}
    mock_client.scroll.return_value = ([p], None)

    with patch("app.utils.qdrant_utils.to_client_image_url", side_effect=lambda x: x):
        result = scroll_random_places(mock_client, "관광지", limit=1, collection_name="places")

    assert result[0]["address"] == "주소 정보 없음"


def test_passes_content_type_to_filter():
    """content_type 인자가 Qdrant 필터에 올바르게 전달돼야 한다."""
    mock_client = MagicMock()
    mock_client.scroll.return_value = ([], None)

    with patch("app.utils.qdrant_utils.to_client_image_url", side_effect=lambda x: x):
        scroll_random_places(mock_client, "음식점", limit=3, collection_name="places")

    call_kwargs = mock_client.scroll.call_args[1]
    must_conditions = call_kwargs["scroll_filter"].must
    assert any(
        getattr(cond, "match", None) and cond.match.value == "음식점"
        for cond in must_conditions
    )
