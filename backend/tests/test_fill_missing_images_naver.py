import json

import pytest
import requests

from app.scripts.fill_missing_images_naver import (
    SearchResult,
    build_query,
    extract_first_link,
    is_missing_image,
    process_jsonl,
    search_image_link_once,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        if not self._responses:
            raise AssertionError("No more fake responses")
        value = self._responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def test_build_query_prefixes_restaurant_keyword():
    assert build_query("가문") == "가문 서울 음식점"
    assert build_query("  가담  ") == "가담 서울 음식점"


def test_is_missing_image():
    assert is_missing_image(None)
    assert is_missing_image("")
    assert is_missing_image("   ")
    assert not is_missing_image("https://example.com/a.jpg")


def test_extract_first_link_uses_link_only():
    payload = {"items": [{"link": "https://img.example.com/a.jpg", "thumbnail": "thumb"}]}
    assert extract_first_link(payload) == "https://img.example.com/a.jpg"


def test_extract_first_link_returns_none_when_link_missing():
    payload = {"items": [{"thumbnail": "https://img.example.com/thumb.jpg"}]}
    assert extract_first_link(payload) is None


def test_search_image_link_once_success():
    session = _FakeSession(
        [_FakeResponse(200, {"items": [{"link": "https://img.example.com/a.jpg"}]})]
    )
    result = search_image_link_once(
        title="가문",
        headers={"X-Naver-Client-Id": "id", "X-Naver-Client-Secret": "secret"},
        sleep_seconds=0,
        max_retries=0,
        session=session,
    )
    assert result == SearchResult(link="https://img.example.com/a.jpg", had_api_error=False)
    assert session.calls[0]["kwargs"]["params"]["query"] == "가문 서울 음식점"
    assert session.calls[0]["kwargs"]["params"]["filter"] == "large"


def test_search_image_link_once_retries_on_429():
    session = _FakeSession(
        [
            _FakeResponse(429, {}),
            _FakeResponse(200, {"items": [{"link": "https://img.example.com/final.jpg"}]}),
        ]
    )
    result = search_image_link_once(
        title="가문",
        headers={"X-Naver-Client-Id": "id", "X-Naver-Client-Secret": "secret"},
        sleep_seconds=0,
        max_retries=1,
        session=session,
    )
    assert result.link == "https://img.example.com/final.jpg"
    assert result.had_api_error is False


def test_search_image_link_once_returns_api_error_after_retry_exhausted():
    session = _FakeSession([_FakeResponse(500, {}), _FakeResponse(500, {})])
    result = search_image_link_once(
        title="가문",
        headers={"X-Naver-Client-Id": "id", "X-Naver-Client-Secret": "secret"},
        sleep_seconds=0,
        max_retries=1,
        session=session,
    )
    assert result.link is None
    assert result.had_api_error is True


def test_search_image_link_once_request_exception():
    session = _FakeSession([requests.RequestException("network error")])
    result = search_image_link_once(
        title="가문",
        headers={"X-Naver-Client-Id": "id", "X-Naver-Client-Secret": "secret"},
        sleep_seconds=0,
        max_retries=0,
        session=session,
    )
    assert result.link is None
    assert result.had_api_error is True


def test_search_image_link_once_auth_error_raises():
    session = _FakeSession([_FakeResponse(401, {})])
    with pytest.raises(RuntimeError):
        search_image_link_once(
            title="가문",
            headers={"X-Naver-Client-Id": "id", "X-Naver-Client-Secret": "secret"},
            sleep_seconds=0,
            max_retries=0,
            session=session,
        )


def test_process_jsonl_updates_only_missing_images(monkeypatch, tmp_path):
    input_path = tmp_path / "in.jsonl"
    output_path = tmp_path / "out.jsonl"

    records = [
        {"contentid": "1", "title": "가문", "image": ""},
        {"contentid": "2", "title": "가담", "image": "https://existing.example.com/2.jpg"},
        {"contentid": "3", "title": "가나돈까스", "image": " "},
        {"contentid": "4", "title": "", "image": ""},
    ]
    with input_path.open("w", encoding="utf-8") as wf:
        for record in records:
            wf.write(json.dumps(record, ensure_ascii=False) + "\n")

    monkeypatch.setenv("NAVER_CLIENT_ID", "id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "secret")

    calls = {"count": 0}

    def _fake_search(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return SearchResult(link="https://img.example.com/1.jpg", had_api_error=False)
        return SearchResult(link=None, had_api_error=False)

    monkeypatch.setattr("app.scripts.fill_missing_images_naver.search_image_link_once", _fake_search)

    stats = process_jsonl(
        input_path=input_path,
        output_path=output_path,
        dry_run=False,
        limit=None,
        sleep_seconds=0,
        max_retries=0,
    )

    assert stats.total == 4
    assert stats.target_missing == 3
    assert stats.filled == 1
    assert stats.skipped_existing == 1
    assert stats.no_result == 2
    assert stats.api_error == 0

    with output_path.open("r", encoding="utf-8") as rf:
        out_records = [json.loads(line) for line in rf if line.strip()]

    assert len(out_records) == 4
    assert out_records[0]["image"] == "https://img.example.com/1.jpg"
    assert out_records[1]["image"] == "https://existing.example.com/2.jpg"
    assert out_records[2]["image"].strip() == ""
