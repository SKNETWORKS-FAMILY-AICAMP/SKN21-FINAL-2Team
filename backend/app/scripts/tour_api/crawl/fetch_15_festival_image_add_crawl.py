import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[4]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scripts.tour_api.crawl.__festival_event_image_add_crawl import (
    DEFAULT_CRAWL_OUTPUT_PATH,
    build_festival_image_add_crawl_only,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=DEFAULT_CRAWL_OUTPUT_PATH)
    parser.add_argument('--max-seoul-pages', type=int, default=None)
    parser.add_argument('--max-visitkorea-pages', type=int, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    summary = build_festival_image_add_crawl_only(
        output_path=args.output,
        max_seoul_pages=args.max_seoul_pages,
        max_visitkorea_pages=args.max_visitkorea_pages,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
