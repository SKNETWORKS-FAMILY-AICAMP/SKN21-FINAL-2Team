"""서울시 문화행사 정보 수집 (열린데이터광장 API)

data.seoul.go.kr OA-15486 culturalEventInfo API를 호출하여
서울시 문화행사 원본 데이터를 저장한다.
"""

import json
import logging
import time
from datetime import date

import requests

from .config import MAX_RETRIES, RAW_DIR, REQUEST_DELAY, REQUEST_TIMEOUT, SEOUL_CULTURE_BASE, SEOUL_CULTURE_SERVICE, SEOUL_OPENDATA_KEY

log = logging.getLogger(__name__)

PAGE_SIZE = 1000
EXCLUDE_CODES = {"교육/체험", "독주/독창회"}


def _fetch_page(start: int, end: int) -> tuple[list[dict], int]:
    """start~end 범위 조회. (items, totalCount) 반환."""
    url = f"{SEOUL_CULTURE_BASE}/{SEOUL_OPENDATA_KEY}/json/{SEOUL_CULTURE_SERVICE}/{start}/{end}/"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            info = data.get(SEOUL_CULTURE_SERVICE, {})
            result = info.get("RESULT", {})

            if result.get("CODE") != "INFO-000":
                log.warning("[seoul_culture] API 에러: %s", result.get("MESSAGE"))
                return [], 0

            total = info.get("list_total_count", 0)
            rows = info.get("row", [])
            return rows, total
        except requests.RequestException as e:
            log.warning("[seoul_culture] %d~%d 실패 (%d/%d): %s", start, end, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    return [], 0


def _load_existing_ids(path) -> set[str]:
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                ids.add(d.get("HMPG_ADDR") or d.get("TITLE", ""))
            except (json.JSONDecodeError, KeyError):
                pass
    return ids


def collect():
    """서울시 문화행사 전체 수집."""
    output_path = RAW_DIR / "seoul_culture.jsonl"
    existing_ids = _load_existing_ids(output_path)

    start = 1
    collected, skipped = 0, 0

    while True:
        end = start + PAGE_SIZE - 1
        rows, total = _fetch_page(start, end)
        if not rows:
            break

        today = date.today().isoformat()  # "2026-03-23"

        for row in rows:
            if row.get("CODENAME", "") in EXCLUDE_CODES:
                skipped += 1
                continue

            # 종료일이 수집일 이전이면 스킵
            end_date = (row.get("END_DATE") or "")[:10]
            if end_date and end_date < today:
                skipped += 1
                continue

            uid = row.get("HMPG_ADDR") or row.get("TITLE", "")
            if uid in existing_ids:
                skipped += 1
                continue

            row["_source"] = "seoul_culture"
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

            existing_ids.add(uid)
            collected += 1

        log.info("[seoul_culture] %d/%d건 처리 (신규 %d)", min(end, total), total, collected)

        if end >= total:
            break
        start += PAGE_SIZE
        time.sleep(REQUEST_DELAY)

    log.info("[seoul_culture] 완료: 신규 %d건, 스킵 %d건 (전체 %d건)", collected, skipped, len(existing_ids))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    collect()
