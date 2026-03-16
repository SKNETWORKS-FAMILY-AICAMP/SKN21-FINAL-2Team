"""
Step 3: 스키마 평탄화 + 텍스트 전처리 + 중복 제거 + tags/llm_text 생성
======================================================================
1. detail_intro 평탄화 (카테고리별 필드 병합)
2. 텍스트 정규화 (HTML 제거, 공백 정리)
3. visitseoul 대비 유사 중복 제거 (ratio >= 0.9)
4. category_depth 코드→한글 변환
5. tags 생성 (규칙 기반)
6. llm_text 생성 (template 방식)

관광지/음식점/숙박: enriched → preprocessed
콘텐츠/투어: JSONL → preprocessed (template)

입력:
  - data/add(image,info)/visitkorea_only/visitkorea_only_{카테고리}_enriched.json
  - data/add(image,info)/visitkorea_only/visitkorea_only_{카테고리}_intro_raw.jsonl
  - data/add(image,info)/visitkorea_only/visitkorea_only_{콘텐츠,투어}.jsonl
출력:
  - data/preprocessed/visitkorea_{카테고리}.json
  - data/preprocessed/visitkorea_{콘텐츠,투어}_template.json

사용법:
  cd backend
  python -u data/scripts/visitkorea/step3_preprocess.py
"""

import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2]
VK_ONLY_DIR = DATA_DIR / "add(image,info)" / "visitkorea_only"
OUT_DIR = DATA_DIR / "preprocessed"
OUT_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════
# 공용 유틸
# ══════════════════════════════════════════════════════════════

def strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^{}]+\{[^}]*\}", "", text)
    text = re.sub(r"^[^가-힣\w\"\']+", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def normalize(text: str) -> str:
    if not text:
        return ""
    text = strip_html(text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_category_depth(text: str) -> str:
    parts = [p.strip() for p in text.split(">")]
    return " > ".join(p for p in parts if p)


def to_float(val):
    try:
        f = float(val)
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return data


def extract_district(addr: str) -> list:
    """주소에서 구/동 지역명 추출"""
    tags = []
    m = re.search(r"서울(?:특별시)?\s*(\S+구)", addr)
    if m:
        gu = m.group(1)
        tags.append(gu)
        short = gu.replace("구", "")
        if len(short) >= 2:
            tags.append(short)
    m2 = re.search(r"[(\s]?([가-힣]{2,4}동)[)\s,]?", addr)
    if m2 and m2.group(1) not in tags:
        tags.append(m2.group(1))
    return tags


def print_stats(results: list[dict], out_path: Path):
    has_tags = sum(1 for r in results if r.get("tags"))
    avg_tags = sum(len(r.get("tags", [])) for r in results) / max(len(results), 1)
    has_llm = sum(1 for r in results if r.get("llm_text"))
    print(f"    출력: {len(results)}건 → {out_path.name}")
    print(f"    tags: {has_tags}건 (평균 {avg_tags:.1f}개)")
    print(f"    llm_text: {has_llm}건")
    for r in results[:2]:
        print(f"\n    [{r.get('title')}]")
        print(f"      tags: {r.get('tags', [])}")
        print(f"      llm_text: {r.get('llm_text', '')[:200]}...")


# ══════════════════════════════════════════════════════════════
# category_depth 코드→한글 변환
# ══════════════════════════════════════════════════════════════

def load_category_map() -> dict:
    map_file = VK_ONLY_DIR / "tourapi_category_map.json"
    if map_file.exists():
        with open(map_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def fix_category_depth(cd: str, cat_map: dict) -> str:
    if not cd:
        return cd
    parts = [p.strip() for p in cd.split(">")]
    result = []
    for p in parts:
        p = p.strip()
        if re.match(r"^[A-Z]\d+$", p) and p in cat_map:
            result.append(cat_map[p])
        else:
            result.append(p)
    return " > ".join(result)


# ══════════════════════════════════════════════════════════════
# 유사 중복 제거
# ══════════════════════════════════════════════════════════════

MANUAL_REMOVE_TITLES = {
    "국립4·19민주묘지", "북촌전통공예체험관", "삼해소주", "서울어린이대공원",
    "홍지문 및 탕춘대성", "서울아트센터 도암홀·도암갤러리", "KT&G 상상마당 홍대",
    "서울 서초 글램핑 청계산장", "응봉산 암벽등반공원", "라 쿠치나",
    "먼데이투선데이", "미 피아체", "남대문 갈치조림골목",
}


def load_visitseoul_titles() -> list[str]:
    titles = []
    for cat in ["관광지", "음식점", "숙박", "투어"]:
        f = OUT_DIR / f"visitseoul_{cat}.json"
        if f.exists():
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            titles.extend(d.get("title", "") for d in data)
    return titles


def find_duplicates(vk_items: list[dict], vs_titles: list[str]) -> set[str]:
    remove_titles = set()
    for item in vk_items:
        vk_title = item.get("title", "").strip()
        if vk_title in MANUAL_REMOVE_TITLES:
            remove_titles.add(vk_title)
            continue
        for vs_title in vs_titles:
            if SequenceMatcher(None, vk_title, vs_title).ratio() >= 0.9:
                remove_titles.add(vk_title)
                break
    return remove_titles


# ══════════════════════════════════════════════════════════════
# detail_intro 평탄화 (관광지 / 음식점 / 숙박)
# ══════════════════════════════════════════════════════════════

def flatten_intro_관광지(item: dict) -> dict:
    di = item.pop("detail_intro", None) or {}
    if not item.get("tel") and di.get("infocenter"):
        item["tel"] = di["infocenter"]
    if not item.get("usetime") and di.get("usetime"):
        item["usetime"] = di["usetime"]
    if not item.get("restdate") and di.get("restdate"):
        item["restdate"] = di["restdate"]
    if di.get("parking"):
        item["parking"] = di["parking"]
    return item


def flatten_intro_음식점(item: dict) -> dict:
    di = item.pop("detail_intro", None) or {}
    if not item.get("tel") and di.get("infocenterfood"):
        item["tel"] = di["infocenterfood"]
    if not item.get("menu"):
        parts = []
        if di.get("firstmenu"):
            parts.append(di["firstmenu"])
        if di.get("treatmenu"):
            parts.append(di["treatmenu"])
        if parts:
            item["menu"] = " / ".join(parts)
    if di.get("firstmenu"):
        item["firstmenu"] = di["firstmenu"]
    if not item.get("usetime") and di.get("opentimefood"):
        item["usetime"] = di["opentimefood"]
    if di.get("restdatefood"):
        item["restdate"] = di["restdatefood"]
    if di.get("parkingfood"):
        item["parking"] = di["parkingfood"]
    if di.get("packing"):
        item["packing"] = di["packing"]
    if not item.get("restaurant_type"):
        cd = item.get("category_depth", "") or ""
        parts = [p.strip() for p in cd.split(">")]
        if len(parts) >= 3 and parts[2].strip():
            item["restaurant_type"] = parts[2].strip()
    return item


def flatten_intro_숙박(item: dict) -> dict:
    di = item.pop("detail_intro", None) or {}
    if not item.get("tel") and di.get("infocenterlodging"):
        item["tel"] = di["infocenterlodging"]
    if di.get("checkintime"):
        item["checkintime"] = di["checkintime"]
    if di.get("checkouttime"):
        item["checkouttime"] = di["checkouttime"]
    if not item.get("usetime"):
        ci = di.get("checkintime", "")
        co = di.get("checkouttime", "")
        if ci and co:
            item["usetime"] = f"체크인 {ci} / 체크아웃 {co}"
    if di.get("parkinglodging"):
        item["parking"] = di["parkinglodging"]
    subfacility = di.get("subfacility", "")
    foodplace = di.get("foodplace", "")
    facilities = [s for s in [subfacility, foodplace] if s]
    if facilities:
        item["subfacility"] = ", ".join(facilities)
    if not item.get("room_type"):
        cd = item.get("category_depth", "") or ""
        parts = [p.strip() for p in cd.split(">")]
        if len(parts) >= 3 and parts[2].strip():
            item["room_type"] = parts[2].strip()
    if di.get("reservationlodging"):
        item["reservation"] = di["reservationlodging"]
    if di.get("accomcountlodging"):
        item["accomcount"] = di["accomcountlodging"]
    return item


FLATTEN_FN = {"관광지": flatten_intro_관광지, "음식점": flatten_intro_음식점, "숙박": flatten_intro_숙박}


# ══════════════════════════════════════════════════════════════
# 텍스트 정규화 (transform)
# ══════════════════════════════════════════════════════════════

TEXT_FIELDS = (
    "usetime", "restdate", "fee", "addr", "tel", "subway_info", "website",
    "title", "parking", "packing", "firstmenu", "restaurant_type",
    "checkintime", "checkouttime", "subfacility", "room_type",
    "reservation", "accomcount",
)


def transform(item: dict) -> dict:
    result = {}
    for key, val in item.items():
        if key in ("mapy", "mapx"):
            result[key] = to_float(val)
        elif key == "category_depth" and isinstance(val, str):
            result[key] = normalize_category_depth(val) or None
        elif key in ("description", "summary"):
            result[key] = normalize(val) if val else None
        elif key == "menu" and val:
            val = normalize(val)
            val = re.sub(r"\s*/\s*", ", ", val)
            result[key] = val
        elif key in TEXT_FIELDS:
            result[key] = normalize(val) if val else None
        elif key == "tags":
            continue
        else:
            result[key] = val
    return {k: v for k, v in result.items() if v is not None and v != [] and v != ""}


# ══════════════════════════════════════════════════════════════
# tags 생성 (규칙 기반)
# ══════════════════════════════════════════════════════════════

CAT_DEPTH_SKIP = {"자연", "음식", "문화관광", "레포츠", "쇼핑", "인문"}


def extract_category_tags(category_depth: str) -> list:
    if not category_depth:
        return []
    parts = [p.strip() for p in category_depth.split(">")]
    tags = []
    for p in parts:
        p = p.strip()
        if p and len(p) >= 2 and p not in CAT_DEPTH_SKIP:
            for sub in p.split("/"):
                sub = sub.strip()
                if sub and len(sub) >= 2:
                    tags.append(sub)
    return tags


def extract_from_text(text: str, max_count: int = 5) -> list:
    if not text:
        return []
    tags = []
    seen = set()

    def add(t):
        t = t.strip()
        if re.search(r"(은|는|이|가|을|를|의|에|로|와|과|도|에서|으로|이다|하는|있는)$", t):
            return
        if t and 2 <= len(t) <= 10 and t not in seen:
            seen.add(t)
            tags.append(t)

    for m in re.finditer(r"['\u2018\u2019\u201c\u201d]([가-힣A-Za-z0-9\s]{2,15})['\u2018\u2019\u201c\u201d]", text):
        add(m.group(1).strip())
    for m in re.finditer(r"[（(]([가-힣]{2,10})[）)]", text):
        add(m.group(1).strip())
    for m in re.finditer(r"([가-힣]{2,6})(?:으?로\s*(?:유명|알려진|잘\s*알려진|손꼽히는|불리는))", text):
        add(m.group(1))
    for m in re.finditer(r"대표\s*(?:메뉴는?\s*)?([가-힣]{2,6})", text):
        add(m.group(1))
    for m in re.finditer(r"([가-힣]{2,6})\s*(?:맛집|전문점|전문|명소)", text):
        add(m.group(1))

    return tags[:max_count]


def generate_tags(item: dict) -> list:
    tags = []
    seen = set()

    def add(tag):
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)

    if title := item.get("title"):
        add(title)
    if addr := item.get("addr"):
        for t in extract_district(addr):
            add(t)
    if cd := item.get("category_depth"):
        for t in extract_category_tags(cd):
            add(t)
    if rt := item.get("restaurant_type"):
        add(rt)
    if fm := item.get("firstmenu"):
        add(fm)
    combined = f"{item.get('summary', '') or ''} {item.get('description', '') or ''}"
    if combined.strip():
        for t in extract_from_text(combined, max_count=5):
            add(t)
    return tags


# ══════════════════════════════════════════════════════════════
# llm_text 생성 (template) — 관광지/음식점/숙박
# ══════════════════════════════════════════════════════════════

def build_llm_text_관광지(item: dict) -> str:
    lines = []
    if v := item.get("title"):    lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):     lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"): lines.append(f"- 카테고리: {v}")
    if tags := item.get("tags"):  lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("usetime"):  lines.append(f"- 이용시간: {v}")
    if v := item.get("restdate"): lines.append(f"- 휴무일: {v}")
    if v := item.get("fee"):      lines.append(f"- 입장료: {v}")
    if v := item.get("parking"):  lines.append(f"- 주차: {v}")
    intro = item.get("description") or item.get("summary") or ""
    if intro: lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def build_llm_text_음식점(item: dict) -> str:
    lines = []
    if v := item.get("title"):     lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):      lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"): lines.append(f"- 카테고리: {v}")
    if tags := item.get("tags"):   lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("firstmenu"): lines.append(f"- 대표메뉴: {v}")
    if v := item.get("menu"):      lines.append(f"- 메뉴: {v}")
    if v := item.get("usetime"):   lines.append(f"- 영업시간: {v}")
    if v := item.get("restdate"):  lines.append(f"- 휴무일: {v}")
    if v := item.get("packing"):   lines.append(f"- 포장: {v}")
    if v := item.get("parking"):   lines.append(f"- 주차: {v}")
    intro = item.get("description") or item.get("summary") or ""
    if intro: lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def build_llm_text_숙박(item: dict) -> str:
    lines = []
    if v := item.get("title"):       lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):        lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"): lines.append(f"- 카테고리: {v}")
    if tags := item.get("tags"):     lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("room_type"):   lines.append(f"- 객실유형: {v}")
    if v := item.get("usetime"):     lines.append(f"- 체크인/아웃: {v}")
    if v := item.get("fee"):         lines.append(f"- 요금: {v}")
    if v := item.get("parking"):     lines.append(f"- 주차: {v}")
    if v := item.get("subfacility"): lines.append(f"- 부대시설: {v}")
    if v := item.get("accomcount"):  lines.append(f"- 수용인원: {v}")
    if v := item.get("reservation"): lines.append(f"- 예약: {v}")
    intro = item.get("description") or item.get("summary") or ""
    if intro: lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


