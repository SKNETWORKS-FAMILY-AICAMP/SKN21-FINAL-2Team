"""전처리된 데이터를 최종 카테고리별로 병합

관광지 = tourapi_관광지 + tourapi_문화시설 + tourapi_레포츠
         + visitseoul_관광지
숙박   = tourapi_숙박 + visitseoul_숙박
음식점 = tourapi_음식점 + visitseoul_음식점
콘텐츠 = seoul_culture_문화행사 + popply_팝업스토어
         + visitseoul_축제공연행사
투어   = visitseoul_투어
쇼핑   = visitseoul_쇼핑
"""

import json
import logging

from .config import PREPROCESSED_DIR

log = logging.getLogger(__name__)

# 병합 규칙: 최종 카테고리 → 소스 파일 목록
MERGE_MAP = {
    "관광지": [
        "tourapi_관광지.json",
        "tourapi_문화시설.json",
        "tourapi_레포츠.json",
        "visitseoul_관광지.json",
    ],
    "숙박": [
        "tourapi_숙박.json",
        "visitseoul_숙박.json",
    ],
    "음식점": [
        "tourapi_음식점.json",
        "visitseoul_음식점.json",
    ],
    "콘텐츠": [
        "seoul_culture_문화행사.json",
    ],
    "팝업스토어": [
        "popply_팝업스토어.json",
    ],
    "투어": [
        "visitseoul_투어.json",
        "visitseoul_쇼핑.json",
    ],
}


# 관광지 → 투어로 이동시킬 키워드
_MOVE_TO_TOUR = ["물품보관소"]


def _should_move_to_tour(item: dict) -> bool:
    """관광지에서 투어로 이동해야 하는 항목인지 판단."""
    title = item.get("title", "")
    return any(kw in title for kw in _MOVE_TO_TOUR)


def merge():
    """전처리된 파일들을 최종 카테고리별로 병합."""
    # 1차: 소스별 로드
    category_items: dict[str, list[dict]] = {}
    category_ids: dict[str, set[str]] = {}

    for category, sources in MERGE_MAP.items():
        merged = []
        seen_ids: set[str] = set()

        for filename in sources:
            path = PREPROCESSED_DIR / filename
            if not path.exists():
                log.warning("  %s 없음, 건너뜀", filename)
                continue

            with open(path, encoding="utf-8") as f:
                items = json.load(f)

            for item in items:
                cid = str(item.get("contentid", ""))
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                merged.append(item)

            log.info("  %s: %d건 로드", filename, len(items))

        category_items[category] = merged
        category_ids[category] = seen_ids

    # 2차: 관광지 → 투어 이동
    if "관광지" in category_items and "투어" in category_items:
        stay = []
        moved = 0
        for item in category_items["관광지"]:
            if _should_move_to_tour(item):
                cid = str(item.get("contentid", ""))
                if cid not in category_ids["투어"]:
                    category_items["투어"].append(item)
                    category_ids["투어"].add(cid)
                moved += 1
            else:
                stay.append(item)
        category_items["관광지"] = stay
        if moved:
            log.info("[merge] 관광지 → 투어: %d건 이동", moved)

    # 3차: 저장
    for category, merged in category_items.items():
        if not merged:
            log.warning("[merge] %s: 병합할 데이터 없음", category)
            continue

        output_path = PREPROCESSED_DIR / f"{category}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        log.info("[merge] %s: 총 %d건 → %s", category, len(merged), output_path.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    merge()
