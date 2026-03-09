import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

DEFAULT_INPUT_PATH = "backend/data/llm_result/39_음식점_enriched.jsonl"
DEFAULT_OUTPUT_PATH = "backend/data/llm_result/39_음식점_enriched_image_filled.jsonl"
NAVER_IMAGE_SEARCH_ENDPOINT = "https://openapi.naver.com/v1/search/image"


@dataclass
class FillStats:
    total: int = 0
    target_missing: int = 0
    filled: int = 0
    skipped_existing: int = 0
    no_result: int = 0
    api_error: int = 0
    parse_error: int = 0
    processed_targets: int = 0


@dataclass
class SearchResult:
    link: str | None
    had_api_error: bool = False


def is_missing_image(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def extract_first_link(payload: dict[str, Any]) -> str | None:
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return None

    first_item = items[0]
    if not isinstance(first_item, dict):
        return None

    link = first_item.get("link")
    if isinstance(link, str) and link.strip():
        return link.strip()
    return None


def get_naver_auth_headers() -> dict[str, str]:
    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set.")

    return {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }


def build_query(title: str) -> str:
    normalized = title.strip()
    return f"{normalized} 서울 음식점"


def search_image_link_once(
    title: str,
    headers: dict[str, str],
    sleep_seconds: float,
    max_retries: int,
    timeout: int = 10,
    session: requests.Session | None = None,
) -> SearchResult:
    requester = session or requests
    params = {
        "query": build_query(title),
        "display": 1,
        "start": 1,
        "sort": "sim",
        "filter": "large",
    }

    for attempt in range(max_retries + 1):
        try:
            response = requester.get(
                NAVER_IMAGE_SEARCH_ENDPOINT,
                headers=headers,
                params=params,
                timeout=timeout,
            )
        except requests.RequestException:
            if attempt == max_retries:
                return SearchResult(link=None, had_api_error=True)
            time.sleep(max(0.2, sleep_seconds * (2 ** attempt)))
            continue

        status = response.status_code
        if status in (401, 403):
            raise RuntimeError(f"Naver auth failed with status={status}.")

        if status == 200:
            try:
                payload = response.json()
            except ValueError:
                return SearchResult(link=None, had_api_error=True)
            return SearchResult(link=extract_first_link(payload), had_api_error=False)

        if status == 429 or 500 <= status <= 599:
            if attempt == max_retries:
                return SearchResult(link=None, had_api_error=True)
            time.sleep(max(0.2, sleep_seconds * (2 ** attempt)))
            continue

        return SearchResult(link=None, had_api_error=True)

    return SearchResult(link=None, had_api_error=True)


def process_jsonl(
    input_path: Path,
    output_path: Path,
    dry_run: bool,
    limit: int | None,
    sleep_seconds: float,
    max_retries: int,
) -> FillStats:
    headers = get_naver_auth_headers()
    stats = FillStats()

    input_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as rf:
        lines = rf.readlines()

    stats.total = len(lines)
    session = requests.Session()
    output_lines: list[str] = []

    for index, line in enumerate(lines, start=1):
        raw_line = line.strip()
        if not raw_line:
            stats.parse_error += 1
            continue

        try:
            item = json.loads(raw_line)
        except json.JSONDecodeError:
            stats.parse_error += 1
            continue

        image_value = item.get("image")
        if not is_missing_image(image_value):
            stats.skipped_existing += 1
            if not dry_run:
                output_lines.append(json.dumps(item, ensure_ascii=False))
            continue

        stats.target_missing += 1
        if limit is not None and stats.processed_targets >= limit:
            if not dry_run:
                output_lines.append(json.dumps(item, ensure_ascii=False))
            continue

        stats.processed_targets += 1
        title = str(item.get("title", "")).strip()
        if not title:
            stats.no_result += 1
            if not dry_run:
                output_lines.append(json.dumps(item, ensure_ascii=False))
            continue

        try:
            search_result = search_image_link_once(
                title=title,
                headers=headers,
                sleep_seconds=sleep_seconds,
                max_retries=max_retries,
                session=session,
            )
        except RuntimeError:
            raise
        except Exception:
            search_result = SearchResult(link=None, had_api_error=True)

        if search_result.had_api_error:
            stats.api_error += 1

        link = search_result.link
        if link:
            item["image"] = link
            stats.filled += 1
        else:
            stats.no_result += 1

        if not dry_run:
            output_lines.append(json.dumps(item, ensure_ascii=False))

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        if stats.processed_targets % 20 == 0:
            print(
                f"[PROGRESS] line={index}/{stats.total} targets={stats.processed_targets} filled={stats.filled}"
            )

    session.close()

    if not dry_run:
        with output_path.open("w", encoding="utf-8") as wf:
            for out_line in output_lines:
                wf.write(out_line + "\n")

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill missing image fields in JSONL with Naver image search link."
    )
    parser.add_argument("--input-path", default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-path", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--max-retries", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    load_dotenv(override=True)
    args = parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    if not input_path.exists():
        print(f"[ERROR] input file not found: {input_path}")
        return 1

    try:
        stats = process_jsonl(
            input_path=input_path,
            output_path=output_path,
            dry_run=bool(args.dry_run),
            limit=args.limit,
            sleep_seconds=float(args.sleep),
            max_retries=int(args.max_retries),
        )
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1
    except Exception as exc:
        print(f"[ERROR] unexpected failure: {exc}")
        return 1

    print("[SUMMARY]")
    print(f"total={stats.total}")
    print(f"target_missing={stats.target_missing}")
    print(f"processed_targets={stats.processed_targets}")
    print(f"filled={stats.filled}")
    print(f"skipped_existing={stats.skipped_existing}")
    print(f"no_result={stats.no_result}")
    print(f"api_error={stats.api_error}")
    print(f"parse_error={stats.parse_error}")
    print(f"output_path={output_path}")
    if args.dry_run:
        print("dry_run=true (no file written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
