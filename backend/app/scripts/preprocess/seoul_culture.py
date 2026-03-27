"""서울 열린데이터광장 문화행사 전처리

raw/seoul_culture.jsonl → preprocessed/seoul_culture_문화행사.json
"""

import json
import logging
import re

from .config import PREPROCESSED_DIR, RAW_DIR, _run_async, clean_title, clean_value, enrich_geo, first_sentence, strip_html

log = logging.getLogger(__name__)


def _reverse_geocode_addr(lat, lon) -> str | None:
    """좌표로 역지오코딩하여 주소 반환."""
    from app.utils.geocoder import GeoCoder
    try:
        result = _run_async(GeoCoder.get_instance().reverse_geocoder(lat, lon))
        if result:
            return result.get("road_address") or result.get("jibun_address")
    except Exception as e:
        log.warning("  역지오코딩 실패: (%s, %s) → %s", lat, lon, e)
    return None


# place 정리 패턴 (검색 안 될 때 순차 적용)
_PLACE_STRIP_PATTERNS = [
    r"\s*[※].*$",                           # ※우천 시 연기 등
    r"\s*\d*[A-Za-z]*홀.*$",                 # B홀, 소나무홀, 크라운해태홀 등
    r"\s*Hall\s*\w+.*$",                     # Hall B2 등
    r"\s*\d+층.*$",                          # 2층 등
    r"\s*\d+관.*$",                          # 1관 등
    r"\s*\(.*?\)\s*",                        # (종로 일원) 등
    r"~.*$",                                 # 동대문~종각사거리 → 동대문
]


def _search_place(query: str) -> str | None:
    """네이버 Local Search API로 장소 검색. 결과의 name 반환."""
    import time
    from app.utils.geocoder import GeoCoder
    time.sleep(0.3)  # rate limit 방지
    try:
        results = _run_async(GeoCoder.get_instance().local_search_places(query, limit=1))
        if results:
            return re.sub(r"<[^>]+>", "", results[0].get("name", ""))
    except Exception:
        pass
    return None


def _validate_place(place: str) -> str:
    """place를 네이버 지도에서 검색 가능하도록 정리.

    1차: 원본으로 검색
    2차: 홀/층/부가텍스트 제거 후 검색
    3차: 쉼표 앞 첫 장소만으로 검색
    실패 시 정리된 값 반환.
    """
    if not place:
        return place

    # 1차: 원본
    if _search_place(place):
        return place

    # 2차: 패턴 제거
    cleaned = place.split(",")[0].strip()  # 쉼표 앞만
    for pat in _PLACE_STRIP_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

    if cleaned and cleaned != place:
        if _search_place(cleaned):
            log.info("  place 보정: %s → %s", place[:30], cleaned)
            return cleaned

    # 3차: 건물명 첫 부분만
    first = cleaned.split()[0] if cleaned else place.split()[0]
    if first and first != cleaned:
        if _search_place(first):
            log.info("  place 보정: %s → %s", place[:30], first)
            return first

    # 실패: 정리된 값이라도 반환
    log.warning("  place 검색 실패: %s (정리: %s)", place[:30], cleaned[:30])
    return cleaned or place



def _extract_cultcode(hmpg_addr: str) -> str:
    """HMPG_ADDR에서 cultcode 추출."""
    m = re.search(r"cultcode=(\d+)", hmpg_addr or "")
    return m.group(1) if m else hmpg_addr or ""


def _clean_date(date_str: str) -> str | None:
    """날짜 포맷 정리. '2026-08-16 00:00:00.0' → '2026-08-16'"""
    val = clean_value(date_str)
    if not val:
        return None
    return val[:10]


def _process_one(raw: dict) -> dict:
    """원본 1건을 통일 스키마로 변환."""
    description = clean_value(strip_html(
        raw.get("PROGRAM") or raw.get("ETC_DESC") or ""
    ))

    result = {
        "contentid": _extract_cultcode(raw.get("HMPG_ADDR", "")),
        "title": clean_title(clean_value(raw.get("TITLE")) or ""),
        "contenttypeid": "콘텐츠",
        "image": clean_value(raw.get("MAIN_IMG")),
        "mapy": raw.get("LAT"),
        "mapx": raw.get("LOT"),
        "tel": clean_value(raw.get("INQUIRY")),
        "usetime": clean_value(raw.get("PRO_TIME")),
        "fee": clean_value(raw.get("USE_FEE")),
        "description": description,
        "website": clean_value(raw.get("ORG_LINK") or raw.get("HMPG_ADDR")),
        "category_depth": clean_value(raw.get("CODENAME")),
        # 고유 필드
        "place": clean_value(raw.get("PLACE")),
        "STRTDATE": _clean_date(raw.get("STRTDATE", "")),
        "END_DATE": _clean_date(raw.get("END_DATE", "")),
        "RGSTDATE": _clean_date(raw.get("RGSTDATE", "")),
        "IS_FREE": clean_value(raw.get("IS_FREE")),
        "PLAYER": clean_value(raw.get("PLAYER")),
    }

    # 좌표로 역지오코딩하여 addr 추가
    if not result.get("addr") and result.get("mapy") and result.get("mapx"):
        try:
            lat = float(result["mapy"])
            lon = float(result["mapx"])
            addr = _reverse_geocode_addr(lat, lon)
            if addr:
                result["addr"] = addr
                log.info("  역지오코딩: %s → %s", result.get("title", "")[:20], addr)
        except (ValueError, TypeError):
            pass

    # None 값 제거
    result = {k: v for k, v in result.items() if v is not None}
    return enrich_geo(result)


def preprocess():
    """서울 열린데이터광장 문화행사 전처리."""
    input_path = RAW_DIR / "seoul_culture.jsonl"
    if not input_path.exists():
        log.warning("[seoul_culture] 원본 파일 없음: %s", input_path)
        return

    results = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            try:
                raw = json.loads(line)
                results.append(_process_one(raw))
            except (json.JSONDecodeError, KeyError) as e:
                log.warning("[seoul_culture] 파싱 실패: %s", e)

    output_path = PREPROCESSED_DIR / "seoul_culture_문화행사.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log.info("[seoul_culture] %d건 → %s", len(results), output_path.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    preprocess()
