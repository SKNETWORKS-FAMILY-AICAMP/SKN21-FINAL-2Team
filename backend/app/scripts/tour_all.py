from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 실행 위치와 무관하게 src import 가능하도록 경로 주입
THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (  # noqa: E402
    TOURAPI_BASE_URL,
    TOURAPI_KEY,
    TOURAPI_MOBILE_OS,
    TOURAPI_MOBILE_APP,
    TOURAPI_TYPE,
    OUTPUT_DIR,
    SEOUL_AREA_CODE,
    DEFAULT_NUM_ROWS,
    DEFAULT_THROTTLE_S,
)
from area_collector import collect_multi_categories_into_one_file  # noqa: E402

ALL_CATEGORIES = {
    12: "관광지",
    14: "문화시설",
    15: "축제공연행사",
    25: "여행코스",
    28: "레포츠",
    32: "숙박",
    38: "쇼핑",
    39: "음식점",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("TourAPI all-in-one collector")
    p.add_argument(
        "--types",
        nargs="+",
        type=int,
        default=list(ALL_CATEGORIES.keys()),
        help="수집할 contentTypeId 목록. 예: --types 14 15 25",
    )
    p.add_argument(
        "--area-code",
        type=int,
        default=SEOUL_AREA_CODE,
        help=f"지역코드 (기본: {SEOUL_AREA_CODE})",
    )
    p.add_argument(
        "--num-rows",
        type=int,
        default=DEFAULT_NUM_ROWS,
        help=f"페이지당 row 수 (기본: {DEFAULT_NUM_ROWS})",
    )
    p.add_argument(
        "--throttle",
        type=float,
        default=DEFAULT_THROTTLE_S,
        help=f"요청 간 대기초 (기본: {DEFAULT_THROTTLE_S})",
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help="기존 산출물/체크포인트 무시하고 처음부터 새로 수집",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if not TOURAPI_KEY:
        raise ValueError("TOURAPI_KEY가 비어있음. backend/app/scripts/src/.env 확인")

    selected = [t for t in args.types if t in ALL_CATEGORIES]
    if not selected:
        raise ValueError(f"유효한 타입이 없음. 허용: {sorted(ALL_CATEGORIES.keys())}")

    category_map = {t: ALL_CATEGORIES[t] for t in selected}

    collect_multi_categories_into_one_file(
        base_url=TOURAPI_BASE_URL,
        service_key=TOURAPI_KEY,
        mobile_os=TOURAPI_MOBILE_OS,
        mobile_app=TOURAPI_MOBILE_APP,
        resp_type=TOURAPI_TYPE,
        outdir=OUTPUT_DIR,
        category_map=category_map,
        area_code=args.area_code,
        num_rows=args.num_rows,
        throttle_s=args.throttle,
        resume=(not args.fresh),
    )


if __name__ == "__main__":
    main()
