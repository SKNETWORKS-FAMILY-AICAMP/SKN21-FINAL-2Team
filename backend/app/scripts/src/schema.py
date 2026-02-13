from __future__ import annotations

from typing import Any, Dict

INTRO_TO_NORMALIZED_MAP = {
    "accomcount": "accomcount",

    "chkbabycarriage": "chkbabycarriage",
    "chkbabycarriageculture": "chkbabycarriage",
    "chkbabycarriageleports": "chkbabycarriage",

    "chkcreditcard": "chkcreditcard",
    "chkcreditcardculture": "chkcreditcard",
    "chkcreditcardleports": "chkcreditcard",

    "chkpet": "chkpet",
    "chkpetculture": "chkpet",
    "chkpetleports": "chkpet",

    "parking": "parking",
    "parkingculture": "parking",
    "parkingleports": "parking",

    "restdate": "restdate",
    "restdateculture": "restdate",
    "restdateleports": "restdate",

    "usetime": "usetime",
    "usetimeculture": "usetime",
    "usetimeleports": "usetime",
}

ORDERED_KEEP_FIELDS = [
    "contentid",
    "title",
    "contenttypeid_code",
    "contenttypeid",
    "firstimage",

    "usetime",
    "restdate",
    "parking",

    "addr1",
    "addr2",
    "mapx",
    "mapy",

    "tel",
    "overview",

    "areacode",
    "cat1",
    "cat2",
    "cat3",
    "lclsSystm1",
    "lclsSystm2",
    "lclsSystm3",
    "lDongRegnCd",
    "lDongSignguCd",

    "accomcount",
    "chkbabycarriage",
    "chkcreditcard",
    "chkpet",
    "dist",
]


def _clean_value(v: Any) -> Any:
    if isinstance(v, str):
        s = v.strip()
        if s == "" or s.lower() == "value":
            return None
        return s
    return v


def normalize_intro_fields(intro: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not isinstance(intro, dict):
        return out
    for k, v in intro.items():
        nk = INTRO_TO_NORMALIZED_MAP.get(k)
        if not nk:
            continue
        cv = _clean_value(v)
        if cv is None:
            continue
        out[nk] = cv
    return out


def normalize_common_record(base: Dict[str, Any], common: Dict[str, Any], intro: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    if isinstance(base, dict):
        merged.update(base)
    if isinstance(common, dict):
        merged.update(common)
    merged.update(normalize_intro_fields(intro))

    # mapy 보정 (혹시 maxy로 들어오는 케이스)
    if ("mapy" not in merged or not str(merged.get("mapy", "")).strip()) and str(merged.get("maxy", "")).strip():
        merged["mapy"] = merged.get("maxy")

    # 값 정리 + firstimage2 제거
    cleaned: Dict[str, Any] = {}
    for k, v in merged.items():
        if k == "firstimage2":
            continue
        cv = _clean_value(v)
        if cv is None:
            continue
        cleaned[k] = cv

    # 화이트리스트 + 순서 고정
    out: Dict[str, Any] = {}
    for key in ORDERED_KEEP_FIELDS:
        if key in cleaned:
            out[key] = cleaned[key]

    return out
