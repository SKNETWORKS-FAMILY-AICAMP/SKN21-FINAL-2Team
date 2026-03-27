"""TourAPI 원본 데이터 전처리

raw/tourapi_*.jsonl → preprocessed/tourapi_*.json
카테고리별 고유 필드를 유지하면서 공통 필드를 통일한다.
"""

import json
import logging
from pathlib import Path

from .config import (
    PREPROCESSED_DIR,
    RAW_DIR,
    TOURAPI_TYPE_MAP,
    clean_title,
    clean_value,
    enrich_geo,
    first_sentence,
    strip_html,
)

log = logging.getLogger(__name__)

# 카테고리별 필드 매핑 (원본 필드 → 통일 필드)
_FIELD_MAP = {
    "12": {  # 관광지
        "tel": "infocenter",
        "usetime": "usetime",
        "restdate": "restdate",
        "parking": "parking",
    },
    "14": {  # 문화시설
        "tel": "infocenterculture",
        "usetime": "usetimeculture",
        "restdate": "restdateculture",
        "fee": "usefee",
        "parking": "parkingculture",
    },
    "28": {  # 레포츠
        "tel": "infocenterleports",
        "usetime": "usetimeleports",
        "restdate": "restdateleports",
        "fee": "usefeeleports",
        "parking": "parkingleports",
    },
    "32": {  # 숙박
        "tel": "infocenterlodging",
        "parking": "parkinglodging",
    },
    "39": {  # 음식점
        "tel": "infocenterfood",
        "usetime": "opentimefood",
        "restdate": "restdatefood",
        "parking": "parkingfood",
    },
}

# 공통 필드 (이 필드들은 통일 스키마로 추출)
_COMMON_KEYS = {
    "contentid", "title", "contenttypeid", "image", "addr",
    "mapy", "mapx", "tel", "usetime", "restdate", "fee",
    "parking", "description", "summary", "website",
    "category_depth", "tags", "subway_info",
}

# 카테고리별 고유 필드 (details에 남길 필드)
_EXTRA_KEYS = {
    "32": [  # 숙박
        "checkintime", "checkouttime", "roomtype", "roomcount",
        "subfacility", "accomcountlodging", "scalelodging",
        "barbecue", "beauty", "beverage", "bicycle", "campfire",
        "fitness", "foodplace", "karaoke", "publicbath", "publicpc",
        "sauna", "seminar", "sports", "pickup", "refundregulation",
        "reservationlodging", "reservationurl",
    ],
    "39": [  # 음식점
        "firstmenu", "treatmenu", "packing", "smoking",
        "kidsfacility", "seat", "scalefood", "lcnsno",
        "chkcreditcardfood", "reservationfood", "opendatefood",
        "discountinfofood",
    ],
}


# TourAPI 카테고리 코드 → 한국어 매핑 (categoryCode2 API 기반)
_CAT_CODE_MAP: dict[str, str] = {}


def _load_category_map():
    """TourAPI categoryCode2 API로 코드→한국어 매핑 로드."""
    global _CAT_CODE_MAP
    if _CAT_CODE_MAP:
        return

    from ..collect.config import TOURAPI_BASE, TOURAPI_PARAMS
    params = {**TOURAPI_PARAMS, "numOfRows": 1000}

    def _get_items(**extra):
        import requests
        r = requests.get(f"{TOURAPI_BASE}/categoryCode2", params={**params, **extra}, timeout=15)
        body = r.json().get("response", {}).get("body", {}).get("items", "")
        if not body or isinstance(body, str):
            return []
        items = body.get("item", [])
        return items if isinstance(items, list) else [items]

    for c1 in _get_items():
        _CAT_CODE_MAP[c1["code"]] = c1["name"]
        for c2 in _get_items(cat1=c1["code"]):
            _CAT_CODE_MAP[c2["code"]] = c2["name"]
            for c3 in _get_items(cat1=c1["code"], cat2=c2["code"]):
                _CAT_CODE_MAP[c3["code"]] = c3["name"]

    log.info("[tourapi] 카테고리 코드 %d개 로드", len(_CAT_CODE_MAP))


def _build_category_depth(raw: dict) -> str:
    """cat1/cat2/cat3 코드를 한국어로 변환하여 카테고리 경로 생성."""
    _load_category_map()
    codes = [raw.get("cat1", ""), raw.get("cat2", ""), raw.get("cat3", "")]
    names = [_CAT_CODE_MAP.get(c, c) for c in codes if c]
    return " > ".join(names)


def _build_tags(raw: dict) -> list[str]:
    """title + 지역명으로 태그 생성."""
    tags = []
    title = raw.get("title", "")
    if title:
        tags.append(title)
    addr = raw.get("addr1", "")
    if addr:
        parts = addr.split()
        for p in parts[:3]:
            if p not in tags:
                tags.append(p)
    return tags


def _process_one(raw: dict, ctid: str) -> dict:
    """원본 1건을 통일 스키마로 변환."""
    fmap = _FIELD_MAP.get(ctid, {})
    type_name = TOURAPI_TYPE_MAP.get(ctid, ctid)

    result = {
        "contentid": raw.get("contentid"),
        "title": clean_title(clean_value(raw.get("title")) or ""),
        "contenttypeid": type_name,
        "image": clean_value(raw.get("firstimage")),
        "addr": clean_value(strip_html(raw.get("addr1", ""))),
        "mapy": raw.get("mapy"),
        "mapx": raw.get("mapx"),
        "tel": clean_value(strip_html(raw.get(fmap.get("tel", "tel"), ""))),
        "usetime": clean_value(strip_html(raw.get(fmap.get("usetime", "usetime"), ""))),
        "restdate": clean_value(strip_html(raw.get(fmap.get("restdate", "restdate"), ""))),
        "fee": clean_value(strip_html(raw.get(fmap.get("fee", "fee"), ""))),
        "parking": clean_value(strip_html(raw.get(fmap.get("parking", "parking"), ""))),
        "description": clean_value(strip_html(raw.get("overview", ""))),
        "website": clean_value(strip_html(raw.get("homepage", ""))),
        "category_depth": _build_category_depth(raw),
        "tags": None,
        "subway_info": None,
    }

    # 카테고리 고유 필드
    extra_keys = _EXTRA_KEYS.get(ctid, [])
    for key in extra_keys:
        val = clean_value(strip_html(str(raw.get(key, ""))))
        if val:
            result[key] = val

    # None 값 제거
    result = {k: v for k, v in result.items() if v is not None}
    return enrich_geo(result)


def preprocess(content_type_id: str | None = None):
    """TourAPI 전처리.

    content_type_id 지정 시 해당 카테고리만, None이면 전체.
    """
    targets = (
        {content_type_id: TOURAPI_TYPE_MAP[content_type_id]}
        if content_type_id
        else TOURAPI_TYPE_MAP
    )

    for ctid, name in targets.items():
        input_path = RAW_DIR / f"tourapi_{name}.jsonl"
        if not input_path.exists():
            log.warning("[tourapi] %s 원본 파일 없음: %s", name, input_path)
            continue

        output_path = PREPROCESSED_DIR / f"tourapi_{name}.json"
        results = []

        with open(input_path, encoding="utf-8") as f:
            for line in f:
                try:
                    raw = json.loads(line)
                    results.append(_process_one(raw, ctid))
                except (json.JSONDecodeError, KeyError) as e:
                    log.warning("[tourapi] 파싱 실패: %s", e)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        log.info("[tourapi] %s: %d건 → %s", name, len(results), output_path.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    preprocess()
