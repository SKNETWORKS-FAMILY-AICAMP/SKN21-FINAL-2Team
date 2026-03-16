"""
visitkorea_only 콘텐츠/투어 전처리 스크립트
============================================
입력: data/add(image,info)/visitkorea_only/visitkorea_only_{콘텐츠,투어}.jsonl
출력: data/preprocessed/visitkorea_{콘텐츠,투어}_template.json

콘텐츠:
    - 전처리 불필요 (이미 정제된 상태)
    - tags 생성: 공연 분위기 태그 포함
    - llm_text: template 형식으로 교체

투어:
    - introduction 없는 건 삭제
    - introduction → summary + description 분리
    - category_depth 규칙 분류
    - tags + llm_text template 생성
    - visitseoul 투어 스키마에 맞춤
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
VK_ONLY_DIR = DATA_DIR / "add(image,info)" / "visitkorea_only"
OUT_DIR = DATA_DIR / "preprocessed"
OUT_DIR.mkdir(exist_ok=True)


# ── 공용 유틸 (preprocess_visitkorea.py에서 재사용) ─────────
def strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    return text


def normalize(text: str) -> str:
    if not text:
        return ""
    text = strip_html(text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def to_float(val):
    try:
        f = float(val)
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


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


def load_jsonl(path: Path) -> list[dict]:
    data = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def print_stats(results: list[dict], out_path: Path):
    has_tags = sum(1 for r in results if r.get("tags"))
    avg_tags = sum(len(r.get("tags", [])) for r in results) / max(len(results), 1)
    has_llm = sum(1 for r in results if r.get("llm_text"))
    print(f"    출력: {len(results)}건 → {out_path.name}")
    print(f"    tags: {has_tags}건 (평균 {avg_tags:.1f}개)")
    print(f"    llm_text: {has_llm}건")

    print(f"\n    === 샘플 ===")
    for r in results[:2]:
        print(f"    [{r.get('title')}]")
        print(f"      tags: {r.get('tags', [])}")
        print(f"      llm_text: {r.get('llm_text', '')[:250]}...")
        print()


# ══════════════════════════════════════════════════════════════
# 콘텐츠 처리
# ══════════════════════════════════════════════════════════════

# 분위기/감성 키워드 사전 — llm_text(산문체)에서 매칭
MOOD_KEYWORDS = {
    # 감정/분위기
    "감동", "힐링", "웅장", "아름다운", "로맨틱", "신나는", "따뜻한",
    "잔잔한", "서정적", "우아한", "화려한", "몽환적", "역동적", "경쾌한",
    "서정", "낭만", "감성", "고요한", "편안한", "유쾌한", "코믹",
    "스릴", "긴장감", "비장", "애절", "섬세한", "깊이 있는",
    # 장르/스타일
    "클래식", "현대적", "전통", "재즈", "국악", "뮤지컬", "연극",
    "오페라", "발레", "무용", "댄스", "팝", "록", "힙합",
    "어쿠스틱", "오케스트라", "실내악", "합창",
    # 대상/상황
    "가족", "데이트", "아이", "어린이", "커플",
}


def extract_mood_tags(text: str, max_count: int = 5) -> list:
    """산문체 텍스트에서 분위기/감성 키워드 추출"""
    if not text:
        return []
    found = []
    seen = set()
    for kw in MOOD_KEYWORDS:
        if kw in text and kw not in seen:
            seen.add(kw)
            found.append(kw)
    return found[:max_count]


def generate_tags_콘텐츠(item: dict) -> list:
    """콘텐츠용 tags 생성"""
    tags = []
    seen = set()

    def add(tag):
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)

    # 1. title (공연명)
    if title := item.get("title"):
        add(title)

    # 2. addr → 구/동
    if addr := item.get("addr"):
        for t in extract_district(addr):
            add(t)

    # 3. category (공연, 전시, 축제 등)
    if cat := item.get("category"):
        if cat and len(cat) >= 2:
            add(cat)

    # 4. place (공연장소)
    if place := item.get("place"):
        if place and len(place) >= 2:
            add(place)

    # 5. 분위기 태그 — 기존 llm_text(산문체)에서 추출
    if llm := item.get("llm_text"):
        for t in extract_mood_tags(llm):
            add(t)

    return tags


def build_llm_text_콘텐츠(item: dict) -> str:
    """콘텐츠 llm_text: 구조화된 template"""
    lines = []
    if v := item.get("title"):
        lines.append(f"- 공연명: {v}")
    if v := item.get("addr"):
        lines.append(f"- 주소: {v}")
    if v := item.get("place"):
        lines.append(f"- 장소: {v}")
    if v := item.get("category"):
        lines.append(f"- 카테고리: {v}")
    if v := item.get("period"):
        lines.append(f"- 기간: {v}")
    if tags := item.get("tags"):
        lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if v := item.get("fee"):
        lines.append(f"- 요금: {v}")
    # 소개: 기존 산문체 llm_text에서 300자
    intro = item.get("_original_llm_text", "")
    if intro:
        lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def process_콘텐츠():
    in_path = VK_ONLY_DIR / "visitkorea_only_콘텐츠.jsonl"
    out_path = OUT_DIR / "visitkorea_콘텐츠_template.json"

    if not in_path.exists():
        print(f"  [SKIP] {in_path.name} 없음")
        return

    data = load_jsonl(in_path)
    print(f"\n  콘텐츠: {len(data)}건 입력")

    results = []
    for item in data:
        # 기존 산문체 llm_text를 소개용으로 보관
        item["_original_llm_text"] = item.get("llm_text", "")

        # 좌표 변환
        item["mapy"] = to_float(item.get("mapy"))
        item["mapx"] = to_float(item.get("mapx"))

        # 텍스트 정규화
        for key in ("usetime", "restdate", "addr", "tel", "title",
                     "parking", "place", "period", "fee"):
            if item.get(key):
                item[key] = normalize(item[key])

        # tags 생성 (분위기 태그 포함)
        item["tags"] = generate_tags_콘텐츠(item)

        # llm_text template 생성
        item["llm_text"] = build_llm_text_콘텐츠(item)

        # 임시 필드 제거
        item.pop("_original_llm_text", None)
        # start_date, end_date는 period에 포함되어 있으므로 제거
        item.pop("start_date", None)
        item.pop("end_date", None)

        # null/빈 필드 제거
        cleaned = {k: v for k, v in item.items()
                   if v is not None and v != [] and v != ""}
        results.append(cleaned)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print_stats(results, out_path)


# ══════════════════════════════════════════════════════════════
# 투어 처리
# ══════════════════════════════════════════════════════════════

# 투어 category_depth 규칙 분류
TOUR_CATEGORY_RULES = [
    # (키워드 리스트, category_depth)
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
    """introduction + title에서 규칙 기반 category_depth 분류"""
    text = f"{item.get('title', '')} {item.get('introduction', '')}".lower()
    for keywords, category in TOUR_CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in text:
                return category
    return "체험 > 투어"


def split_introduction(intro: str) -> tuple[str, str]:
    """introduction → (summary, description) 분리
    summary: 첫 1~2문장 (마침표 기준)
    description: 전체
    """
    if not intro:
        return "", ""
    intro = normalize(intro)
    # 마침표로 문장 분리
    sentences = re.split(r"(?<=[.!?])\s+", intro)
    if len(sentences) >= 2:
        summary = " ".join(sentences[:2])
    else:
        summary = sentences[0] if sentences else intro[:100]
    return summary, intro


def generate_tags_투어(item: dict) -> list:
    """투어용 tags 생성"""
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
        parts = [p.strip() for p in cd.split(">")]
        for p in parts:
            p = p.strip()
            if p and len(p) >= 2:
                add(p)

    # 4. introduction에서 키워드 추출
    intro = item.get("description", "") or ""
    if intro:
        # 따옴표 안 내용
        for m in re.finditer(r"['\"'\u2018\u2019\u201c\u201d]([가-힣A-Za-z0-9\s]{2,15})['\"'\u2018\u2019\u201c\u201d]", intro):
            t = m.group(1).strip()
            if 2 <= len(t) <= 10:
                add(t)
        # "~로 유명", "~(으)로 알려진"
        for m in re.finditer(r"([가-힣]{2,6})(?:으?로\s*(?:유명|알려진|손꼽히는))", intro):
            add(m.group(1))
        # 체험/투어 관련 키워드
        for kw in ["도자기", "한복", "메이크업", "K-POP", "한류",
                    "뷰티", "공방", "공예", "전통", "포토", "사진",
                    "요리", "쿠킹", "연예인", "스타"]:
            if kw in intro:
                add(kw)

    return tags


def build_llm_text_투어(item: dict) -> str:
    """투어 llm_text: template 형식 (visitseoul 투어와 동일 형태)"""
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
    intro = item.get("description") or item.get("summary") or ""
    if intro:
        lines.append(f"- 소개: {intro[:300]}")
    return "\n".join(lines)


def process_투어():
    in_path = VK_ONLY_DIR / "visitkorea_only_투어.jsonl"
    out_path = OUT_DIR / "visitkorea_투어_template.json"

    if not in_path.exists():
        print(f"  [SKIP] {in_path.name} 없음")
        return

    data = load_jsonl(in_path)
    print(f"\n  투어: {len(data)}건 입력")

    # introduction 없는 건 삭제
    before = len(data)
    data = [d for d in data if d.get("introduction", "").strip()]
    removed = before - len(data)
    print(f"    introduction 없는 건 삭제: {removed}건 → {len(data)}건 남음")

    # 좌표 현황
    no_coord = sum(1 for d in data if not to_float(d.get("mapy")) or not to_float(d.get("mapx")))
    print(f"    좌표 없는 건수: {no_coord}건 (별도 geocoding 필요)")

    results = []
    for item in data:
        # 1. introduction → summary + description
        summary, description = split_introduction(item.get("introduction", ""))

        # 2. category_depth 규칙 분류
        category_depth = classify_tour_category(item)

        # 3. 새 아이템 구성 (visitseoul 투어 스키마에 맞춤)
        cleaned = {}
        cleaned["contentid"] = item.get("contentid")
        cleaned["title"] = normalize(item.get("title", ""))
        cleaned["contenttypeid"] = "투어"
        if img := item.get("image"):
            cleaned["image"] = img
        if v := normalize(item.get("usetime", "")):
            cleaned["usetime"] = v
        if v := normalize(item.get("restdate", "")):
            cleaned["restdate"] = v
        if v := normalize(item.get("addr", "")):
            cleaned["addr"] = v

        mapy = to_float(item.get("mapy"))
        mapx = to_float(item.get("mapx"))
        if mapy:
            cleaned["mapy"] = mapy
        if mapx:
            cleaned["mapx"] = mapx

        if v := normalize(item.get("tel", "")):
            cleaned["tel"] = v

        cleaned["category_depth"] = category_depth
        cleaned["summary"] = summary
        cleaned["description"] = description

        # 4. tags 생성
        cleaned["tags"] = generate_tags_투어(cleaned)

        # 5. llm_text 생성
        cleaned["llm_text"] = build_llm_text_투어(cleaned)

        # null/빈 필드 제거
        cleaned = {k: v for k, v in cleaned.items()
                   if v is not None and v != [] and v != ""}
        results.append(cleaned)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print_stats(results, out_path)

    # category_depth 분포
    from collections import Counter
    cat_dist = Counter(r.get("category_depth", "?") for r in results)
    print("    category_depth 분포:")
    for cat, cnt in cat_dist.most_common():
        print(f"      {cat}: {cnt}건")


# ── 메인 ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("visitkorea_only 콘텐츠/투어 전처리")
    print("=" * 60)

    process_콘텐츠()
    process_투어()

    print("\n" + "=" * 60)
    print("완료")


if __name__ == "__main__":
    main()
