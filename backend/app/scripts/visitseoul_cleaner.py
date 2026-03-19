"""
Visit Seoul 데이터 전처리 스크립트
====================================
raw/contents_detail_all.json (원본 API) → Visit Korea 호환 스키마로 변환

출력 스키마 (Visit Korea 기준):
    contentid, title, contenttypeid, contenttypeid_code,
    image, usetime, restdate, parking, fee,
    addr, mapy, mapx, tel, source

Visit Seoul 전용 추가 필드:
    category_depth, summary, description, subway_info,
    website, tags, updated_at, multi_lang_list
    (food)         restaurant_type, menu, cuisine_kind, price_range, halal, salam, dietary
    (accommodation) room_type, checkin_time, checkout_time

카테고리 매핑 (contenttypeid):
    문화관광/역사관광/자연관광/체험관광 → 관광지 (12)
    쇼핑                               → 투어   (99)
    음식                               → 음식점 (39)
    숙박                               → 숙박   (32)
    공연시설/행사시설 등               → 콘텐츠 (없음, 문자열만)
"""

import json
import re
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_PATH = DATA_DIR / "raw" / "contents_detail_all.json"
OUT_PATH = DATA_DIR / "contents_visitseoul.json"

TODAY = date.today().isoformat()

# ─── 카테고리 매핑 ────────────────────────────────────────
# (cate_depth 최상위 키워드, 하위 콘텐츠 키워드) → (contenttypeid, code)
CONTENT_KEYWORDS = {"공연", "행사"}   # 관광 카테고리 안에서 콘텐츠로 분류할 하위 키워드

CATE_MAP = [
    ("축제",    None,      None),   # 제외
    ("공연",    None,      None),   # 제외 (최상위 축제/공연/행사)
    ("행사",    None,      None),   # 제외
    ("문화관광", "관광지",  12),
    ("역사관광", "관광지",  12),
    ("자연관광", "관광지",  12),
    ("체험관광", "관광지",  12),
    ("쇼핑",    "투어",    99),
    ("음식",    "음식점",  39),
    ("숙박",    "숙박",    32),
]


def resolve_category(cate_depth: str):
    """cate_depth → (contenttypeid 문자열, contenttypeid_code 숫자 or None)"""
    val = cate_depth.strip()
    for keyword, type_name, code in CATE_MAP:
        if keyword in val:
            if type_name is None:
                return None, None   # 제외 대상
            # 관광 계열이면 하위 키워드 검사해서 콘텐츠 분류
            if type_name == "관광지":
                for ck in CONTENT_KEYWORDS:
                    if ck in val:
                        return "콘텐츠", None
            return type_name, code
    return "관광지", 12   # 기본값


# ─── 필터링 ──────────────────────────────────────────────
def should_exclude(item: dict, contenttypeid) -> bool:
    """True면 제외"""
    # 카테고리 제외 대상
    if contenttypeid is None:
        return True
    # 제목 없음
    if not (item.get("post_sj") or "").strip():
        return True
    # schdul_info_endde 가 존재하면서 비어있거나 과거인 경우
    endde = item.get("schdul_info_endde")
    if endde is not None:
        endde_str = (endde or "").strip()
        if not endde_str:
            return True
        # YYYYMMDD 형식
        try:
            end_date = f"{endde_str[:4]}-{endde_str[4:6]}-{endde_str[6:8]}"
            if end_date < TODAY:
                return True
        except Exception:
            return True
    return False


# ─── HTML 제거 ────────────────────────────────────────────
def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def to_str(val) -> str:
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if v)
    return (str(val) or "").strip()


# ─── 변환 ────────────────────────────────────────────────
def transform(item: dict) -> dict | None:
    cate_depth = item.get("cate_depth") or ""
    contenttypeid, code = resolve_category(cate_depth)

    if should_exclude(item, contenttypeid):
        return None

    extra = item.get("extra") or {}
    traffic = item.get("traffic") or {}

    try:
        mapy = float(traffic.get("map_position_y") or 0) or None
        mapx = float(traffic.get("map_position_x") or 0) or None
    except (ValueError, TypeError):
        mapy, mapx = None, None

    relate_img = item.get("relate_img") or []
    image = relate_img[0] if relate_img else item.get("main_img")

    result = {
        # ── Visit Korea 호환 필드 ──
        "contentid":         item.get("cid"),
        "title":             (item.get("post_sj") or "").strip(),
        "contenttypeid":     contenttypeid,
        "contenttypeid_code": code,
        "image":             image,
        "usetime":           (extra.get("cmmn_use_time") or "").strip() or None,
        "restdate":          (extra.get("closed_days") or "").strip() or None,
        "parking":           None,   # Visit Seoul API에 없음
        "fee":               (extra.get("usage_fee") or "").strip() or None,
        "addr":              (traffic.get("new_adres") or traffic.get("adres") or "").strip() or None,
        "mapy":              mapy,
        "mapx":              mapx,
        "tel":               (extra.get("cmmn_telno") or "").strip() or None,
        "source":            "visitseoul",
        # ── Visit Seoul 전용 필드 ──
        "category_depth":    cate_depth.strip() or None,
        "summary":           (item.get("sumry") or "").strip() or None,
        "description":       strip_html(item.get("post_desc") or "") or None,
        "subway_info":       (traffic.get("subway_info") or "").strip() or None,
        "website":           (extra.get("cmmn_hmpg_url") or "").strip() or None,
        "tags":              item.get("tag") or [],
        "updated_at":        item.get("updt_dt_text"),
        "multi_lang_list":   item.get("multi_lang_list"),
        "place":             (item.get("place") or "").strip() or None,
    }

    # food 전용
    if contenttypeid == "음식점":
        r = item.get("restaurant") or {}
        result.update({
            "restaurant_type": to_str(r.get("type")) or None,
            "menu":            to_str(r.get("fd_reprsnt_menu")) or None,
            "cuisine_kind":    to_str(r.get("kind")) or None,
            "price_range":     to_str(r.get("price_range")) or None,
            "halal":           to_str(r.get("halal")) or None,
            "salam":           to_str(r.get("salam")) or None,
            "dietary":         to_str(r.get("dietary")) or None,
        })

    # accommodation 전용
    if contenttypeid == "숙박":
        a = item.get("accommodation") or {}
        result.update({
            "room_type":     (a.get("stayng_room_type") or "").strip() or None,
            "checkin_time":  (a.get("stayng_chkin_time") or "").strip() or None,
            "checkout_time": (a.get("stayng_chckt_time") or "").strip() or None,
        })

    return result


# ─── 메인 ────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("Visit Seoul 데이터 전처리")
    print("=" * 50)

    with open(RAW_PATH, encoding="utf-8") as f:
        raw_data = json.load(f)
    print(f"원본 로드: {len(raw_data)}건")

    results = []
    skipped = 0
    category_counter: dict[str, int] = {}

    for item in raw_data:
        converted = transform(item)
        if converted is None:
            skipped += 1
            continue
        cat = converted["contenttypeid"]
        category_counter[cat] = category_counter.get(cat, 0) + 1
        results.append(converted)

    print(f"제외: {skipped}건")
    print(f"정제 완료: {len(results)}건")
    print("\n카테고리별 분포:")
    for cat, cnt in sorted(category_counter.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}건")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료 → {OUT_PATH.name}")
    print("=" * 50)


if __name__ == "__main__":
    main()
