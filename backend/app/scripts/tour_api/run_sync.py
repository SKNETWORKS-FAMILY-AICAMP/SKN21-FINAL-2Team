import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scripts.tour_api.__crawl import add_content_args, run_content_collection
from app.scripts.tour_api.__tour_api import load_settings, run_pipeline


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
    return add_content_args(parser).parse_args()


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
    content_summary = run_content_collection(args)

    print(json.dumps({
        "tour_api_types": args.types,
        "tour_api_summary": api_summary,
        "content_collection_summary": content_summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
