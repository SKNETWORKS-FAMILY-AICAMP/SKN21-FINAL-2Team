"""
sync_new_contents.py 단위 테스트.

외부 크롤러(Selenium), Qdrant, Naver API, OpenAI 호출은 모두 mock 처리한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.scripts.scheduler.sync_new_contents import _get_existing_contentids


def _make_point(contentid: str):
    pt = MagicMock()
    pt.payload = {"contentid": contentid}
    return pt


def test_get_existing_contentids_returns_ids():
    """contenttypeid='콘텐츠' 기준으로 스캔하여 기존 contentid를 반환한다."""
    mock_client = MagicMock()
    pts = [_make_point("4640"), _make_point("4639"), _make_point("156698")]
    mock_client.scroll.return_value = (pts, None)

    ids = _get_existing_contentids(mock_client)

    assert "4640" in ids
    assert "4639" in ids
    assert "156698" in ids
    assert len(ids) == 3


def test_get_existing_contentids_paginates():
    """여러 페이지를 순회하여 전체 contentid를 수집한다."""
    mock_client = MagicMock()
    page1 = [_make_point("4640")]
    page2 = [_make_point("4639")]
    mock_client.scroll.side_effect = [
        (page1, "cursor-1"),
        (page2, None),
    ]

    ids = _get_existing_contentids(mock_client)

    assert len(ids) == 2
    assert mock_client.scroll.call_count == 2


def test_get_existing_contentids_skips_empty():
    """contentid가 비어있는 포인트는 건너뛴다."""
    mock_client = MagicMock()
    pt_empty = MagicMock()
    pt_empty.payload = {}
    pt_valid = _make_point("4640")
    mock_client.scroll.return_value = ([pt_empty, pt_valid], None)

    ids = _get_existing_contentids(mock_client)

    assert "" not in ids
    assert len(ids) == 1
