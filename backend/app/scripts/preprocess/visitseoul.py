"""VisitSeoul 원본 데이터 전처리

raw/visitseoul.jsonl → preprocessed/visitseoul_{카테고리}.json
카테고리별 고유 필드(restaurant, accommodation 등)를 유지한다.
"""

import json
import logging
from collections import defaultdict

from .config import (
    PREPROCESSED_DIR,
    RAW_DIR,
    VISITSEOUL_EXCLUDE,
    VISITSEOUL_TYPE_MAP,
    clean_title,
    clean_value,
    enrich_geo,
    first_sentence,
    strip_html,
)

log = logging.getLogger(__name__)


def _map_type(cate_depth: str) -> str:
    """cate_depth 문자열에서 contenttypeid 매핑."""
    if not cate_depth:
        return "기타"
    top = cate_depth.strip().split(">")[0].strip()
    return VISITSEOUL_TYPE_MAP.get(top, "기타")


def _process_one(raw: dict) -> dict:
    """원본 1건을 통일 스키마로 변환."""
    extra = raw.get("extra") or {}
    traffic = raw.get("traffic") or {}
    cate_depth = raw.get("cate_depth", "")

    # fee: "N", "F" 등 의미없는 값 처리
    fee_raw = strip_html(extra.get("usage_fee") or extra.get("trrsrt_use_chrge", ""))
    fee = clean_value(fee_raw)
    if fee and fee.upper() in ("N", "F"):
        fee = None

    # category_depth: restaurant.kind가 있으면 반영 (음식 > 한식)
    restaurant = raw.get("restaurant") or {}
    cat_depth = clean_value(cate_depth)
    if isinstance(restaurant, dict):
        kind = restaurant.get("kind")
        if kind and isinstance(kind, list) and kind:
            kind_nm = kind[0].get("code_nm", "")
            if kind_nm and cat_depth:
                cat_depth = f"{cat_depth.strip()} > {kind_nm}"

    result = {
        "contentid": raw.get("cid"),
        "title": clean_title(clean_value(raw.get("post_sj")) or ""),
        "contenttypeid": _map_type(cate_depth),
        "image": clean_value(raw.get("main_img")),
        "addr": clean_value(traffic.get("new_adres") or traffic.get("adres")),
        "mapy": traffic.get("map_position_y"),
        "mapx": traffic.get("map_position_x"),
        "tel": clean_value(extra.get("cmmn_telno")),
        "usetime": clean_value(strip_html(extra.get("cmmn_use_time", ""))),
        "restdate": clean_value(strip_html(extra.get("closed_days", ""))),
        "fee": fee,
        "parking": None,
        "description": clean_value(strip_html(raw.get("post_desc", ""))),
        "summary": clean_value(raw.get("sumry")),
        "website": clean_value(extra.get("cmmn_hmpg_url")),
        "category_depth": cat_depth,
        "tags": [t for t in (raw.get("tag") or []) if isinstance(t, str) and t.strip()],
        "subway_info": clean_value(traffic.get("subway_info")),
    }

    # summary가 없으면 description에서 추출
    if not result["summary"]:
        result["summary"] = first_sentence(result.get("description", ""))

    # 음식점 고유 필드 (평탄화)
    if isinstance(restaurant, dict):
        # restaurant_type: code_nm만 추출
        rtype = restaurant.get("type")
        if rtype and isinstance(rtype, list) and rtype:
            result["restaurant_type"] = rtype[0].get("code_nm", "")

        # menu: fd_reprsnt_menu → menu로 변환, 가격 제거
        menu = clean_value(restaurant.get("fd_reprsnt_menu"))
        if menu:
            import re
            # 줄바꿈+쉼표 모두 구분자로 분리
            parts = re.split(r"[\r\n,]+", menu)
            items = []
            for part in parts:
                name = re.sub(r"[￦₩]?\s*[\d,]+\s*원?", "", part).strip()
                name = name.rstrip("/,- ").strip()
                if name:
                    items.append(name)
            if items:
                result["menu"] = ", ".join(items)

        # halal, salam, kind → 제거 (kind는 category_depth에 반영됨)

    # 숙박 고유 필드 — 제외

    # None 값 제거
    result = {k: v for k, v in result.items() if v is not None}
    return enrich_geo(result)


def preprocess():
    """VisitSeoul 전처리."""
    input_path = RAW_DIR / "visitseoul.jsonl"
    if not input_path.exists():
        log.warning("[visitseoul] 원본 파일 없음: %s", input_path)
        return

    # 카테고리별 분류
    by_type: dict[str, list[dict]] = defaultdict(list)

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            try:
                raw = json.loads(line)
                cate = (raw.get("cate_depth") or "").strip()
                top_cate = cate.split(">")[0].strip()
                if top_cate in VISITSEOUL_EXCLUDE:
                    continue
                processed = _process_one(raw)
                type_name = processed.get("contenttypeid", "기타")
                by_type[type_name].append(processed)
            except (json.JSONDecodeError, KeyError) as e:
                log.warning("[visitseoul] 파싱 실패: %s", e)

    for type_name, items in by_type.items():
        output_path = PREPROCESSED_DIR / f"visitseoul_{type_name}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        log.info("[visitseoul] %s: %d건 → %s", type_name, len(items), output_path.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    preprocess()
