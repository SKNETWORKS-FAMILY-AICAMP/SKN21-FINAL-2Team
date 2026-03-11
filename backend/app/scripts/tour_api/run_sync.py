import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scripts.tour_api.__config import load_settings
from app.scripts.tour_api.__pipeline import run_pipeline
from app.scripts.tour_api.crawl.__festival_event_image_add_crawl import (
    DEFAULT_CRAWL_OUTPUT_PATH,
    build_festival_image_add_crawl_only,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--types", nargs="+", type=int, default=[12, 14, 25, 28, 32, 39])
    parser.add_argument("--area-code", type=int, default=1)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--fresh", action="store_true", default=False)
    parser.add_argument("--num-rows", type=int, default=100)
    parser.add_argument("--throttle", type=float, default=0.12)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--test-one", action="store_true")
    parser.add_argument("--test-pages", type=int, default=1)
    parser.add_argument("--test-geocode-limit", type=int, default=3)
    parser.add_argument("--no-resume", action="store_true", default=False)
    parser.add_argument("--skip-15-crawl", action="store_true", default=False)
    parser.add_argument("--festival-output", type=Path, default=DEFAULT_CRAWL_OUTPUT_PATH)
    parser.add_argument("--max-seoul-pages", type=int, default=None)
    parser.add_argument("--max-visitkorea-pages", type=int, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    if 15 in args.types:
        raise RuntimeError("15_축제공연행사 is crawler-only. Remove 15 from --types and use the built-in crawl step.")
    settings = load_settings()
    if not settings.tour_api_key:
        raise RuntimeError("TOURAPI_KEY 누락(.env 확인)")
    resume = (not args.no_resume) and (not args.fresh)
    api_summary = run_pipeline(
        settings=settings,
        content_types=args.types,
        area_code=args.area_code,
        resume=resume,
        fresh=args.fresh,
        num_rows=args.num_rows,
        throttle=args.throttle,
        verbose=args.verbose,
        test_one=args.test_one,
        test_pages=args.test_pages,
        test_geocode_limit=args.test_geocode_limit,
    )

    festival_summary = None
    if not args.skip_15_crawl:
        festival_summary = build_festival_image_add_crawl_only(
            output_path=args.festival_output,
            max_seoul_pages=args.max_seoul_pages,
            max_visitkorea_pages=args.max_visitkorea_pages,
        )

    print(json.dumps({
        "tour_api_types": args.types,
        "tour_api_summary": api_summary,
        "festival_crawl_summary": festival_summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
