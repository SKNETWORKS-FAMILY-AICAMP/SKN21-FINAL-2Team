from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scripts.tour_api.__tour_api import (
    EventRow,
    VISITKOREA_IMAGE_CALL_PREFIX,
    _detail_intro,
    _event_is_active_or_upcoming,
    _format_period,
    _geocode_with_cache,
    _load_geocode_cache,
    _save_geocode_cache,
    _text,
    dedupe_event_rows,
    fetch_seoul_culture_events,
    load_settings,
    write_event_rows,
)

VISITKOREA_SHOW_CALL_URL = "https://korean.visitkorea.or.kr/call"
VISITKOREA_SHOW_REFERER = "https://korean.visitkorea.or.kr/list/travelinfo.do?service=show"
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

TODAY = date.today()
POPPLY_API_BASE = "https://api.popply.co.kr"
DEFAULT_POPUP_RAW_OUTPUT_PATH = Path("backend/data/99_팝업스토어.json")
DEFAULT_POPUP_IMAGE_ADD_PATH = Path("backend/data/image_add/99_팝업스토어_enriched.jsonl")
DEFAULT_POPUP_LLM_CACHE_PATH = Path("backend/data/llm_result/99_팝업스토어_enriched.jsonl")
DEFAULT_FESTIVAL_OUTPUT_PATH = Path("backend/data/image_add/15_축제공연행사_image_add.jsonl")
DEFAULT_CONTENT15_OUTPUT_PATH = Path("backend/data/image_add/15_콘텐츠.jsonl")
DEFAULT_ATTRACTION12_OUTPUT_PATH = Path("backend/data/image_add/12_관광지.jsonl")
DEFAULT_ATTRACTION12_NON_NUMERIC_ADDR_OUTPUT_PATH = Path("backend/data/image_add/12_관광지_address_non_numeric_end.jsonl")
DEFAULT_ATTRACTION12_SOURCE_PATH = Path("backend/data/image_add/12_관광지_image_add.jsonl")
DEFAULT_CULTURE14_SOURCE_PATH = Path("backend/data/image_add/14_문화시설_image_add.jsonl")
DEFAULT_LEPORTS28_SOURCE_PATH = Path("backend/data/image_add/28_레포츠_enriched.jsonl")
SEOUL_EVENT_LIST_URL = "https://culture.seoul.go.kr/culture/culture/cultureEvent/list.do?searchCate=SHOW&menuNo=200008"
SEOUL_EVENT_DETAIL_URL = "https://culture.seoul.go.kr/culture/culture/cultureEvent/view.do"
SEOUL_BASE_URL = "https://culture.seoul.go.kr"