LLM_TEXT_FN = {"관광지": build_llm_text_관광지, "음식점": build_llm_text_음식점, "숙박": build_llm_text_숙박}

# llm_text 전용 필드 (생성 후 최종 스키마에서 제거)
LLM_ONLY_FIELDS = {"packing", "firstmenu", "checkintime", "checkouttime", "subfacility", "reservation", "accomcount"}


# ══════════════════════════════════════════════════════════════
# detail_intro 로드 (intro_raw.jsonl → contentid 매핑)
# ══════════════════════════════════════════════════════════════

def load_intro_map(cat_name: str) -> dict:
    intro_file = VK_ONLY_DIR / f"visitkorea_only_{cat_name}_intro_raw.jsonl"
    intro_map = {}
    for d in load_jsonl(intro_file):
        if d.get("detail_intro"):
            intro_map[str(d["contentid"])] = d["detail_intro"]
    return intro_map


# ══════════════════════════════════════════════════════════════
# 관광지 / 음식점 / 숙박 처리
# ══════════════════════════════════════════════════════════════

def process_main_category(category: str, vs_titles: list[str], cat_map: dict):
    in_path = VK_ONLY_DIR / f"visitkorea_only_{category}_enriched.json"
    out_path = OUT_DIR / f"visitkorea_{category}.json"

    if not in_path.exists():
        print(f"  [SKIP] {in_path.name} 없음")
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    # intro_raw 병합
    intro_map = load_intro_map(category)
    for item in data:
        cid = str(item.get("contentid", ""))
        if cid in intro_map and "detail_intro" not in item:
            item["detail_intro"] = intro_map[cid]
    print(f"  detail_intro 병합: {len(intro_map)}건")

    # contentid 중복 제거
    seen_cids = set()
    deduped = []
    for item in data:
        cid = str(item.get("contentid", ""))
        if cid not in seen_cids:
            seen_cids.add(cid)
            deduped.append(item)
    if len(deduped) < len(data):
        print(f"  contentid 중복 제거: {len(data)} → {len(deduped)}건")
    data = deduped

    print(f"\n  {category}: {len(data)}건 입력")

    # 유사 중복 제거
    dup_titles = find_duplicates(data, vs_titles)
    data = [d for d in data if d.get("title", "").strip() not in dup_titles]
    print(f"    중복 제거: {len(dup_titles)}건 → {len(data)}건 남음")

    flatten_fn = FLATTEN_FN.get(category, lambda x: x)
    llm_fn = LLM_TEXT_FN.get(category, build_llm_text_관광지)

    results = []
    for item in data:
        if cd := item.get("category_depth"):
            item["category_depth"] = fix_category_depth(cd, cat_map)
        item = flatten_fn(item)
        cleaned = transform(item)
        cleaned["tags"] = generate_tags(cleaned)
        cleaned["llm_text"] = llm_fn(cleaned)
        for field in LLM_ONLY_FIELDS:
            cleaned.pop(field, None)
        results.append(cleaned)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print_stats(results, out_path)


