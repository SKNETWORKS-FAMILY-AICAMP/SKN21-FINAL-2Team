"""
cleanup_closed_places.py 단위 테스트.

외부 API(Kakao) 및 Qdrant 호출은 모두 mock 처리한다.
NaverPlaceChecker 테스트 패턴(test_check_places_with_naver.py)을 따른다.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.scripts.scheduler.cleanup_closed_places import (
    KakaoCandidate,
    KakaoPlaceChecker,
    _delete_and_sync,
    _load_scroll_state,
    _save_scroll_state,
)


# ---------------------------------------------------------------------------
# KakaoPlaceChecker.evaluate_match 단위 테스트
# ---------------------------------------------------------------------------

def _make_checker() -> KakaoPlaceChecker:
    checker = KakaoPlaceChecker(sleep_ms=0)
    checker.api_key = "dummy_key"
    return checker


def _make_candidate(
    place_name: str,
    road_address: str = "",
    address_name: str = "",
    x: str = "",
    y: str = "",
    phone: str = "",
) -> KakaoCandidate:
    return KakaoCandidate(
        query=place_name,
        place_name=place_name,
        address_name=address_name,
        road_address_name=road_address,
        phone=phone,
        category_name="",
        place_url="",
        x=x,
        y=y,
    )


def test_evaluate_match_returns_no_match_when_no_candidates():
    checker = _make_checker()
    item = {"title": "어느 카페", "addr": "서울 마포구 어딘가", "mapy": "37.5", "mapx": "126.9"}
    result = checker.evaluate_match(item, ["어느 카페"], [])

    assert result.status == "no_match"
    assert result.score == 0.0


def test_evaluate_match_returns_open_for_exact_name_match():
    checker = _make_checker()
    item = {
        "title": "스타벅스 홍대점",
        "addr": "서울 마포구 양화로 160",
        "mapy": "37.5561",
        "mapx": "126.9231",
    }
    candidates = [
        _make_candidate(
            place_name="스타벅스 홍대점",
            road_address="서울 마포구 양화로 160",
            x="126.9231",
            y="37.5561",
        )
    ]
    result = checker.evaluate_match(item, ["스타벅스 홍대점"], candidates)

    assert result.status == "open"
    assert result.name_similarity >= 0.9


def test_evaluate_match_returns_closed_suspected_when_name_and_address_differ():
    checker = _make_checker()
    item = {
        "title": "폐업한 식당",
        "addr": "서울 강남구 테헤란로 100",
        "mapy": "37.4980",
        "mapx": "127.0276",
    }
    candidates = [
        _make_candidate(
            place_name="전혀다른가게",
            road_address="서울 강남구 역삼로 200",
            x="127.0500",
            y="37.5100",
        )
    ]
    result = checker.evaluate_match(item, ["폐업한 식당"], candidates)

    assert result.status == "closed_suspected"


def test_evaluate_match_returns_review_needed_for_partial_match():
    checker = _make_checker()
    item = {
        "title": "카페 아무개",
        "addr": "서울 종로구 인사동길 10",
        "mapy": "37.5742",
        "mapx": "126.9850",
    }
    candidates = [
        _make_candidate(
            place_name="카페아무개",
            road_address="서울 종로구 인사동길 10",
            x="126.9851",
            y="37.5743",
        )
    ]
    result = checker.evaluate_match(item, ["카페 아무개"], candidates)

    # 이름 유사도 낮지만 주소 일치 + 거리 가까움 → review_needed 또는 open
    assert result.status in ("open", "review_needed")


# ---------------------------------------------------------------------------
# scroll cursor 저장/로드 테스트
# ---------------------------------------------------------------------------

def test_load_scroll_state_returns_defaults_when_file_missing(tmp_path):
    with patch("app.scripts.scheduler.cleanup_closed_places.STATE_FILE", tmp_path / "state.json"):
        state = _load_scroll_state()

    assert state == {"places_offset": None, "photos_offset": None}


def test_save_and_load_scroll_state(tmp_path):
    state_file = tmp_path / "state.json"
    reports_dir = tmp_path

    with patch("app.scripts.scheduler.cleanup_closed_places.STATE_FILE", state_file), \
         patch("app.scripts.scheduler.cleanup_closed_places.REPORTS_DIR", reports_dir):
        _save_scroll_state("abc-uuid-places", "def-uuid-photos")
        state = _load_scroll_state()

    assert state["places_offset"] == "abc-uuid-places"
    assert state["photos_offset"] == "def-uuid-photos"


def test_save_scroll_state_resets_on_none(tmp_path):
    state_file = tmp_path / "state.json"
    reports_dir = tmp_path

    with patch("app.scripts.scheduler.cleanup_closed_places.STATE_FILE", state_file), \
         patch("app.scripts.scheduler.cleanup_closed_places.REPORTS_DIR", reports_dir):
        _save_scroll_state(None, None)
        state = _load_scroll_state()

    assert state["places_offset"] is None
    assert state["photos_offset"] is None


# ---------------------------------------------------------------------------
# delete_and_sync 테스트 (mock Qdrant client)
# ---------------------------------------------------------------------------

def test_delete_and_sync_does_not_call_delete_in_dry_run():
    mock_client = MagicMock()

    result = _delete_and_sync(
        client=mock_client,
        point_id="point-123",
        contentid="9000001",
        source_collection="places",
        dry_run=True,
    )

    mock_client.delete.assert_not_called()
    assert result["dry_run"] is True
    assert result["deleted_ids"] == []
    assert result["synced_ids"] == []


def test_delete_and_sync_deletes_source_and_syncs_other_collection():
    mock_client = MagicMock()

    # photos 컬렉션에서 contentid로 조회 시 2건 반환
    photo_pt1 = MagicMock()
    photo_pt1.id = "photo-uuid-1"
    photo_pt2 = MagicMock()
    photo_pt2.id = "photo-uuid-2"
    mock_client.scroll.return_value = ([photo_pt1, photo_pt2], None)

    result = _delete_and_sync(
        client=mock_client,
        point_id=9000001,
        contentid="9000001",
        source_collection="places",
        dry_run=False,
    )

    # places에서 삭제 호출
    assert mock_client.delete.call_count == 2  # places + photos
    assert result["deleted_ids"] == ["9000001"]
    assert "photo-uuid-1" in result["synced_ids"]
    assert "photo-uuid-2" in result["synced_ids"]


def test_delete_and_sync_skips_sync_when_no_contentid():
    mock_client = MagicMock()
    mock_client.scroll.return_value = ([], None)

    result = _delete_and_sync(
        client=mock_client,
        point_id="some-uuid",
        contentid=None,
        source_collection="photos",
        dry_run=False,
    )

    # source 삭제 1회만
    assert mock_client.delete.call_count == 1
    assert result["synced_ids"] == []
