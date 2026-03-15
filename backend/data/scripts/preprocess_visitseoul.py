"""
Visit Seoul 데이터 전처리 스크립트
=====================================
입력: data/visitseoul_{카테고리}.json
출력: data/preprocessed/visitseoul_{카테고리}.json

처리 내용:
    1. 불필요한 필드 제거 (parking, source, multi_lang_list, contenttypeid_code)
    2. null 필드 제거
    3. 텍스트 정규화 (공백/개행 정리, HTML 제거)
    4. tags 정제 (개행 제거, 빈 태그 제거)
    5. mapy/mapx float 보장
    6. category_depth 공백 정규화
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = DATA_DIR / "preprocessed"
OUT_DIR.mkdir(exist_ok=True)

CATEGORIES = ["관광지", "음식점", "숙박", "투어"]

# 제거할 필드
DROP_FIELDS = {"parking", "source", "multi_lang_list", "contenttypeid_code", "updated_at"}


# ── 텍스트 정규화 ──────────────────────────────────────────
def strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    # CSS 블록 패턴 제거 (태그 없이 텍스트로 삽입된 경우)
    # {…} 포함 블록 제거
    text = re.sub(r"[^{}]+\{[^}]*\}", "", text)
    # 남은 CSS 선택자 잔여물 제거 (한글 등장 전까지)
    text = re.sub(r"^[^가-힣\w\"\']+", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def normalize(text: str) -> str:
    """공백·개행 정규화"""
    text = strip_html(text)
    text = re.sub(r"\r\n|\r", "\n", text)       # CR 통일
    text = re.sub(r"[ \t]+", " ", text)          # 수평 공백 압축
    text = re.sub(r"\n{3,}", "\n\n", text)       # 3개 이상 개행 → 2개
    return text.strip()


def normalize_category_depth(text: str) -> str:
    """'문화관광  > 랜드마크관광' → '문화관광 > 랜드마크관광'"""
    parts = [p.strip() for p in text.split(">")]
    return " > ".join(p for p in parts if p)


def clean_tags(tags) -> list:
    if not isinstance(tags, list):
        return []
    result = []
    for tag in tags:
        tag = re.sub(r"\s+", "", str(tag))   # 공백·개행 모두 제거
        if tag:
            result.append(tag)
    return result


def to_float(val):
    try:
        f = float(val)
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


# ── 항목 변환 ─────────────────────────────────────────────
def transform(item: dict) -> dict:
    result = {}

    for key, val in item.items():
        # 제거 필드 스킵
        if key in DROP_FIELDS:
            continue

        # 타입별 처리
        if key in ("mapy", "mapx"):
            result[key] = to_float(val)
        elif key == "tags":
            result[key] = clean_tags(val)
        elif key == "category_depth" and isinstance(val, str):
            result[key] = normalize_category_depth(val) or None
        elif key in ("description", "summary"):
            result[key] = normalize(val) if val else None
        elif key in ("usetime", "restdate", "fee", "addr", "tel", "subway_info", "website", "title"):
            result[key] = normalize(val) if val else None
        else:
            result[key] = val

    # null 필드 제거
    result = {k: v for k, v in result.items() if v is not None and v != [] and v != ""}

    return result


# ── 메인 ──────────────────────────────────────────────────
def process(category: str):
    in_path = DATA_DIR / f"visitseoul_{category}.json"
    if not in_path.exists():
        print(f"  파일 없음: {in_path.name}")
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    results = [transform(item) for item in data]

    out_path = OUT_DIR / f"visitseoul_{category}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  {category}: {len(results)}건 → {out_path.relative_to(DATA_DIR.parent)}")


def main():
    print("=" * 50)
    print("Visit Seoul 전처리")
    print("=" * 50)
    for cat in CATEGORIES:
        process(cat)
    print("완료")
    print("=" * 50)


if __name__ == "__main__":
    main()