# ══════════════════════════════════════════════════════════════
# 콘텐츠 처리
# ══════════════════════════════════════════════════════════════

MOOD_KEYWORDS = {
    "감동", "힐링", "웅장", "아름다운", "로맨틱", "신나는", "따뜻한",
    "잔잔한", "서정적", "우아한", "화려한", "몽환적", "역동적", "경쾌한",
    "서정", "낭만", "감성", "고요한", "편안한", "유쾌한", "코믹",
    "스릴", "긴장감", "비장", "애절", "섬세한", "깊이 있는",
    "클래식", "현대적", "전통", "재즈", "국악", "뮤지컬", "연극",
    "오페라", "발레", "무용", "댄스", "팝", "록", "힙합",
    "어쿠스틱", "오케스트라", "실내악", "합창",
    "가족", "데이트", "아이", "어린이", "커플",
}


def generate_tags_콘텐츠(item: dict) -> list:
    tags, seen = [], set()
    def add(tag):
        if tag and tag not in seen:
            seen.add(tag); tags.append(tag)
    if title := item.get("title"): add(title)
    if addr := item.get("addr"):
        for t in extract_district(addr): add(t)
    if cat := item.get("category"):
        if cat and len(cat) >= 2: add(cat)
    if place := item.get("place"):
        if place and len(place) >= 2: add(place)
    if llm := item.get("llm_text"):
        for kw in MOOD_KEYWORDS:
            if kw in llm: add(kw)
            if len(tags) >= 15: break
    return tags