def _format_popup_working_time(raw: Any) -> str:
    if isinstance(raw, str) and raw.strip():
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip()
    if not isinstance(raw, list):
        return ""

    hours: List[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        start = _text(item.get("startDate"))
        end = _text(item.get("endDate"))
        holiday = bool(item.get("holiday"))
        if holiday:
            continue
        if start and end:
            hours.append(f"{start} ~ {end}")

    if not hours:
        return ""
    return hours[0] if len(set(hours)) == 1 else " / ".join(dict.fromkeys(hours))


def _normalize_popup_store(store: Dict[str, Any]) -> Dict[str, Any]:
    detail = store.get("storeDetail") or {}
    return {
        "url": f"https://www.popply.co.kr/popup/{store.get('storeId')}",
        "name": _text(store.get("title") or store.get("name")),
        "schedule": f"{_text(store.get('startDate'))}T00:00:00 ~ {_text(store.get('endDate'))}T00:00:00",
        "location": _text(store.get("address")),
        "hours": _format_popup_working_time(store.get("workingTime")),
        "introduction": _text(detail.get("contents")),
        "thumbnail": _text(store.get("thumbnails")),
        "parking": "주차 가능" if detail.get("parking") is True else ("주차 불가" if detail.get("parking") is False else ""),
        "fee": "무료" if detail.get("free") is True else ("유료" if detail.get("free") is False else ""),
        "pet": "반려동물 동반 가능" if detail.get("pet") is True else "",
        "kids": "웰컴 키즈존" if detail.get("kids") is True else ("노키즈존" if detail.get("noKids") is True else ""),
        "food_ban": "식음료 반입 금지" if detail.get("food") is True else "",
        "adult_only": "19세 이상" if detail.get("adult") is True else "",
        "wifi": "와이파이 가능" if detail.get("wifi") is True else "",
        "photo": "",
        "mapy": _text(store.get("latitude")),
        "mapx": _text(store.get("longitude")),
        "llm_text": "",
    }


def _crawl_popup_store_rows(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    location_filter: str = "서울",
) -> List[Dict[str, Any]]:
    params = {
        "fromDate": date_from or date.today().strftime("%Y-%m-%d"),
        "toDate": date_to or "2026-12-31",
        "address1": location_filter,
    }
    response = requests.get(
        f"{POPPLY_API_BASE}/api/store/",
        params=params,
        headers={"User-Agent": "Mozilla/5.0", "x-source-param": "boardSearch"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    stores = payload.get("data") or []
    if not isinstance(stores, list):
        return []
    return [_normalize_popup_store(store) for store in stores if isinstance(store, dict)]


def _save_popup_store_rows(rows: List[Dict[str, Any]], output_path: Path | str = DEFAULT_POPUP_RAW_OUTPUT_PATH) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
    return str(path.resolve())


def add_content_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--popup-raw-output", type=Path, default=DEFAULT_POPUP_RAW_OUTPUT_PATH)
    parser.add_argument("--popup-image-add-output", type=Path, default=DEFAULT_POPUP_IMAGE_ADD_PATH)
    parser.add_argument("--festival-output", type=Path, default=DEFAULT_FESTIVAL_OUTPUT_PATH)
    parser.add_argument("--content15-output", type=Path, default=DEFAULT_CONTENT15_OUTPUT_PATH)
    parser.add_argument("--content12-output", type=Path, default=DEFAULT_ATTRACTION12_OUTPUT_PATH)
    parser.add_argument("--source12", type=Path, default=DEFAULT_ATTRACTION12_SOURCE_PATH)
    parser.add_argument("--source14", type=Path, default=DEFAULT_CULTURE14_SOURCE_PATH)
    parser.add_argument("--source28", type=Path, default=DEFAULT_LEPORTS28_SOURCE_PATH)
    parser.add_argument("--popup-location-filter", type=str, default="서울")
    parser.add_argument("--popup-visible", action="store_true", default=False)
    parser.add_argument("--max-seoul-pages", type=int, default=None)
    parser.add_argument("--max-visitkorea-pages", type=int, default=None)
    return parser


def parse_args() -> argparse.Namespace:
    parser = add_content_args(argparse.ArgumentParser())
    return parser.parse_args()


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line, strict=False))
    return rows


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _copy_file(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return str(dst.resolve())


def _parse_date(value: str) -> date | None:
    raw = _text(value)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_schedule(schedule: str) -> Tuple[str, str]:
    raw = _text(schedule)
    if "~" not in raw:
        return "", ""
    start_raw, end_raw = [part.strip() for part in raw.split("~", 1)]
    return _parse_datetime_to_date_str(start_raw), _parse_datetime_to_date_str(end_raw)


def _parse_datetime_to_date_str(value: str) -> str:
    raw = _text(value)
    if not raw:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except ValueError:
        return ""


def _split_period(period: str) -> Tuple[str, str]:
    raw = _text(period)
    if "~" not in raw:
        return raw, raw
    start, end = [part.strip() for part in raw.split("~", 1)]
    return start, end


def _is_active_or_upcoming(end_date: str) -> bool:
    parsed = _parse_date(end_date)
    if parsed is None:
        return True
    return parsed >= TODAY


def _popup_content_id(row: Dict[str, Any], fallback_index: int) -> str:
    existing = _text(row.get("contentid"))
    if existing:
        return existing
    basis = "|".join([
        _text(row.get("url")),
        _text(row.get("name") or row.get("title")),
        _text(row.get("location") or row.get("addr")),
        _text(row.get("schedule")),
        _text(row.get("start_date")),
        _text(row.get("end_date")),
    ])
    digest = int(hashlib.md5(basis.encode("utf-8")).hexdigest(), 16) % 1_000_000_000
    return f"9{digest:09d}"


def _normalize_fee(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text in {"0", "0원"}:
        return "무료"
    return text


def _normalize_title(value: str) -> str:
    text = _text(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _clean_popup_intro(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(
        "[" 
        "\U0001F300-\U0001FAFF"
        "\U00002300-\U000023FF"
        "\U00002600-\U000027BF"
        "\uFE00-\uFE0F"
        "]+",
        " ",
        text,
        flags=re.UNICODE,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _popup_identity_key(title: str, addr: str, start_date: str, end_date: str) -> str:
    return "|".join([
        _normalize_title(title),
        _normalize_title(re.sub(r"\([^)]*\)", " ", addr)),
        _text(start_date),
        _text(end_date),
    ])


def _load_popup_llm_cache(path: Path) -> Dict[str, Dict[str, str]]:
    cache: Dict[str, Dict[str, str]] = {}
    for row in _read_jsonl(path):
        key = _popup_identity_key(
            _text(row.get("title")),
            _text(row.get("addr")),
            _text(row.get("start_date")),
            _text(row.get("end_date")),
        )
        if key:
            cache[key] = row
    return cache


def _normalize_popup_image_add_row(
    row: Dict[str, Any],
    llm_cache: Dict[str, Dict[str, str]],
    fallback_index: int,
) -> Dict[str, str]:
    start_date, end_date = _parse_schedule(_text(row.get("schedule")))
    title = _text(row.get("name") or row.get("title"))
    addr = _text(row.get("location") or row.get("addr"))
    cache_row = llm_cache.get(_popup_identity_key(title, addr, start_date, end_date), {})
    fee = "" if _text(row.get("fee")) == "Unknown" else _normalize_fee(_text(row.get("fee")))
    parking = "" if _text(row.get("parking")) == "Unknown" else _text(row.get("parking"))
    llm_text = _text(row.get("llm_text")) or _text(cache_row.get("llm_text")) or _clean_popup_intro(_text(row.get("introduction")))
    image = _text(row.get("thumbnail") or row.get("image") or cache_row.get("image"))

    return {
        "contentid": _popup_content_id(row, fallback_index),
        "title": title,
        "contenttypeid": "팝업스토어",
        "image": image,
        "usetime": _text(row.get("hours") or row.get("usetime")),
        "restdate": "",
        "start_date": start_date,
        "end_date": end_date,
        "parking": parking,
        "fee": fee,
        "addr": addr,
        "mapy": _text(row.get("mapy")),
        "mapx": _text(row.get("mapx")),
        "contenttypeid_code": "99",
        "llm_text": llm_text,
    }


def _build_popup_image_add_rows(raw_rows: List[Dict[str, Any]], llm_cache_path: Path) -> List[Dict[str, str]]:
    llm_cache = _load_popup_llm_cache(llm_cache_path)
    rows: List[Dict[str, str]] = []
    for index, row in enumerate(raw_rows, start=1):
        normalized = _normalize_popup_image_add_row(row, llm_cache, index)
        if not _is_active_or_upcoming(_text(normalized.get("end_date"))):
            continue
        rows.append(normalized)
    rows.sort(key=lambda row: (row.get("end_date") or "9999-99-99", row.get("start_date") or "9999-99-99", row.get("title") or "", row.get("contentid") or ""))
    return rows


def _extract_keyword_candidates(title: str) -> List[str]:
    normalized = _normalize_title(title)
    chunks = [normalized]
    chunks.extend(part.strip().lower() for part in re.findall(r"\[([^\]]+)\]", title) if len(part.strip()) >= 4)
    chunks.extend(part.strip().lower() for part in re.split(r"[:\-]", re.sub(r"\[[^\]]+\]", " ", title)) if len(part.strip()) >= 6)
    deduped: List[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        if chunk and chunk not in seen:
            deduped.append(chunk)
            seen.add(chunk)
    return deduped


def _fetch_seoul_portal_visible_items(session: requests.Session) -> List[Tuple[str, str]]:
    html_text = session.get(SEOUL_EVENT_LIST_URL, timeout=30).text
    items = re.findall(r'/culture/culture/cultureEvent/view\.do\?cultcode=(\d+)&menuNo=200008" title="([^"]+)"', html_text)
    deduped: List[Tuple[str, str]] = []
    seen: set[str] = set()
    for contentid, title in items:
        if contentid in seen:
            continue
        seen.add(contentid)
        deduped.append((contentid, title))
    return deduped


def _discover_deleted_seoul_filters(existing_rows: List[Dict[str, Any]], session: requests.Session) -> Dict[str, Any]:
    visible_items = _fetch_seoul_portal_visible_items(session)
    existing_ids = {str(row.get("contentid")) for row in existing_rows}
    missing_items = [(contentid, title) for contentid, title in visible_items if contentid not in existing_ids]
    blocked_ids = {contentid for contentid, _ in missing_items}
    blocked_titles = {_normalize_title(title) for _, title in missing_items}
    blocked_keywords: List[str] = []
    seen_keywords: set[str] = set()
    for _, title in missing_items:
        for keyword in _extract_keyword_candidates(title):
            if keyword not in seen_keywords:
                blocked_keywords.append(keyword)
                seen_keywords.add(keyword)
    return {
        "visible_count": len(visible_items),
        "missing_count": len(missing_items),
        "blocked_ids": blocked_ids,
        "blocked_titles": blocked_titles,
        "blocked_keywords": blocked_keywords,
        "missing_titles": [title for _, title in missing_items],
    }


def _row_matches_deleted_filter(row: Dict[str, Any], deleted_filter: Dict[str, Any]) -> bool:
    contentid = _text(row.get("contentid"))
    title = _normalize_title(_text(row.get("title")))
    if contentid in deleted_filter["blocked_ids"]:
        return True
    if title in deleted_filter["blocked_titles"]:
        return True
    for keyword in deleted_filter["blocked_keywords"]:
        if keyword and keyword in title:
            return True
    return False


def _filter_festival_rows(festival_rows: List[Dict[str, Any]], deleted_filter: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    filtered: List[Dict[str, Any]] = []
    removed = 0
    for row in festival_rows:
        if _row_matches_deleted_filter(row, deleted_filter):
            removed += 1
            continue
        filtered.append(row)
    return filtered, removed


def _extract_seoul_fee(html_text: str) -> str:
    patterns = [
        r"<span>\s*요금\s*</span>.*?<div class=\"type-td\">\s*<span>(.*?)</span>",
        r"티켓\s*([^|<\"]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.S | re.I)
        if not match:
            continue
        fee = _normalize_fee(match.group(1))
        if fee:
            return fee
    return ""


def _absolute_seoul_url(url: str) -> str:
    raw = _text(url)
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/"):
        return SEOUL_BASE_URL + raw
    return f"{SEOUL_BASE_URL}/{raw.lstrip('/')}"


def _extract_seoul_detail_fields(html_text: str) -> Dict[str, str]:
    patterns = {
        "place": r"<span>\s*장소\s*</span>.*?<div class=\"type-td\">\s*<span>(.*?)</span>",
        "usetime": r"<span>\s*시간\s*</span>.*?<div class=\"type-td\">\s*<span>(.*?)</span>",
        "fee": r"<span>\s*요금\s*</span>.*?<div class=\"type-td\">\s*<span>(.*?)</span>",
        "image": r"<div class=\"intro-top clearfix\">.*?<img src=\"([^\"]+)\"",
    }
    out: Dict[str, str] = {"place": "", "usetime": "", "fee": "", "image": ""}
    for key, pattern in patterns.items():
        match = re.search(pattern, html_text, flags=re.S | re.I)
        if not match:
            continue
        value = _normalize_fee(match.group(1)) if key == "fee" else _text(html.unescape(match.group(1)))
        if key == "image":
            value = _absolute_seoul_url(value)
        out[key] = value
    return out


def _fetch_seoul_fee(contentid: str, session: requests.Session) -> str:
    response = session.get(SEOUL_EVENT_DETAIL_URL, params={"cultcode": contentid, "menuNo": "200008"}, timeout=20)
    response.raise_for_status()
    if "요청하신 페이지가 존재하지 않습니다" in response.text:
        return ""
    return _extract_seoul_fee(response.text)


def _fetch_seoul_detail_fields(contentid: str, session: requests.Session) -> Dict[str, str]:
    response = session.get(SEOUL_EVENT_DETAIL_URL, params={"cultcode": contentid, "menuNo": "200008"}, timeout=20)
    response.raise_for_status()
    if "요청하신 페이지가 존재하지 않습니다" in response.text:
        return {"place": "", "usetime": "", "fee": "", "image": ""}
    return _extract_seoul_detail_fields(response.text)


def _fetch_visitkorea_fee(contentid: str) -> str:
    intro = _detail_intro(load_settings(), contentid, 15)
    return _normalize_fee(_text(intro.get("usetimefestival")))


def _fetch_visitkorea_detail_fields(contentid: str) -> Dict[str, str]:
    intro = _detail_intro(load_settings(), contentid, 15)
    return {
        "usetime": _text(intro.get("playtime")),
        "fee": _normalize_fee(_text(intro.get("usetimefestival"))),
        "place": _text(intro.get("eventplace")),
    }


def _fill_common_text_inference(row: Dict[str, str]) -> None:
    llm_text = _text(row.get("llm_text"))
    if not _text(row.get("parking")):
        if "주차 불가" in llm_text:
            row["parking"] = "주차 불가"
        elif "주차 가능" in llm_text:
            row["parking"] = "주차 가능"
    if not _text(row.get("restdate")) and "연중무휴" in llm_text:
        row["restdate"] = "연중무휴"
    if not _text(row.get("fee")):
        if "무료" in llm_text:
            row["fee"] = "무료"
        else:
            fee_matches = re.findall(r"[A-Z가-힣]*\s?\d[\d,]*원", llm_text)
            if fee_matches:
                row["fee"] = " ".join(dict.fromkeys(match.strip() for match in fee_matches[:3]))


def _enrich_content15_rows(rows: List[Dict[str, str]], session: requests.Session) -> Dict[str, int]:
    summary = {"missing_fee_before": 0, "filled_fee": 0, "filled_usetime": 0, "filled_image": 0, "inferred_parking": 0, "inferred_restdate": 0}
    seoul_cache: Dict[str, Dict[str, str]] = {}
    visitkorea_cache: Dict[str, Dict[str, str]] = {}
    for row in rows:
        before_parking = _text(row.get("parking"))
        before_restdate = _text(row.get("restdate"))
        before_fee = _text(row.get("fee"))
        before_usetime = _text(row.get("usetime"))
        before_image = _text(row.get("image"))

        contentid = _text(row.get("contentid"))
        detail: Dict[str, str] = {}
        if not contentid.startswith("9"):
            if contentid not in seoul_cache:
                try:
                    seoul_cache[contentid] = _fetch_seoul_detail_fields(contentid, session)
                except Exception:
                    seoul_cache[contentid] = {"place": "", "usetime": "", "fee": "", "image": ""}
            detail = seoul_cache[contentid]
            if not any(detail.values()):
                if contentid not in visitkorea_cache:
                    try:
                        visitkorea_cache[contentid] = _fetch_visitkorea_detail_fields(contentid)
                    except Exception:
                        visitkorea_cache[contentid] = {"place": "", "usetime": "", "fee": ""}
                detail = visitkorea_cache[contentid]

        if not before_usetime and _text(detail.get("usetime")):
            row["usetime"] = _text(detail.get("usetime"))
            summary["filled_usetime"] += 1
        if not before_image and _text(detail.get("image")):
            row["image"] = _text(detail.get("image"))
            summary["filled_image"] += 1
        if not before_fee:
            summary["missing_fee_before"] += 1
            fee = _normalize_fee(_text(detail.get("fee")))
            if not fee and contentid.startswith("9"):
                fee = "무료"
            if fee:
                row["fee"] = fee
                summary["filled_fee"] += 1

        _fill_common_text_inference(row)
        if not before_parking and _text(row.get("parking")):
            summary["inferred_parking"] += 1
        if not before_restdate and _text(row.get("restdate")):
            summary["inferred_restdate"] += 1
        time.sleep(0.02)
    return summary


def _normalize_popup_row(row: Dict[str, Any], fallback_index: int) -> Dict[str, str]:
    if "schedule" in row:
        start_date, end_date = _parse_schedule(_text(row.get("schedule")))
        fee = "" if _text(row.get("fee")) == "Unknown" else _normalize_fee(_text(row.get("fee")))
        return {
            "contentid": _popup_content_id(row, fallback_index),
            "title": _text(row.get("name") or row.get("title")),
            "contenttypeid": "콘텐츠",
            "image": _text(row.get("thumbnail") or row.get("image")),
            "usetime": _text(row.get("hours") or row.get("usetime")),
            "restdate": _text(row.get("restdate")),
            "start_date": start_date,
            "end_date": end_date,
            "parking": "" if _text(row.get("parking")) == "Unknown" else _text(row.get("parking")),
            "fee": fee,
            "addr": _text(row.get("location") or row.get("addr")),
            "mapy": _text(row.get("mapy")),
            "mapx": _text(row.get("mapx")),
            "contenttypeid_code": "15",
            "llm_text": _text(row.get("llm_text")),
        }
    return {
        "contentid": _text(row.get("contentid")),
        "title": _text(row.get("title")),
        "contenttypeid": "콘텐츠",
        "image": _text(row.get("image")),
        "usetime": _text(row.get("usetime")),
        "restdate": _text(row.get("restdate")),
        "start_date": _text(row.get("start_date")),
        "end_date": _text(row.get("end_date")),
        "parking": _text(row.get("parking")),
        "fee": _normalize_fee(_text(row.get("fee"))),
        "addr": _text(row.get("addr")),
        "mapy": _text(row.get("mapy")),
        "mapx": _text(row.get("mapx")),
        "contenttypeid_code": "15",
        "llm_text": _text(row.get("llm_text")),
    }


def _normalize_festival_row(row: Dict[str, Any]) -> Dict[str, str]:
    start_date, end_date = _split_period(_text(row.get("period")))
    return {
        "contentid": _text(row.get("contentid")),
        "title": _text(row.get("title")),
        "contenttypeid": "콘텐츠",
        "image": _text(row.get("image")),
        "usetime": _text(row.get("usetime")),
        "restdate": _text(row.get("restdate")),
        "start_date": start_date,
        "end_date": end_date,
        "parking": _text(row.get("parking")),
        "fee": _normalize_fee(_text(row.get("fee"))),
        "addr": _text(row.get("addr")),
        "mapy": _text(row.get("mapy")),
        "mapx": _text(row.get("mapx")),
        "contenttypeid_code": "15",
        "llm_text": _text(row.get("llm_text")),
    }


def _build_15_content(
    popup_rows: List[Dict[str, Any]],
    festival_rows: List[Dict[str, Any]],
    output_path: Path,
    session: requests.Session,
) -> Dict[str, Any]:
    normalized_rows = [_normalize_festival_row(row) for row in festival_rows]
    normalized_rows.extend(_normalize_popup_row(row, index) for index, row in enumerate(popup_rows, start=1))
    active_rows = [row for row in normalized_rows if _is_active_or_upcoming(_text(row.get("end_date")))]
    enrich_summary = _enrich_content15_rows(active_rows, session)
    active_rows.sort(key=lambda row: (row.get("end_date") or "9999-99-99", row.get("start_date") or "9999-99-99", row.get("title") or "", row.get("contentid") or ""))
    _write_jsonl(output_path, active_rows)
    return {
        "output_path": str(output_path.resolve()),
        "popup_count": len(popup_rows),
        "festival_count": len(festival_rows),
        "active_or_upcoming_count": len(active_rows),
        "content_enrich_summary": enrich_summary,
    }


def _fee_from_fees_field(row: Dict[str, Any]) -> str:
    fees = row.get("fees")
    if isinstance(fees, list):
        parts = []
        for item in fees:
            if not isinstance(item, dict):
                continue
            text = _normalize_fee(_text(item.get("text")))
            if text:
                parts.append(text)
        if parts:
            return " ".join(parts)
    return ""


def _normalize_12_like_row(row: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(row)
    merged["contenttypeid"] = "관광지"
    merged["contenttypeid_code"] = "12"
    if not _text(merged.get("fee")):
        fee = _fee_from_fees_field(merged)
        if fee:
            merged["fee"] = fee
    merged.pop("fees", None)
    _fill_common_text_inference(merged)
    return merged


def _apply_12_manual_overrides(rows: List[Dict[str, Any]], override_path: Path) -> int:
    if not override_path.exists():
        return 0

    override_rows = _read_jsonl(override_path)
    override_map = {
        _text(row.get("contentid")): row
        for row in override_rows
        if _text(row.get("contentid"))
    }

    applied = 0
    for row in rows:
        contentid = _text(row.get("contentid"))
        override = override_map.get(contentid)
        if not override:
            continue

        old_title = _text(row.get("title"))
        for key, value in override.items():
            if key == "contentid":
                continue
            if value is None:
                continue
            if isinstance(value, str) and not value.strip() and key not in {"restdate", "usetime", "parking", "fee", "llm_text"}:
                continue
            row[key] = value

        new_title = _text(row.get("title"))
        if old_title and new_title and old_title != new_title:
            llm_text = _text(row.get("llm_text"))
            if llm_text:
                row["llm_text"] = llm_text.replace(old_title, new_title)
        applied += 1

    return applied


def _geocode_queries_for_addr(addr: str) -> List[str]:
    raw = _text(addr)
    if not raw:
        return []
    no_paren = re.sub(r"\([^)]*\)", " ", raw)
    no_paren = re.sub(r"\s+", " ", no_paren).strip()
    queries: List[str] = []
    for query in [raw, no_paren]:
        normalized = _text(query)
        if normalized and normalized not in queries:
            queries.append(normalized)
    return queries


def _regeocode_12_rows(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    settings = load_settings()
    cache = _load_geocode_cache(settings)
    geocode_calls = [0]
    geocoded = 0
    failed = 0

    for row in rows:
        addr = _text(row.get("addr"))
        if not addr:
            failed += 1
            continue

        result: Optional[Tuple[float, float]] = None
        for query in _geocode_queries_for_addr(addr):
            result = _geocode_with_cache(settings, query, cache, geocode_calls, 10**9)
            if result:
                break

        if result:
            x, y = result
            row["mapx"] = str(x)
            row["mapy"] = str(y)
            geocoded += 1
        else:
            failed += 1

    _save_geocode_cache(settings, cache)
    return {
        "geocoded_count": geocoded,
        "geocode_failed_count": failed,
        "geocode_calls": geocode_calls[0],
    }


def _fallback_contentid_for_12(row: Dict[str, Any]) -> str:
    contentid = _text(row.get("contentid"))
    if contentid:
        return contentid
    basis = "|".join([
        _text(row.get("title")),
        _text(row.get("addr")),
        _text(row.get("mapx")),
        _text(row.get("mapy")),
    ])
    digest = hashlib.md5(basis.encode("utf-8")).hexdigest()[:12]
    return f"12MISSING_{digest}"


def _has_non_numeric_addr_end(addr: str) -> bool:
    raw = _text(addr)
    if not raw:
        return False
    raw = re.sub(r"\([^)]*\)\s*$", "", raw).strip()
    return re.search(r"(\d+(?:-\d+)?(?:번지)?|\d+길|\d+로)\s*$", raw) is None


def _build_12_attraction(
    source12: Path,
    source14: Path,
    source28: Path,
    output_path: Path,
    addr_override_path: Path = DEFAULT_ATTRACTION12_NON_NUMERIC_ADDR_OUTPUT_PATH,
) -> Dict[str, Any]:
    rows12 = [_normalize_12_like_row(row) for row in _read_jsonl(source12)]
    rows14 = [_normalize_12_like_row(row) for row in _read_jsonl(source14)]
    rows28 = [_normalize_12_like_row(row) for row in _read_jsonl(source28)]

    merged_map: Dict[str, Dict[str, Any]] = {}
    for row in [*rows12, *rows14, *rows28]:
        contentid = _fallback_contentid_for_12(row)
        row["contentid"] = contentid
        merged_map[contentid] = row
    merged_rows = list(merged_map.values())
    override_count = _apply_12_manual_overrides(merged_rows, addr_override_path)
    geocode_summary = _regeocode_12_rows(merged_rows)
    merged_rows.sort(key=lambda row: (_text(row.get("title")), _text(row.get("contentid"))))
    _write_jsonl(output_path, merged_rows)
    non_numeric_addr_rows = [row for row in merged_rows if _has_non_numeric_addr_end(_text(row.get("addr")))]
    return {
        "output_path": str(output_path.resolve()),
        "addr_override_path": str(addr_override_path.resolve()),
        "source12_count": len(rows12),
        "source14_count": len(rows14),
        "source28_count": len(rows28),
        "merged_count": len(merged_rows),
        "override_count": override_count,
        "non_numeric_addr_count": len(non_numeric_addr_rows),
        **geocode_summary,
    }


def run_content_collection(args: argparse.Namespace) -> Dict[str, Any]:
    settings = load_settings()
    session = requests.Session()
    try:
        popup_rows = _crawl_popup_store_rows(
            location_filter=args.popup_location_filter,
        )
        popup_raw_path = settings.project_root / args.popup_raw_output
        popup_raw_saved_path = _save_popup_store_rows(popup_rows, popup_raw_path)

        popup_image_add_rows = _build_popup_image_add_rows(
            popup_rows,
            settings.project_root / DEFAULT_POPUP_LLM_CACHE_PATH,
        )
        popup_image_add_path = settings.project_root / args.popup_image_add_output
        _write_jsonl(popup_image_add_path, popup_image_add_rows)
        popup_preprocess_summary: Dict[str, Any] | None = {
            "popup_image_add_path": str(popup_image_add_path.resolve()),
            "popup_image_add_count": len(popup_image_add_rows),
            "popup_schema_normalized_in_crawl": True,
            "popup_llm_cache_path": str((settings.project_root / DEFAULT_POPUP_LLM_CACHE_PATH).resolve()),
        }

        existing_festival_rows = _read_jsonl(settings.project_root / args.festival_output)
        deleted_filter = _discover_deleted_seoul_filters(existing_festival_rows, session)

        festival_summary = build_festival_image_add_crawl_only(
            output_path=args.festival_output,
            max_seoul_pages=args.max_seoul_pages,
            max_visitkorea_pages=args.max_visitkorea_pages,
        )
        festival_output_path = settings.project_root / args.festival_output
        crawled_festival_rows = _read_jsonl(festival_output_path)
        filtered_festival_rows, removed_festival_count = _filter_festival_rows(crawled_festival_rows, deleted_filter)
        _write_jsonl(festival_output_path, filtered_festival_rows)

        content15_summary = _build_15_content(
            popup_rows=popup_image_add_rows,
            festival_rows=filtered_festival_rows,
            output_path=settings.project_root / args.content15_output,
            session=session,
        )
        content12_summary = _build_12_attraction(
            source12=settings.project_root / args.source12,
            source14=settings.project_root / args.source14,
            source28=settings.project_root / args.source28,
            output_path=settings.project_root / args.content12_output,
        )

        return {
            "popup_raw_summary": {
                "output_path": popup_raw_saved_path,
                "popup_raw_count": len(popup_rows),
                "location_filter": args.popup_location_filter,
            },
            "popup_preprocess_summary": popup_preprocess_summary,
            "festival_deleted_filter_summary": {
                "visible_count": deleted_filter["visible_count"],
                "missing_count": deleted_filter["missing_count"],
                "blocked_keywords": deleted_filter["blocked_keywords"],
                "missing_titles": deleted_filter["missing_titles"],
                "removed_from_crawled_festival_count": removed_festival_count,
            },
            "festival_crawl_summary": festival_summary,
            "content15_summary": content15_summary,
            "content12_summary": content12_summary,
        }
    finally:
        session.close()


def main() -> int:
    args = parse_args()
    summary = run_content_collection(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
