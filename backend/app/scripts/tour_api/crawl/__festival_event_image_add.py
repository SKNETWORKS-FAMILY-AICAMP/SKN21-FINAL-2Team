from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from ..__config import load_settings

SEOUL_CULTURE_LIST_URL = "https://culture.seoul.go.kr/culture/culture/cultureEvent/jsonList.json"
SEOUL_CULTURE_IMAGE_URL = "https://culture.seoul.go.kr/cmmn/file/getImage.do"
VISITKOREA_IMAGE_CALL_PREFIX = "https://cdn.visitkorea.or.kr/img/call?cmd=VIEW&id="
DEFAULT_OUTPUT_PATH = Path("backend/data/image_add/15_축제공연행사_image_add.jsonl")
TODAY = date.today()


@dataclass
class EventRow:
    contentid: str
    title: str
    contenttypeid: str
    contenttypeid_code: str
    category: str
    image: str
    usetime: str
    restdate: str
    parking: str
    place: str
    addr: str
    mapy: str
    mapx: str
    tel: str
    period: str
    llm_text: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _norm_space(value: str) -> str:
    return re.sub(r"\s+", " ", _text(value)).strip()


def _norm_title(value: str) -> str:
    value = _norm_space(value)
    value = value.lower()
    value = re.sub(r"\s*[\-–~]+\s*", " ", value)
    return value


def _norm_addr(value: str) -> str:
    value = _norm_space(value)
    value = value.replace("서울특별시", "서울")
    return value


def _absolute_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://culture.seoul.go.kr" + url
    return url


def _build_seoul_culture_image_url(atch_file_id: str) -> str:
    if not atch_file_id:
        return ""
    return f"{SEOUL_CULTURE_IMAGE_URL}?atchFileId={atch_file_id}&thumb=Y"