def build_llm_text_콘텐츠(item: dict) -> str:
    lines = []
    if v := item.get("title"):   lines.append(f"- 공연명: {v}")
    if v := item.get("addr"):    lines.append(f"- 주소: {v}")
    if v := item.get("place"):   lines.append(f"- 장소: {v}")
    if v := item.get("category"):lines.append(f"- 카테고리: {v}")
    if v := item.get("period"):  lines.append(f"- 기간: {v}")
    if tags := item.get("tags"): lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("fee"):     lines.append(f"- 요금: {v}")
    intro = item.get("_original_llm_text", "")
    if intro: lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def process_콘텐츠():
    in_path = VK_ONLY_DIR / "visitkorea_only_콘텐츠.jsonl"
    out_path = OUT_DIR / "visitkorea_콘텐츠_template.json"
    if not in_path.exists():
        print(f"  [SKIP] {in_path.name} 없음"); return

    data = load_jsonl(in_path)
    print(f"\n  콘텐츠: {len(data)}건 입력")

    results = []
    for item in data:
        item["_original_llm_text"] = item.get("llm_text", "")
        item["mapy"] = to_float(item.get("mapy"))
        item["mapx"] = to_float(item.get("mapx"))
        for key in ("usetime", "restdate", "addr", "tel", "title", "parking", "place", "period", "fee"):
            if item.get(key): item[key] = normalize(item[key])
        item["tags"] = generate_tags_콘텐츠(item)
        item["llm_text"] = build_llm_text_콘텐츠(item)
        item.pop("_original_llm_text", None)
        item.pop("start_date", None)
        item.pop("end_date", None)
        cleaned = {k: v for k, v in item.items() if v is not None and v != [] and v != ""}
        results.append(cleaned)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print_stats(results, out_path)


# ══════════════════════════════════════════════════════════════
# 투어 처리
# ══════════════════════════════════════════════════════════════

TOUR_CATEGORY_RULES = [
    (["도자기", "공방", "공예", "만들기", "체험"], "체험 > 공방체험"),
    (["뷰티", "메이크업", "화장", "네일", "헤어", "스파"], "체험 > 뷰티체험"),
    (["한복", "전통"], "체험 > 전통체험"),
    (["포토", "사진", "스튜디오", "촬영"], "체험 > 포토체험"),
    (["요리", "쿠킹", "음식", "떡", "김치", "베이킹"], "체험 > 요리체험"),
    (["K-POP", "케이팝", "아이돌", "한류", "팬"], "한류 > K-POP"),
    (["드라마", "촬영지"], "한류 > 드라마"),
    (["쇼핑", "시장", "매장"], "쇼핑 > 투어"),
    (["야경", "전망", "타워", "루프탑"], "관광 > 야경투어"),
    (["역사", "궁궐", "문화재", "유적"], "관광 > 역사투어"),
    (["맛집", "미식", "푸드"], "관광 > 미식투어"),
]


def classify_tour_category(item: dict) -> str:
    text = f"{item.get('title', '')} {item.get('introduction', '')}".lower()
    for keywords, category in TOUR_CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in text:
                return category
    return "체험 > 투어"


