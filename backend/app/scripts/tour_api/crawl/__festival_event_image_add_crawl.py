from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..__config import load_settings
from .__festival_event_image_add import (
    EventRow,
    _event_is_active_or_upcoming,
    _format_period,
    _text,
    dedupe_event_rows,
    fetch_seoul_culture_events,
    write_event_rows,
)

VISITKOREA_SHOW_CALL_URL = "https://korean.visitkorea.or.kr/call"
VISITKOREA_SHOW_REFERER = "https://korean.visitkorea.or.kr/list/travelinfo.do?service=show"
VISITKOREA_IMAGE_CALL_PREFIX = "https://cdn.visitkorea.or.kr/img/call?cmd=VIEW&id="
DEFAULT_CRAWL_OUTPUT_PATH = Path("backend/data/image_add/15_축제공연행사_image_add_crawl.jsonl")


def _visitkorea_headers() -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": VISITKOREA_SHOW_REFERER,
        "X-Requested-With": "XMLHttpRequest",
    }


def _geocode_address_kakao(address: str, kakao_rest_api_key: str) -> Tuple[str, str]:
    if not address or not kakao_rest_api_key:
        return "", ""
    response = requests.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        params={"query": address, "size": 1},
        headers={"Authorization": f"KakaoAK {kakao_rest_api_key}"},
        timeout=20,
    )
    if response.status_code != 200:
        return "", ""
    docs = response.json().get("documents") or []
    if not docs:
        return "", ""
    doc = docs[0]
    return _text(doc.get("y")), _text(doc.get("x"))


def fetch_visitkorea_show_events_by_call(*, max_pages: Optional[int] = None) -> List[EventRow]:
    settings = load_settings()
    rows: List[EventRow] = []
    page = 1
    total_count = None

    while True:
        if max_pages is not None and page > max_pages:
            break

        payload = {
            "cmd": "FESTIVAL_CONTENT_LIST_VIEW",
            "year": "All",
            "month": "All",
            "areaCode": "1",
            "sigunguCode": "All",
            "tagId": "All",
            "sortkind": "1",
            "locationx": "0",
            "locationy": "0",
            "page": str(page),
            "cnt": "10",
        }
        response = requests.post(
            VISITKOREA_SHOW_CALL_URL,
            data=payload,
            headers=_visitkorea_headers(),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        body = data.get("body") or {}
        result = body.get("result") or []
        if total_count is None:
            total_count = int(body.get("totalCount") or 0)
        if not result:
            break

        for item in result:
            start_date = _text(item.get("startDate"))
            end_date = _text(item.get("endDate"))
            if not _event_is_active_or_upcoming(start_date, end_date):
                continue

            addr = _text(item.get("addr1"))
            addr2 = _text(item.get("addr2"))
            full_addr = addr if not addr2 else f"{addr} {addr2}".strip()
            mapy, mapx = _geocode_address_kakao(full_addr or addr, settings.kakao_rest_api_key)

            rows.append(
                EventRow(
                    contentid=_text(item.get("cid") or item.get("cotId")),
                    title=_text(item.get("title")),
                    contenttypeid="축제공연행사",
                    contenttypeid_code="15",
                    category="축제",
                    image=VISITKOREA_IMAGE_CALL_PREFIX + _text(item.get("imgPath")),
                    usetime="",
                    restdate="",
                    parking="",
                    place="",
                    addr=full_addr or addr,
                    mapy=mapy,
                    mapx=mapx,
                    tel=_text(item.get("telNo")),
                    period=_format_period(start_date, end_date),
                    llm_text="",
                )
            )

        if total_count is not None and page * 10 >= total_count:
            break
        page += 1

    return rows


def build_festival_image_add_crawl_only(
    output_path: Path = DEFAULT_CRAWL_OUTPUT_PATH,
    *,
    max_seoul_pages: Optional[int] = None,
    max_visitkorea_pages: Optional[int] = None,
) -> Dict[str, Any]:
    seoul_rows = fetch_seoul_culture_events(max_pages=max_seoul_pages)
    visitkorea_rows = fetch_visitkorea_show_events_by_call(max_pages=max_visitkorea_pages)
    merged_rows = dedupe_event_rows([*seoul_rows, *visitkorea_rows])
    write_event_rows(output_path, merged_rows)
    return {
        "output_path": str(output_path),
        "seoul_culture_count": len(seoul_rows),
        "visitkorea_crawl_count": len(visitkorea_rows),
        "merged_count": len(merged_rows),
        "crawl_only": True,
    }