def _try_parse_date(value: str) -> Optional[date]:
    value = _text(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _format_period(start_value: str, end_value: str) -> str:
    start = _try_parse_date(start_value)
    end = _try_parse_date(end_value)
    if start and end:
        return f"{start.isoformat()} ~ {end.isoformat()}"
    if start:
        return f"{start.isoformat()} ~ {start.isoformat()}"
    return ""


def _event_is_active_or_upcoming(start_value: str, end_value: str) -> bool:
    start = _try_parse_date(start_value)
    end = _try_parse_date(end_value)
    if end:
        return end >= TODAY
    if start:
        return start >= TODAY
    return True


def _tour_api_params(settings, extra: Dict[str, Any], tour_api_key: str) -> Dict[str, Any]:
    params = {
        "serviceKey": tour_api_key,
        "MobileOS": settings.tour_mobile_os,
        "MobileApp": settings.tour_mobile_app,
        "_type": settings.tour_api_type,
    }
    params.update(extra)
    return params


def _tour_api_get(url: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _tour_api_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = (payload.get("response") or {}).get("body") or {}
    items = (body.get("items") or {}).get("item")
    if items is None:
        return []
    if isinstance(items, list):
        return items
    return [items]


def _visitkorea_image_url(raw_url: str) -> str:
    raw_url = _absolute_url(raw_url)
    match = re.search(r"id=([0-9a-f\-]{32,36})", raw_url, re.I)
    if match:
        return VISITKOREA_IMAGE_CALL_PREFIX + match.group(1)
    match = re.search(r"/([0-9a-f\-]{32,36})(?:_[^/]+)?\.(?:jpg|jpeg|png|webp)$", raw_url, re.I)
    if match:
        return VISITKOREA_IMAGE_CALL_PREFIX + match.group(1)
    return raw_url


def fetch_seoul_culture_events(search_cate: str = "SHOW", menu_no: str = "200008", max_pages: Optional[int] = None) -> List[EventRow]:
    rows: List[EventRow] = []
    seen_ids: set[str] = set()
    seen_page_signatures: set[Tuple[str, ...]] = set()
    page_index = 1

    while True:
        if max_pages is not None and page_index > max_pages:
            break
        response = requests.post(
            SEOUL_CULTURE_LIST_URL,
            data={"searchCate": search_cate, "menuNo": menu_no, "pageIndex": str(page_index)},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        result_list = payload.get("resultList") or []
        if not result_list:
            break

        page_signature = tuple(_text(item.get("cultcode")) for item in result_list)
        if page_signature in seen_page_signatures:
            break
        seen_page_signatures.add(page_signature)

        added = 0
        for item in result_list:
            contentid = _text(item.get("cultcode"))
            if not contentid or contentid in seen_ids:
                continue
            start_value = _text(item.get("strtdate"))
            end_value = _text(item.get("endDate"))
            if not _event_is_active_or_upcoming(start_value, end_value):
                continue
            seen_ids.add(contentid)
            added += 1

            image = _absolute_url(_text(item.get("mainImg")))
            if not image:
                image = _build_seoul_culture_image_url(_text(item.get("atchFileId")))

            rows.append(
                EventRow(
                    contentid=contentid,
                    title=_text(item.get("title")),
                    contenttypeid="축제공연행사",
                    contenttypeid_code="15",
                    category=_text(item.get("subjcodeGroupNm") or item.get("subjcodeNm")),
                    image=image,
                    usetime="",
                    restdate="",
                    parking="",
                    place=_text(item.get("facName")),
                    addr=_text(item.get("addr")),
                    mapy=_text(item.get("xCoord")),
                    mapx=_text(item.get("yCoord")),
                    tel="",
                    period=_format_period(start_value, end_value),
                    llm_text="",
                )
            )

        if added == 0:
            break
        page_index += 1

    return rows


def fetch_tour_api_events(tour_api_key: str, area_code: int = 1) -> List[EventRow]:
    settings = load_settings()
    rows: List[EventRow] = []
    page_no = 1

    while True:
        params = _tour_api_params(
            settings,
            {
                "contentTypeId": 15,
                "areaCode": area_code,
                "pageNo": page_no,
                "numOfRows": 200,
                "arrange": "A",
            },
            tour_api_key,
        )
        payload = _tour_api_get(settings.tour_api_area_based_url, params)
        items = _tour_api_items(payload)
        if not items:
            break

        for item in items:
            contentid = _text(item.get("contentid") or item.get("contentId"))
            if not contentid:
                continue

            intro_params = _tour_api_params(
                settings,
                {"contentId": contentid, "contentTypeId": 15},
                tour_api_key,
            )
            intro_payload = _tour_api_get(settings.tour_api_detail_intro_url, intro_params)
            intro_list = _tour_api_items(intro_payload)
            intro = intro_list[0] if intro_list else {}

            start_value = _text(intro.get("eventstartdate"))
            end_value = _text(intro.get("eventenddate"))
            if not _event_is_active_or_upcoming(start_value, end_value):
                continue

            rows.append(
                EventRow(
                    contentid=contentid,
                    title=_text(item.get("title")),
                    contenttypeid="축제공연행사",
                    contenttypeid_code="15",
                    category="축제",
                    image=_visitkorea_image_url(_text(item.get("firstimage"))),
                    usetime=_text(intro.get("playtime")),
                    restdate="",
                    parking="",
                    place=_text(intro.get("eventplace")),
                    addr=_text(item.get("addr1")),
                    mapy=_text(item.get("mapy")),
                    mapx=_text(item.get("mapx")),
                    tel=_text(item.get("tel") or intro.get("sponsor1tel")),
                    period=_format_period(start_value, end_value),
                    llm_text="",
                )
            )

        page_no += 1

    return rows


def dedupe_event_rows(rows: Iterable[EventRow]) -> List[EventRow]:
    best_by_key: Dict[Tuple[str, str, str], EventRow] = {}

    def score(row: EventRow) -> Tuple[int, int, int, int]:
        return (
            1 if "culture.seoul.go.kr" in row.image else 0,
            1 if row.place else 0,
            1 if row.addr else 0,
            1 if row.period else 0,
        )

    for row in rows:
        key = (_norm_title(row.title), _norm_space(row.period), _norm_addr(row.addr))
        current = best_by_key.get(key)
        if current is None or score(row) > score(current):
            best_by_key[key] = row

    merged = list(best_by_key.values())
    merged.sort(key=lambda r: (r.period or "9999-99-99", r.title, r.addr))
    return merged


def write_event_rows(path: Path, rows: Iterable[EventRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")


def build_festival_image_add(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    tour_api_key: str = "",
    include_tour_api: bool = True,
    max_seoul_pages: Optional[int] = None,
) -> Dict[str, Any]:
    seoul_rows = fetch_seoul_culture_events(max_pages=max_seoul_pages)
    tour_rows: List[EventRow] = []
    effective_key = tour_api_key or os.getenv("TOURAPI_KEY", "").strip()
    if include_tour_api and effective_key:
        tour_rows = fetch_tour_api_events(effective_key)

    merged_rows = dedupe_event_rows([*seoul_rows, *tour_rows])
    write_event_rows(output_path, merged_rows)

    return {
        "output_path": str(output_path),
        "seoul_culture_count": len(seoul_rows),
        "tour_api_count": len(tour_rows),
        "merged_count": len(merged_rows),
        "tour_api_included": bool(tour_rows),
    }
