"""
sync_new_popup_data.py 단위 테스트.

외부 크롤러(Selenium), Qdrant, Naver API, OpenAI 호출은 모두 mock 처리한다.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.scripts.scheduler.sync_new_popup_data import (
    _get_existing_popup_identity_keys,
    _step1_normalize,
)
from app.scripts.tour_api.__crawl import _popup_identity_key, _text


# ---------------------------------------------------------------------------
# identity_key 안정성 테스트
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
# _step1_normalize 테스트
# ---------------------------------------------------------------------------

def _make_raw(name, schedule, location="서울 강남구 테헤란로 1",
              hours="", introduction="", thumbnail="",
              parking="Unknown", fee="Unknown"):
    return {
        "url": f"https://popply.co.kr/popup/1",
        "name": name,
        "schedule": schedule,
        "location": location,
        "hours": hours,
        "introduction": introduction,
        "thumbnail": thumbnail,
        "parking": parking,
        "fee": fee,
        "pet": "Unknown",
        "kids": "Unknown",
        "food_ban": "Unknown",
        "adult_only": "Unknown",
        "wifi": "Unknown",
        "photo": "Unknown",
    }


def test_step1_normalize_excludes_expired_popups():
    """end_date가 오늘 이전이면 1단계 정규화에서 제외된다."""
    raw = [
        _make_raw("만료 팝업", "2020-01-01T00:00:00 ~ 2020-12-31T00:00:00"),
        _make_raw("활성 팝업", "2026-01-01T00:00:00 ~ 2026-12-31T00:00:00"),
    ]
    result = _step1_normalize(raw)
    titles = [r["title"] for r in result]
    assert "만료 팝업" not in titles
    assert "활성 팝업" in titles


def test_step1_normalize_fields_mapped_correctly():
    """crawler의 name/location/hours 필드가 title/addr/usetime으로 정규화된다.
    contenttypeid는 기존 파이프라인과 동일하게 '콘텐츠', contenttypeid_code='15'."""
    raw = [_make_raw(
        "테스트 팝업",
        "2026-03-01T00:00:00 ~ 2026-06-30T00:00:00",
        location="서울 마포구 홍익로 5",
        hours="10:00 ~ 20:00",
        introduction="팝업 소개",
        thumbnail="https://img.example.com/thumb.jpg",
        parking="주차 가능",
        fee="무료",
    )]
    result = _step1_normalize(raw)
    assert len(result) == 1
    r = result[0]
    assert r["title"] == "테스트 팝업"
    assert r["addr"] == "서울 마포구 홍익로 5"
    assert r["usetime"] == "10:00 ~ 20:00"
    assert r["start_date"] == "2026-03-01"
    assert r["end_date"] == "2026-06-30"
    # 기존 _build_15_content 경로와 동일한 규격
    assert r["contenttypeid"] == "콘텐츠"
    assert r["contenttypeid_code"] == "15"
    assert r["parking"] == "주차 가능"
    assert r["fee"] == "무료"


def test_step1_normalize_contentid_is_stable():
    """같은 raw 데이터에 대해 contentid가 항상 동일하다 (순번 기반 아님)."""
    raw = [_make_raw("안정 팝업", "2026-03-01T00:00:00 ~ 2026-12-31T00:00:00")]
    result1 = _step1_normalize(raw)
    result2 = _step1_normalize(raw)
    assert result1[0]["contentid"] == result2[0]["contentid"]
    # 9로 시작하는 10자리 해시 형식
    assert result1[0]["contentid"].startswith("9")


def test_step1_normalize_unknown_fields_excluded():
    """'Unknown' 값인 parking/fee는 결과에서 제외된다."""
    raw = [_make_raw("팝업", "2026-01-01T00:00:00 ~ 2026-12-31T00:00:00",
                     parking="Unknown", fee="Unknown")]
    result = _step1_normalize(raw)
    assert "parking" not in result[0]
    assert "fee" not in result[0]


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
    """contenttypeid='콘텐츠' 기준으로 스캔하여 기존 팝업 key를 반환한다."""
    mock_client = MagicMock()
    pts = [
        _make_popup_point("팝업A", "서울 강남구", "2025-01-01", "2025-03-31"),
        _make_popup_point("팝업B", "서울 마포구", "2025-02-01", "2025-04-30"),
    ]
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
    mock_client.scroll.side_effect = [
        (page1, "some-cursor"),
        (page2, None),
    ]

    keys = _get_existing_popup_identity_keys(mock_client)

    assert len(keys) == 2
    assert mock_client.scroll.call_count == 2


def test_get_existing_popup_identity_keys_skips_empty_title():
    """title이 없는 포인트는 identity_key 계산을 건너뜀."""
    mock_client = MagicMock()
    pt_empty = MagicMock()
    pt_empty.payload = {"contenttypeid": "팝업스토어"}  # title 없음
    pt_valid = _make_popup_point("팝업A", "서울 강남구", "2025-01-01", "2025-03-31")

    mock_client.scroll.return_value = ([pt_empty, pt_valid], None)

    keys = _get_existing_popup_identity_keys(mock_client)

    assert "" not in keys
    assert len(keys) == 1
