"""
sync_new_popup_data.py 단위 테스트.

외부 크롤러(Selenium), Qdrant 호출은 모두 mock 처리한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.scripts.scheduler.sync_new_popup_data import (
    _get_existing_popup_identity_keys,
)
from app.scripts.tour_api.__crawl import _popup_identity_key, _text


# ---------------------------------------------------------------------------
# identity_key 중복 필터 테스트
# ---------------------------------------------------------------------------

def test_popup_identity_key_is_stable():
    """동일한 입력에 대해 항상 같은 key를 반환한다."""
    key1 = _popup_identity_key("팝업A", "서울 강남구 테헤란로 1", "2025-01-01", "2025-03-31")
    key2 = _popup_identity_key("팝업A", "서울 강남구 테헤란로 1", "2025-01-01", "2025-03-31")
    assert key1 == key2
    assert key1 != ""


def test_popup_identity_key_differs_for_different_dates():
    """같은 이름/주소라도 날짜가 다르면 다른 key를 반환한다 (다른 회차 팝업 구별)."""
    key1 = _popup_identity_key("팝업A", "서울 강남구 테헤란로 1", "2025-01-01", "2025-03-31")
    key2 = _popup_identity_key("팝업A", "서울 강남구 테헤란로 1", "2025-04-01", "2025-06-30")
    assert key1 != key2


def test_popup_identity_key_differs_for_different_addresses():
    """같은 이름이라도 주소가 다르면 다른 key를 반환한다 (다른 지점 팝업 구별)."""
    key1 = _popup_identity_key("팝업B", "서울 마포구 홍익로 1", "2025-01-01", "2025-03-31")
    key2 = _popup_identity_key("팝업B", "서울 강남구 테헤란로 1", "2025-01-01", "2025-03-31")
    assert key1 != key2


# ---------------------------------------------------------------------------
# _get_existing_popup_identity_keys 테스트
# ---------------------------------------------------------------------------

def _make_popup_point(title: str, addr: str, start_date: str, end_date: str):
    pt = MagicMock()
    pt.payload = {
        "title": title,
        "addr": addr,
        "start_date": start_date,
        "end_date": end_date,
        "contenttypeid": "팝업스토어",
    }
    return pt


def test_get_existing_popup_identity_keys_returns_keys_from_qdrant():
    mock_client = MagicMock()
    pts = [
        _make_popup_point("팝업A", "서울 강남구", "2025-01-01", "2025-03-31"),
        _make_popup_point("팝업B", "서울 마포구", "2025-02-01", "2025-04-30"),
    ]
    # 첫 scroll은 pts 반환, next_offset=None (끝)
    mock_client.scroll.return_value = (pts, None)

    keys = _get_existing_popup_identity_keys(mock_client)

    expected_a = _popup_identity_key("팝업A", "서울 강남구", "2025-01-01", "2025-03-31")
    expected_b = _popup_identity_key("팝업B", "서울 마포구", "2025-02-01", "2025-04-30")
    assert expected_a in keys
    assert expected_b in keys
    assert len(keys) == 2


def test_get_existing_popup_identity_keys_paginates_correctly():
    mock_client = MagicMock()
    page1 = [_make_popup_point("팝업A", "서울 강남구", "2025-01-01", "2025-03-31")]
    page2 = [_make_popup_point("팝업B", "서울 마포구", "2025-02-01", "2025-04-30")]

    # 첫 scroll: page1 반환, next_offset="some-cursor"
    # 두 번째 scroll: page2 반환, next_offset=None
    mock_client.scroll.side_effect = [
        (page1, "some-cursor"),
        (page2, None),
    ]

    keys = _get_existing_popup_identity_keys(mock_client)

    assert len(keys) == 2
    assert mock_client.scroll.call_count == 2


def test_get_existing_popup_identity_keys_skips_empty_keys():
    """title/addr 없는 포인트의 identity_key는 빈 문자열이므로 건너뜀."""
    mock_client = MagicMock()
    pt_empty = MagicMock()
    pt_empty.payload = {"contenttypeid": "팝업스토어"}  # title, addr 없음
    pt_valid = _make_popup_point("팝업A", "서울 강남구", "2025-01-01", "2025-03-31")

    mock_client.scroll.return_value = ([pt_empty, pt_valid], None)

    keys = _get_existing_popup_identity_keys(mock_client)

    # 빈 key는 포함되지 않음
    assert "" not in keys
    assert len(keys) == 1


# ---------------------------------------------------------------------------
# 만료 팝업 제외 검증 (경량 정규화 경로 확인)
# ---------------------------------------------------------------------------

def test_build_popup_image_add_rows_excludes_expired_popups():
    """end_date가 오늘 이전이면 정규화 후 제외된다."""
    from app.scripts.tour_api.__crawl import _build_popup_image_add_rows
    from pathlib import Path

    raw_data = [
        {
            "name": "만료된 팝업",
            "schedule": "2020-01-01T00:00:00 ~ 2020-12-31T00:00:00",  # 과거
            "location": "서울 강남구 테헤란로 1",
            "hours": "",
            "introduction": "",
            "thumbnail": "",
            "parking": "Unknown",
            "fee": "Unknown",
            "pet": "Unknown",
            "kids": "Unknown",
            "food_ban": "Unknown",
            "adult_only": "Unknown",
            "wifi": "Unknown",
            "photo": "Unknown",
        },
        {
            "name": "활성 팝업",
            "schedule": "2026-01-01T00:00:00 ~ 2026-12-31T00:00:00",  # 미래
            "location": "서울 마포구 홍익로 2",
            "hours": "",
            "introduction": "좋은 팝업",
            "thumbnail": "",
            "parking": "Unknown",
            "fee": "Unknown",
            "pet": "Unknown",
            "kids": "Unknown",
            "food_ban": "Unknown",
            "adult_only": "Unknown",
            "wifi": "Unknown",
            "photo": "Unknown",
        },
    ]

    # llm_cache_path는 존재하지 않는 경로 (빈 캐시로 처리됨)
    rows = _build_popup_image_add_rows(raw_data, Path("/nonexistent/cache.jsonl"))

    titles = [r.get("title") for r in rows]
    assert "만료된 팝업" not in titles
    assert "활성 팝업" in titles
