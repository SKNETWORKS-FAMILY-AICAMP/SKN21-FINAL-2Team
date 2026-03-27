"""VisitSeoul API 수집

contents/list → contents/info 순차 호출하여 원본 데이터를 저장한다.
"""

import json
import logging
import time

import requests

from .config import (
    MAX_RETRIES,
    RAW_DIR,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    VISITSEOUL_BASE,
    VISITSEOUL_HEADERS,
)

log = logging.getLogger(__name__)

PAGE_SIZE = 100
EXCLUDE_CATE = {"축제/공연/행사"}


def _post(path: str, body: dict) -> dict | None:
    """VisitSeoul POST 요청. 재시도 포함."""
    url = f"{VISITSEOUL_BASE}{path}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(url, headers=VISITSEOUL_HEADERS, json=body, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            log.warning("[visitseoul] %s 요청 실패 (%d/%d): %s", path, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
    return None


def _get(path: str) -> dict | None:
    """VisitSeoul GET 요청."""
    url = f"{VISITSEOUL_BASE}{path}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=VISITSEOUL_HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            log.warning("[visitseoul] %s 요청 실패 (%d/%d): %s", path, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
    return None


def _extract_data(response: dict | None) -> list | dict:
    """응답에서 data/result 추출 (구조가 유동적이므로 유연하게 파싱)."""
    if not response:
        return []
    data = response.get("data") or response.get("result") or response
    if isinstance(data, dict):
        data = data.get("list") or data.get("contents") or data.get("items") or data
    return data


def _fetch_all_cids() -> list[str]:
    """전체 CID 목록 수집 (페이징)."""
    cids = []
    page = 1

    while True:
        resp = _post("/api/v1/contents/list", {
            "page_no": page,
            "page_size": PAGE_SIZE,
            "lang_code": "ko",
        })
        data = _extract_data(resp)
        if not data or not isinstance(data, list):
            break

        for item in data:
            cid = item.get("cid") or item.get("content_id") or item.get("id")
            if cid:
                cids.append(cid)

        if len(data) < PAGE_SIZE:
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    return cids


def _fetch_info(cid: str) -> dict | None:
    """단일 콘텐츠 상세 조회. 원본 그대로 반환."""
    resp = _post("/api/v1/contents/info", {"cid": cid})
    data = _extract_data(resp)
    if isinstance(data, list):
        data = data[0] if data else None
    if isinstance(data, dict):
        data["_source"] = "visitseoul"
    return data if isinstance(data, dict) else None


def collect():
    """VisitSeoul 전체 콘텐츠 수집."""
    output_path = RAW_DIR / "visitseoul.jsonl"

    # 이어받기: 기존 CID 로드
    existing_cids: set[str] = set()
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                try:
                    existing_cids.add(json.loads(line)["cid"])
                except (json.JSONDecodeError, KeyError):
                    pass

    log.info("[visitseoul] CID 목록 수집 중...")
    all_cids = _fetch_all_cids()
    new_cids = [c for c in all_cids if c not in existing_cids]
    log.info("[visitseoul] 전체 %d건, 신규 %d건", len(all_cids), len(new_cids))

    collected = 0
    for cid in new_cids:
        time.sleep(REQUEST_DELAY)
        detail = _fetch_info(cid)
        if not detail:
            log.warning("  %s 상세 조회 실패, 건너뜀", cid)
            continue

        # 제외 카테고리 필터링
        cate = (detail.get("cate_depth") or "").strip()
        top_cate = cate.split(">")[0].strip()
        if top_cate in EXCLUDE_CATE:
            continue

        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(detail, ensure_ascii=False) + "\n")

        collected += 1
        if collected % 50 == 0:
            log.info("  visitseoul: %d건 수집 완료", collected)

    log.info("[visitseoul] 완료: 신규 %d건, 스킵 %d건 (전체 %d건)",
             collected, len(all_cids) - len(new_cids), len(all_cids))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    collect()
