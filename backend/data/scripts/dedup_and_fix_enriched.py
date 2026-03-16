"""
0-A단계: 유사 중복 제거 + category_depth 코드→한글 수정
=======================================================
- visitseoul 전체 타이틀(1,876건)과 visitkorea enriched 전역 비교
- ratio >= 0.9: 자동 제거
- 0.85 <= ratio < 0.9: 수동 확인 목록에서 제거 대상만 제거
- 관광지 category_depth: cat2/cat3 코드→한글 변환 (tourapi_category_map.json)
- enriched 파일 덮어쓰기
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
VK_DIR = DATA_DIR / "add(image,info)" / "visitkorea_only"
PRE_DIR = DATA_DIR / "preprocessed"

CATEGORIES = ["관광지", "음식점", "숙박"]

# ── 수동 확인 후 제거 확정된 타이틀 (visitkorea 쪽) ──
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


def load_visitseoul_titles() -> set:
    """visitseoul 전체 타이틀 로드 (카테고리 무관)"""
    titles = set()
    for cat in ["관광지", "음식점", "숙박", "투어"]:
        path = PRE_DIR / f"visitseoul_{cat}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                t = item.get("title", "").strip()
                if t:
                    titles.add(t)
    return titles


def find_duplicates(vk_data: list, vs_titles: set, threshold: float = 0.9) -> set:
    """ratio >= threshold 인 visitkorea 타이틀 인덱스 반환"""
    remove_indices = set()
    vs_list = list(vs_titles)

    for idx, item in enumerate(vk_data):
        vk_title = item.get("title", "").strip()
        if not vk_title:
            continue

        # 수동 제거 목록 체크
        if vk_title in MANUAL_REMOVE_TITLES:
            remove_indices.add(idx)
            continue

        # 유사도 체크 (ratio >= threshold)
        for vs_title in vs_list:
            ratio = SequenceMatcher(None, vk_title, vs_title).ratio()
            if ratio >= threshold:
                remove_indices.add(idx)
                break

    return remove_indices


def fix_category_depth(data: list, cat_map: dict) -> int:
    """category_depth의 코드를 한글로 변환. 변환 건수 반환."""
    code_pattern = re.compile(r"[A-Z]\d{2}")
    fixed = 0

    for item in data:
        cd = item.get("category_depth")
        if not cd or not code_pattern.search(cd):
            continue

        parts = [p.strip() for p in cd.split(">")]
        new_parts = []
        for p in parts:
            if p in cat_map:
                new_parts.append(cat_map[p])
            else:
                new_parts.append(p)
        new_cd = " > ".join(new_parts)
        if new_cd != cd:
            item["category_depth"] = new_cd
            fixed += 1

    return fixed


def main():
    print("=" * 60)
    print("0-A: 유사 중복 제거 + category_depth 코드→한글")
    print("=" * 60)

    # visitseoul 타이틀 로드
    vs_titles = load_visitseoul_titles()
    print(f"visitseoul 타이틀: {len(vs_titles)}건")

    # category map 로드
    cat_map_path = VK_DIR / "tourapi_category_map.json"
    with open(cat_map_path, encoding="utf-8") as f:
        cat_map = json.load(f)
    print(f"카테고리 코드 매핑: {len(cat_map)}건")

    total_removed = 0
    total_fixed = 0

    for cat in CATEGORIES:
        enriched_path = VK_DIR / f"visitkorea_only_{cat}_enriched.json"
        if not enriched_path.exists():
            print(f"\n  [{cat}] 파일 없음: {enriched_path.name}")
            continue

        with open(enriched_path, encoding="utf-8") as f:
            data = json.load(f)
        original_count = len(data)

        # 중복 제거
        remove_indices = find_duplicates(data, vs_titles, threshold=0.9)
        removed_titles = [data[i].get("title", "") for i in sorted(remove_indices)]

        if remove_indices:
            data = [item for idx, item in enumerate(data) if idx not in remove_indices]

        # category_depth 코드→한글 (관광지만 해당)
        fixed = fix_category_depth(data, cat_map)

        # 저장
        with open(enriched_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n  [{cat}] {original_count}건 → {len(data)}건 (제거: {len(remove_indices)}건)")
        if removed_titles:
            for t in removed_titles[:5]:
                print(f"    - {t}")
            if len(removed_titles) > 5:
                print(f"    ... 외 {len(removed_titles) - 5}건")

        if fixed:
            print(f"  category_depth 코드→한글 변환: {fixed}건")

        total_removed += len(remove_indices)
        total_fixed += fixed

    print(f"\n{'=' * 60}")
    print(f"총 제거: {total_removed}건, category_depth 변환: {total_fixed}건")
    print("=" * 60)


if __name__ == "__main__":
    main()
