"""한국관광공사 TourAPI 수집

areaBasedList2 → detailCommon2 + detailIntro2 를 한 번에 호출하여
카테고리(contentTypeId)별 원본 데이터를 저장한다.
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
    TOURAPI_BASE,
    TOURAPI_CONTENT_TYPES,
    TOURAPI_PARAMS,
)

log = logging.getLogger(__name__)


def _get(endpoint: str, params: dict) -> dict | None:
    """TourAPI GET 요청. 재시도 포함."""
    url = f"{TOURAPI_BASE}/{endpoint}"
    merged = {**TOURAPI_PARAMS, **params}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=merged, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            if "response" not in data:
                code = data.get("resultCode", "")
                msg = data.get("resultMsg", "")
                log.warning("[%s] API 에러 code=%s msg=%s", endpoint, code, msg)
                return None

            return data["response"]["body"]
        except requests.RequestException as e:
            log.warning("[%s] 요청 실패 (%d/%d): %s", endpoint, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
    return None


def _parse_items(body: dict | None) -> list[dict]:
    """API body에서 item 리스트 추출."""
    if not body:
        return []
    items = body.get("items", "")
    if not items or isinstance(items, str):
        return []
    item_list = items.get("item", [])
    if isinstance(item_list, dict):
        return [item_list]
    return item_list


def _fetch_list(content_type_id: str, page: int = 1, size: int = 100) -> tuple[list[dict], int]:
    """areaBasedList2로 서울 지역 콘텐츠 목록 조회."""
    body = _get("areaBasedList2", {
        "areaCode": 1,
        "contentTypeId": content_type_id,
        "numOfRows": size,
        "pageNo": page,
        "arrange": "A",
    })
    total = body.get("totalCount", 0) if body else 0
    return _parse_items(body), total


def _fetch_detail(content_id: str, content_type_id: str) -> dict | None:
    """detailCommon2 + detailIntro2 원본을 합쳐 반환."""
    common_list = _parse_items(_get("detailCommon2", {"contentId": content_id}))
    if not common_list:
        return None
    common = common_list[0]

    intro_list = _parse_items(_get("detailIntro2", {
        "contentId": content_id,
        "contentTypeId": content_type_id,
    }))
    intro = intro_list[0] if intro_list else {}

    return {**intro, **common, "_source": "tourapi"}


def _load_existing_ids(path) -> set[str]:
    """이미 수집된 contentid 목록 로드 (이어받기용)."""
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                ids.add(json.loads(line)["contentid"])
            except (json.JSONDecodeError, KeyError):
                pass
    return ids


def collect(content_type_id: str | None = None):
    """TourAPI 데이터 수집.

    content_type_id 지정 시 해당 카테고리만, None이면 전체 수집.
    """
    targets = (
        {content_type_id: TOURAPI_CONTENT_TYPES[content_type_id]}
        if content_type_id
        else TOURAPI_CONTENT_TYPES
    )

    for ctid, name in targets.items():
        log.info("[tourapi] %s(%s) 수집 시작", name, ctid)
        output_path = RAW_DIR / f"tourapi_{name}.jsonl"
        existing_ids = _load_existing_ids(output_path)

        page, collected, skipped = 1, 0, 0

        while True:
            items, total = _fetch_list(ctid, page=page)
            if not items:
                break

            for item in items:
                cid = item["contentid"]
                if cid in existing_ids:
                    skipped += 1
                    continue

                time.sleep(REQUEST_DELAY)
                detail = _fetch_detail(cid, ctid)
                if not detail:
                    log.warning("  %s 상세 조회 실패, 건너뜀", cid)
                    continue

                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(detail, ensure_ascii=False) + "\n")

                existing_ids.add(cid)
                collected += 1

                if collected % 50 == 0:
                    log.info("  %s: %d건 수집 완료", name, collected)

            if page * 100 >= total:
                break
            page += 1
            time.sleep(REQUEST_DELAY)

        log.info("[tourapi] %s 완료: 신규 %d건, 스킵 %d건 (전체 %d건)",
                 name, collected, skipped, len(existing_ids))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    collect()
