"""
visitkorea 전처리 스크립트
===========================
입력: data/add(image,info)/visitkorea/visitkorea_{카테고리}.json
출력: data/preprocessed/visitkorea_{카테고리}.json

처리:
    1. detail_intro 평탄화 + 필드 병합
    2. 텍스트 정규화
    3. 유사 중복 제거 (visitseoul 대비)
    4. category_depth 코드→한글 변환
    5. tags 생성 (규칙 기반, LLM 없이)
    6. llm_text 생성 (template 방식)
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
VK_DIR = DATA_DIR / "add(image,info)" / "visitkorea"
VK_ONLY_DIR = DATA_DIR / "add(image,info)" / "visitkorea_only"
OUT_DIR = DATA_DIR / "preprocessed"
OUT_DIR.mkdir(exist_ok=True)

CATEGORIES = ["관광지", "음식점", "숙박"]


# ── 텍스트 정규화 (preprocess_visitseoul.py 동일) ──────────
def strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^{}]+\{[^}]*\}", "", text)
    text = re.sub(r"^[^가-힣\w\"\']+", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def normalize(text: str) -> str:
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


# ── category_depth 코드→한글 변환 ─────────────────────────
def load_category_map() -> dict:
    map_file = VK_ONLY_DIR / "tourapi_category_map.json"
    if map_file.exists():
        with open(map_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def fix_category_depth(cd: str, cat_map: dict) -> str:
    """category_depth에서 코드(A0101 등)를 한글로 변환"""
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


# ── 유사 중복 제거 ────────────────────────────────────────
# 수동 확인 후 제거 확정된 visitkorea 타이틀
MANUAL_REMOVE_TITLES = {
    "국립4·19민주묘지",
    "북촌전통공예체험관",
    "삼해소주",
    "서울어린이대공원",
    "홍지문 및 탕춘대성",
    "서울아트센터 도암홀·도암갤러리",
    "KT&G 상상마당 홍대",
    "서울 서초 글램핑 청계산장",
    "응봉산 암벽등반공원",
    "라 쿠치나",
    "먼데이투선데이",
    "미 피아체",
    "남대문 갈치조림골목",
}


def load_visitseoul_titles() -> list[str]:
    """visitseoul 전처리 파일에서 전체 타이틀 로드 (전역 비교)"""
    titles = []
    for cat in ["관광지", "음식점", "숙박", "투어"]:
        f = OUT_DIR / f"visitseoul_{cat}.json"
        if f.exists():
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            titles.extend(d.get("title", "") for d in data)
    return titles


def find_duplicates(vk_items: list[dict], vs_titles: list[str]) -> set[str]:
    """visitseoul과 유사 중복인 visitkorea 타이틀 찾기"""
    remove_titles = set()

    for item in vk_items:
        vk_title = item.get("title", "").strip()

        # 수동 제거 목록
        if vk_title in MANUAL_REMOVE_TITLES:
            remove_titles.add(vk_title)
            continue

        # ratio >= 0.9 자동 제거
        for vs_title in vs_titles:
            ratio = SequenceMatcher(None, vk_title, vs_title).ratio()
            if ratio >= 0.9:
                remove_titles.add(vk_title)
                break

    return remove_titles


# ── detail_intro 평탄화 ───────────────────────────────────
def flatten_intro_관광지(item: dict) -> dict:
    """관광지: detail_intro에서 필요한 필드 추출 → 최상위 병합"""
    di = item.pop("detail_intro", None) or {}

    # tel 보완
    if not item.get("tel") and di.get("infocenter"):
        item["tel"] = di["infocenter"]

    # usetime/restdate 보완
    if not item.get("usetime") and di.get("usetime"):
        item["usetime"] = di["usetime"]
    if not item.get("restdate") and di.get("restdate"):
        item["restdate"] = di["restdate"]

    # parking 새 필드
    if di.get("parking"):
        item["parking"] = di["parking"]

    return item


def flatten_intro_음식점(item: dict) -> dict:
    """음식점: detail_intro에서 필요한 필드 추출 → 최상위 병합"""
    di = item.pop("detail_intro", None) or {}

    # tel 보완
    if not item.get("tel") and di.get("infocenterfood"):
        item["tel"] = di["infocenterfood"]

    # menu 보완: firstmenu + treatmenu
    if not item.get("menu"):
        parts = []
        if di.get("firstmenu"):
            parts.append(di["firstmenu"])
        if di.get("treatmenu"):
            parts.append(di["treatmenu"])
        if parts:
            item["menu"] = " / ".join(parts)

    # firstmenu 별도 보관 (tags, llm_text용)
    if di.get("firstmenu"):
        item["firstmenu"] = di["firstmenu"]

    # usetime 보완
    if not item.get("usetime") and di.get("opentimefood"):
        item["usetime"] = di["opentimefood"]

    # restdate 추가
    if di.get("restdatefood"):
        item["restdate"] = di["restdatefood"]

    # parking 새 필드
    if di.get("parkingfood"):
        item["parking"] = di["parkingfood"]

    # packing (llm_text용으로만 보관)
    if di.get("packing"):
        item["packing"] = di["packing"]

    # restaurant_type 보완: category_depth 3번째 레벨
    if not item.get("restaurant_type"):
        cd = item.get("category_depth", "") or ""
        parts = [p.strip() for p in cd.split(">")]
        if len(parts) >= 3 and parts[2].strip():
            item["restaurant_type"] = parts[2].strip()

    return item


def flatten_intro_숙박(item: dict) -> dict:
    """숙박: detail_intro에서 필요한 필드 추출 → 최상위 병합"""
    di = item.pop("detail_intro", None) or {}

    # tel 보완
    if not item.get("tel") and di.get("infocenterlodging"):
        item["tel"] = di["infocenterlodging"]

    # checkin/checkout
    if di.get("checkintime"):
        item["checkintime"] = di["checkintime"]
    if di.get("checkouttime"):
        item["checkouttime"] = di["checkouttime"]

    # usetime 보완 (checkin~checkout)
    if not item.get("usetime"):
        ci = di.get("checkintime", "")
        co = di.get("checkouttime", "")
        if ci and co:
            item["usetime"] = f"체크인 {ci} / 체크아웃 {co}"

    # parking
    if di.get("parkinglodging"):
        item["parking"] = di["parkinglodging"]

    # fee 보완 (subfacility, foodplace 등 부대시설)
    subfacility = di.get("subfacility", "")
    foodplace = di.get("foodplace", "")
    facilities = [s for s in [subfacility, foodplace] if s]
    if facilities:
        item["subfacility"] = ", ".join(facilities)

    # room_type: category_depth 3번째 레벨
    if not item.get("room_type"):
        cd = item.get("category_depth", "") or ""
        parts = [p.strip() for p in cd.split(">")]
        if len(parts) >= 3 and parts[2].strip():
            item["room_type"] = parts[2].strip()

    # reservation
    if di.get("reservationlodging"):
        item["reservation"] = di["reservationlodging"]

    # accomcount
    if di.get("accomcountlodging"):
        item["accomcount"] = di["accomcountlodging"]

    return item


FLATTEN_FN = {
    "관광지": flatten_intro_관광지,
    "음식점": flatten_intro_음식점,
    "숙박": flatten_intro_숙박,
}


# ── 텍스트 정규화 (transform) ─────────────────────────────
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
            # " / " → ", " (visitseoul 형식에 맞춤)
            val = normalize(val)
            val = re.sub(r"\s*/\s*", ", ", val)
            result[key] = val
        elif key in ("usetime", "restdate", "fee", "addr", "tel",
                      "subway_info", "website", "title",
                      "parking", "packing", "firstmenu", "restaurant_type",
                      "checkintime", "checkouttime", "subfacility",
                      "room_type", "reservation", "accomcount"):
            result[key] = normalize(val) if val else None
        elif key == "tags":
            # 기존 tags는 비어있으므로 무시 (새로 생성)
            continue
        else:
            result[key] = val

    # null 필드 제거
    result = {k: v for k, v in result.items() if v is not None and v != [] and v != ""}
    return result


# ── tags 생성 (규칙 기반) ─────────────────────────────────
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


CAT_DEPTH_SKIP = {"자연", "음식", "문화관광", "레포츠", "쇼핑", "인문"}

def extract_category_tags(category_depth: str) -> list:
    """category_depth에서 태그 추출 (너무 일반적인 1레벨은 제외)"""
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
    """summary/description에서 의미있는 키워드 추출
    - 괄호 안 내용 (보통 별칭)
    - 따옴표 안 내용
    - "~로 유명한" 앞의 명사
    - "대표 ~", "명물" 패턴
    """
    if not text:
        return []
    tags = []
    seen = set()

    def add(t):
        t = t.strip()
        # 조사/어미로 끝나는 단어 제거
        if re.search(r"(은|는|이|가|을|를|의|에|로|와|과|도|에서|으로|이다|하는|있는|들은|메뉴는|맛있기|곳으로|위치한|불리는|시작한|한다고|된다고)$", t):
            return
        if t and 2 <= len(t) <= 10 and t not in seen:
            seen.add(t)
            tags.append(t)

    # 괄호 안 내용 (별칭 등)
    for m in re.finditer(r"['\u2018\u2019\u201c\u201d]([가-힣A-Za-z0-9\s]{2,15})['\u2018\u2019\u201c\u201d]", text):
        add(m.group(1).strip())
    for m in re.finditer(r"[（(]([가-힣]{2,10})[）)]", text):
        add(m.group(1).strip())

    # "~로 유명한", "~(으)로 알려진" 앞의 명사
    for m in re.finditer(r"([가-힣]{2,6})(?:으?로\s*(?:유명|알려진|잘\s*알려진|손꼽히는|불리는))", text):
        add(m.group(1))

    # "대표 메뉴는 ~", "대표 ~"
    for m in re.finditer(r"대표\s*(?:메뉴는?\s*)?([가-힣]{2,6})", text):
        add(m.group(1))

    # "명물" 앞뒤
    for m in re.finditer(r"([가-힣]{2,6})\s*명물", text):
        add(m.group(1))

    # "~ 맛집", "~ 전문점"
    for m in re.finditer(r"([가-힣]{2,6})\s*(?:맛집|전문점|전문|명소)", text):
        add(m.group(1))

    return tags[:max_count]


def generate_tags(item: dict) -> list:
    """규칙 기반 tags 생성"""
    tags = []
    seen = set()

    def add(tag):
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)

    # 1. title
    if title := item.get("title"):
        add(title)

    # 2. addr → 구/동
    if addr := item.get("addr"):
        for t in extract_district(addr):
            add(t)

    # 3. category_depth
    if cd := item.get("category_depth"):
        for t in extract_category_tags(cd):
            add(t)

    # 4. restaurant_type / firstmenu (음식점)
    if rt := item.get("restaurant_type"):
        add(rt)
    if fm := item.get("firstmenu"):
        add(fm)

    # 5. summary/description에서 키워드 추출
    text = item.get("summary", "") or ""
    desc = item.get("description", "") or ""
    combined = f"{text} {desc}"
    if combined.strip():
        for t in extract_from_text(combined, max_count=5):
            add(t)

    return tags


# ── llm_text 생성 (template) ─────────────────────────────
def build_llm_text_관광지(item: dict) -> str:
    lines = []
    if v := item.get("title"):
        lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):
        lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"):
        lines.append(f"- 카테고리: {v}")
    if tags := item.get("tags"):
        lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("usetime"):
        lines.append(f"- 이용시간: {v}")
    if v := item.get("restdate"):
        lines.append(f"- 휴무일: {v}")
    if v := item.get("fee"):
        lines.append(f"- 입장료: {v}")
    if v := item.get("parking"):
        lines.append(f"- 주차: {v}")
    intro = item.get("description") or item.get("summary") or ""
    if intro:
        lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def build_llm_text_음식점(item: dict) -> str:
    lines = []
    if v := item.get("title"):
        lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):
        lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"):
        lines.append(f"- 카테고리: {v}")
    if tags := item.get("tags"):
        lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("firstmenu"):
        lines.append(f"- 대표메뉴: {v}")
    if v := item.get("menu"):
        lines.append(f"- 메뉴: {v}")
    if v := item.get("usetime"):
        lines.append(f"- 영업시간: {v}")
    if v := item.get("restdate"):
        lines.append(f"- 휴무일: {v}")
    if v := item.get("packing"):
        lines.append(f"- 포장: {v}")
    if v := item.get("parking"):
        lines.append(f"- 주차: {v}")
    intro = item.get("description") or item.get("summary") or ""
    if intro:
        lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def build_llm_text_숙박(item: dict) -> str:
    lines = []
    if v := item.get("title"):
        lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):
        lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"):
        lines.append(f"- 카테고리: {v}")
    if tags := item.get("tags"):
        lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("room_type"):
        lines.append(f"- 객실유형: {v}")
    if v := item.get("usetime"):
        lines.append(f"- 체크인/아웃: {v}")
    if v := item.get("fee"):
        lines.append(f"- 요금: {v}")
    if v := item.get("parking"):
        lines.append(f"- 주차: {v}")
    if v := item.get("subfacility"):
        lines.append(f"- 부대시설: {v}")
    if v := item.get("accomcount"):
        lines.append(f"- 수용인원: {v}")
    if v := item.get("reservation"):
        lines.append(f"- 예약: {v}")
    intro = item.get("description") or item.get("summary") or ""
    if intro:
        lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


LLM_TEXT_FN = {
    "관광지": build_llm_text_관광지,
    "음식점": build_llm_text_음식점,
    "숙박": build_llm_text_숙박,
}


# ── detail_intro 로드 (있으면 병합) ──────────────────────
def load_intro_map(cat_name: str) -> dict:
    """intro_raw.jsonl에서 contentid → detail_intro 매핑 로드"""
    intro_file = VK_ONLY_DIR / f"visitkorea_only_{cat_name}_intro_raw.jsonl"
    intro_map = {}
    if intro_file.exists():
        with open(intro_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    if d.get("detail_intro"):
                        intro_map[str(d["contentid"])] = d["detail_intro"]
                except Exception:
                    continue
    return intro_map


# ── 메인 처리 ─────────────────────────────────────────────
def process(category: str, vs_titles: list[str], cat_map: dict):
    # 모든 카테고리: enriched 전체 사용 + intro_raw 병합
    in_path = VK_ONLY_DIR / f"visitkorea_only_{category}_enriched.json"
    out_path = OUT_DIR / f"visitkorea_{category}.json"

    if not in_path.exists():
        print(f"  [SKIP] {in_path.name} 없음")
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    # intro_raw에서 detail_intro 병합
    intro_map = load_intro_map(category)
    for item in data:
        cid = str(item.get("contentid", ""))
        if cid in intro_map and "detail_intro" not in item:
            item["detail_intro"] = intro_map[cid]
    print(f"  detail_intro 병합: {len(intro_map)}건")

    # contentid 중복 제거 (같은 contentid가 2건 이상이면 첫 번째만 유지)
    seen_cids = set()
    deduped = []
    for item in data:
        cid = str(item.get("contentid", ""))
        if cid in seen_cids:
            continue
        seen_cids.add(cid)
        deduped.append(item)
    if len(deduped) < len(data):
        print(f"  contentid 중복 제거: {len(data)} → {len(deduped)}건")
    data = deduped

    print(f"\n  {category}: {len(data)}건 입력")

    # 0. 유사 중복 제거
    dup_titles = find_duplicates(data, vs_titles)
    data = [d for d in data if d.get("title", "").strip() not in dup_titles]
    print(f"    중복 제거: {len(dup_titles)}건 → {len(data)}건 남음")

    flatten_fn = FLATTEN_FN.get(category, lambda x: x)
    llm_fn = LLM_TEXT_FN.get(category, build_llm_text_관광지)

    results = []
    for item in data:
        # 1. category_depth 코드→한글
        if cd := item.get("category_depth"):
            item["category_depth"] = fix_category_depth(cd, cat_map)

        # 2. detail_intro 평탄화
        item = flatten_fn(item)

        # 3. 텍스트 정규화
        cleaned = transform(item)

        # 4. tags 생성
        cleaned["tags"] = generate_tags(cleaned)

        # 5. llm_text 생성
        cleaned["llm_text"] = llm_fn(cleaned)

        # 6. llm_text에만 쓰고 최종 스키마에서 제거할 필드
        cleaned.pop("packing", None)
        cleaned.pop("firstmenu", None)
        cleaned.pop("checkintime", None)
        cleaned.pop("checkouttime", None)
        cleaned.pop("subfacility", None)
        cleaned.pop("reservation", None)
        cleaned.pop("accomcount", None)

        results.append(cleaned)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 통계
    has_tags = sum(1 for r in results if r.get("tags"))
    avg_tags = sum(len(r.get("tags", [])) for r in results) / max(len(results), 1)
    has_llm = sum(1 for r in results if r.get("llm_text"))
    print(f"    출력: {len(results)}건 → {out_path.name}")
    print(f"    tags: {has_tags}건 (평균 {avg_tags:.1f}개)")
    print(f"    llm_text: {has_llm}건")

    # 샘플 출력
    print(f"\n    === 샘플 ===")
    for r in results[:2]:
        print(f"    [{r.get('title')}]")
        print(f"      tags: {r.get('tags', [])}")
        print(f"      llm_text: {r.get('llm_text', '')[:200]}...")
        print()


def main():
    print("=" * 60)
    print("visitkorea 전처리")
    print("=" * 60)

    cat_map = load_category_map()
    print(f"  카테고리 맵: {len(cat_map)}개 코드")

    vs_titles = load_visitseoul_titles()
    print(f"  visitseoul 타이틀: {len(vs_titles)}건 (중복 비교용)")

    for cat in CATEGORIES:
        process(cat, vs_titles, cat_map)

    print("\n" + "=" * 60)
    print("완료")


if __name__ == "__main__":
    main()