def generate_tags_투어(item: dict) -> list:
    tags, seen = [], set()
    def add(tag):
        if tag and tag not in seen:
            seen.add(tag); tags.append(tag)
    if title := item.get("title"): add(title)
    if addr := item.get("addr"):
        for t in extract_district(addr): add(t)
    if cd := item.get("category_depth"):
        for p in [p.strip() for p in cd.split(">")]:
            if p and len(p) >= 2: add(p)
    intro = item.get("description", "") or ""
    if intro:
        for m in re.finditer(r"['\"'\u2018\u2019\u201c\u201d]([가-힣A-Za-z0-9\s]{2,15})['\"'\u2018\u2019\u201c\u201d]", intro):
            t = m.group(1).strip()
            if 2 <= len(t) <= 10: add(t)
        for kw in ["도자기", "한복", "메이크업", "K-POP", "한류", "뷰티", "공방", "공예", "전통", "포토", "사진", "요리", "쿠킹", "연예인", "스타"]:
            if kw in intro: add(kw)
    return tags


def build_llm_text_투어(item: dict) -> str:
    lines = []
    if v := item.get("title"):   lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):    lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"): lines.append(f"- 카테고리: {v}")
    if tags := item.get("tags"): lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("usetime"): lines.append(f"- 이용시간: {v}")
    if v := item.get("restdate"):lines.append(f"- 휴무일: {v}")
    intro = item.get("description") or item.get("summary") or ""
    if intro: lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def process_투어():
    in_path = VK_ONLY_DIR / "visitkorea_only_투어.jsonl"
    out_path = OUT_DIR / "visitkorea_투어_template.json"
    if not in_path.exists():
        print(f"  [SKIP] {in_path.name} 없음"); return

    data = load_jsonl(in_path)
    print(f"\n  투어: {len(data)}건 입력")

    before = len(data)
    data = [d for d in data if d.get("introduction", "").strip()]
    print(f"    introduction 없는 건 삭제: {before - len(data)}건 → {len(data)}건 남음")

    results = []
    for item in data:
        summary_text, description_text = "", ""
        intro = normalize(item.get("introduction", ""))
        if intro:
            sentences = re.split(r"(?<=[.!?])\s+", intro)
            summary_text = " ".join(sentences[:2]) if len(sentences) >= 2 else sentences[0]
            description_text = intro

        cleaned = {}
        cleaned["contentid"] = item.get("contentid")
        cleaned["title"] = normalize(item.get("title", ""))
        cleaned["contenttypeid"] = "투어"
        if img := item.get("image"): cleaned["image"] = img
        if v := normalize(item.get("usetime", "")): cleaned["usetime"] = v
        if v := normalize(item.get("restdate", "")): cleaned["restdate"] = v
        if v := normalize(item.get("addr", "")): cleaned["addr"] = v
        mapy, mapx = to_float(item.get("mapy")), to_float(item.get("mapx"))
        if mapy: cleaned["mapy"] = mapy
        if mapx: cleaned["mapx"] = mapx
        if v := normalize(item.get("tel", "")): cleaned["tel"] = v
        cleaned["category_depth"] = classify_tour_category(item)
        cleaned["summary"] = summary_text
        cleaned["description"] = description_text
        cleaned["tags"] = generate_tags_투어(cleaned)
        cleaned["llm_text"] = build_llm_text_투어(cleaned)
        cleaned = {k: v for k, v in cleaned.items() if v is not None and v != [] and v != ""}
        results.append(cleaned)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print_stats(results, out_path)

    cat_dist = Counter(r.get("category_depth", "?") for r in results)
    print("    category_depth 분포:")
    for cat, cnt in cat_dist.most_common():
        print(f"      {cat}: {cnt}건")


# ══════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("visitkorea 전처리 (관광지/음식점/숙박/콘텐츠/투어)")
    print("=" * 60)

    cat_map = load_category_map()
    print(f"  카테고리 맵: {len(cat_map)}개 코드")

    vs_titles = load_visitseoul_titles()
    print(f"  visitseoul 타이틀: {len(vs_titles)}건 (중복 비교용)")

    for cat in ["관광지", "음식점", "숙박"]:
        process_main_category(cat, vs_titles, cat_map)

    process_콘텐츠()
    process_투어()

    print("\n" + "=" * 60)
    print("완료")


if __name__ == "__main__":
    main()
