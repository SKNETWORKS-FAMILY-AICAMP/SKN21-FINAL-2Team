import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scripts.src.__config import load_settings
from app.scripts.src.__pipeline import run_pipeline


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--types", nargs="+", type=int, default=[12, 14, 15, 25, 28, 32, 39])
    p.add_argument("--area-code", type=int, default=1)
    p.add_argument("--resume", action="store_true", default=True)
    p.add_argument("--fresh", action="store_true", default=False)
    p.add_argument("--num-rows", type=int, default=100)
    p.add_argument("--throttle", type=float, default=0.12)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--test-one", action="store_true")
    p.add_argument("--test-pages", type=int, default=1)
    p.add_argument("--test-geocode-limit", type=int, default=3)
    p.add_argument("--no-resume", action="store_true", default=False)
    return p.parse_args()


def main():
    args = parse_args()
    s = load_settings()

    if not s.tour_api_key:
        raise RuntimeError("TOURAPI_KEY 누락(.env 확인)")

    resume = (not args.no_resume) and (not args.fresh)

    summary = run_pipeline(
        settings=s,
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

    if args.verbose:
        print("\n=== 수집 요약 ===")
        for ct, st in summary.items():
            print(
                f"CT{ct}: fetched={st['fetched']}, wrote={st['wrote']}, "
                f"skipped={st['skipped']}, errors={st['errors']}, geocode_calls={st['geocode_calls']}"
            )


if __name__ == "__main__":
    main()
