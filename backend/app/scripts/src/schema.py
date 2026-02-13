from __future__ import annotations

from typing import Any, Dict, List

# 1) 공통(목록 + common + intro 정규화 타깃)
COMMON_NORMALIZED_KEYS = [
    "contentid", "contenttypeid", "title",
    "mapx", "mapy", "addr1", "addr2", "tel",
    "overview", "firstimage", "firstimage2",
    "cat1", "cat2", "cat3",
    "lclsSystm1", "lclsSystm2", "lclsSystm3",
    "lDongRegnCd", "lDongSignguCd",
    "keyword", "dist",
    # intro 정규화 키
    "accomcount", "chkbabycarriage", "chkcreditcard", "chkpet",
    "parking", "restdate", "usetime",
]

# 2) intro 원본 키 → 정규화 키 매핑 (contentType별로 이름이 달라지는 필드 흡수)
INTRO_TO_NORMALIZED_MAP = {
    # 수용인원
    "accomcount": "accomcount",

    # 유모차
    "chkbabycarriage": "chkbabycarriage",
    "chkbabycarriageculture": "chkbabycarriage",
    "chkbabycarriageleports": "chkbabycarriage",

    # 카드
    "chkcreditcard": "chkcreditcard",
    "chkcreditcardculture": "chkcreditcard",
    "chkcreditcardleports": "chkcreditcard",

    # 반려동물
    "chkpet": "chkpet",
    "chkpetculture": "chkpet",
    "chkpetleports": "chkpet",

    # 주차
    "parking": "parking",
    "parkingculture": "parking",
    "parkingleports": "parking",

    # 휴무일
    "restdate": "restdate",
    "restdateculture": "restdate",
    "restdateleports": "restdate",

    # 이용시간
    "usetime": "usetime",
    "usetimeculture": "usetime",
    "usetimeleports": "usetime",
}


def pick_keys(row: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in keys:
        if k in row and row[k] not in ("", None):
            out[k] = row[k]
    return out


def normalize_intro_fields(intro: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not isinstance(intro, dict):
        return out
    for src_k, val in intro.items():
        if val in ("", None):
            continue
        dst_k = INTRO_TO_NORMALIZED_MAP.get(src_k)
        if dst_k:
            out[dst_k] = val
    return out


def normalize_common_record(base: Dict[str, Any], common: Dict[str, Any], intro: Dict[str, Any]) -> Dict[str, Any]:
    """
    목록(base) + detailCommon2(common) + detailIntro2(intro)를 합쳐 공통 스키마로 정규화.
    """
    merged: Dict[str, Any] = {}

    # 우선순위: intro(normalized) > common > base (단, intro는 매핑키만)
    merged.update(pick_keys(base, COMMON_NORMALIZED_KEYS))
    merged.update(pick_keys(common, COMMON_NORMALIZED_KEYS))
    merged.update(normalize_intro_fields(intro))

    # 최소 보정
    if "mapy" not in merged and "maxy" in merged:
        merged["mapy"] = merged["maxy"]

    # 문자열 trim
    for k, v in list(merged.items()):
        if isinstance(v, str):
            merged[k] = v.strip()

    return merged
