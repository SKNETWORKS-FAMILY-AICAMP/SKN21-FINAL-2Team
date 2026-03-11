import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False

DEFAULT_INPUT_PATH = "backend/data/llm_result/39_음식점_enriched.jsonl"
DEFAULT_OUTPUT_PATH = "backend/data/llm_result/39_음식점_enriched_image_filled.jsonl"
NAVER_IMAGE_SEARCH_ENDPOINT = "https://openapi.naver.com/v1/search/image"
NAVER_WEB_SEARCH_ENDPOINT = "https://search.naver.com/search.naver"


def _load_env_file_fallback(path: Path) -> None:
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except Exception:
        return


def load_env_candidates() -> None:
    this = Path(__file__).resolve()
    project_root = this.parents[4]
    backend_dir = this.parents[3]
    candidates = [
        project_root / ".env",
        backend_dir / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=True)
            _load_env_file_fallback(candidate)


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


@dataclass
class PlaceCandidate:
    name: str
    address: str
    image: str
    score: float = 0.0


def is_missing_image(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in {"", "null", "None"})


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


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_addr(addr: str) -> str:
    return normalize_space(re.sub(r"\([^)]*\)", " ", addr or "")).strip()


def area_hint_from_addr(addr: str) -> str:
    cleaned = clean_addr(addr)
    parts = cleaned.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return cleaned


def normalize_key(value: str) -> str:
    value = re.sub(r"</?mark>", "", value or "", flags=re.IGNORECASE)
    value = value.strip().lower()
    return re.sub(r"[^0-9a-z가-힣]+", "", value)


def tokenize(value: str) -> list[str]:
    return [token for token in re.findall(r"[0-9A-Za-z가-힣]+", normalize_space(value)) if len(token) >= 2]


def lodging_keyword_candidates(title: str) -> list[str]:
    lowered = normalize_space(title).lower()
    if any(keyword in lowered for keyword in ["guesthouse", "게스트하우스", "호스텔", "hostel"]):
        return ["게스트하우스", "호스텔", "숙소"]
    if any(keyword in lowered for keyword in ["호텔", "hotel", "mercure", "novotel", "ibis", "lotte", "shilla"]):
        return ["호텔", "숙박", "숙소"]
    if any(keyword in lowered for keyword in ["hanok", "한옥", "스테이", "stay"]):
        return ["스테이", "숙소", "숙박"]
    return ["숙박", "숙소", "호텔"]


def build_queries(item: dict[str, Any], query_mode: str) -> list[str]:
    title = normalize_space(str(item.get("title", "")))
    addr = clean_addr(str(item.get("addr", "")))
    area_hint = area_hint_from_addr(addr)
    queries: list[str] = []

    if query_mode == "lodging":
        keywords = lodging_keyword_candidates(title)
        if title and addr:
            queries.append(f"{title} {addr}")
        if title and area_hint:
            queries.extend(f"{title} {area_hint} {keyword}" for keyword in keywords)
        if title:
            queries.append(f"{title} 서울 숙소")
            queries.append(f"{title} 서울 숙박")
            queries.append(title)
    elif query_mode == "restaurant":
        if title and area_hint:
            queries.append(f"{title} {area_hint} 음식점")
        if title:
            queries.append(f"{title} 서울 음식점")
    else:
        if title and addr:
            queries.append(f"{title} {addr}")
        if title and area_hint:
            queries.append(f"{title} {area_hint}")
        if title:
            queries.append(title)

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = normalize_space(query)
        if not normalized or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
    return deduped


def build_query(title: str) -> str:
    return f"{normalize_space(title)} 서울 음식점".strip()


def decode_json_string(raw: str) -> str:
    return json.loads(f'"{raw}"')


def extract_naver_place_candidates(page_text: str) -> list[PlaceCandidate]:
    pattern = re.compile(
        r'"name":"((?:\\.|[^"\\])*)".*?"fullAddress":"((?:\\.|[^"\\])*)".*?"imageUrl":"((?:\\.|[^"\\])*)"',
        re.S,
    )
    candidates: list[PlaceCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for match in pattern.finditer(page_text):
        try:
            name = re.sub(r"</?mark>", "", decode_json_string(match.group(1)), flags=re.IGNORECASE).strip()
            address = decode_json_string(match.group(2)).strip()
            image = decode_json_string(match.group(3)).strip()
        except Exception:
            continue
        if not name or not image:
            continue
        if "og-map-400x200" in image or "searchad-phinf" in image:
            continue
        key = (name, address, image)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(PlaceCandidate(name=name, address=address, image=image))
    return candidates


def score_naver_place_candidate(item: dict[str, Any], candidate: PlaceCandidate) -> float:
    title = normalize_key(str(item.get("title", "")))
    address = clean_addr(str(item.get("addr", "")))
    candidate_name = normalize_key(candidate.name)
    candidate_addr = normalize_space(candidate.address)
    if not title or not candidate_name:
        return 0.0

    score = SequenceMatcher(None, title, candidate_name).ratio() * 2.0
    if title in candidate_name or candidate_name in title:
        score += 0.8

    area_hint = area_hint_from_addr(address)
    if area_hint and area_hint in candidate_addr:
        score += 0.6

    for token in tokenize(address)[:4]:
        if token and token in candidate_addr:
            score += 0.15

    return score


def search_image_link_from_naver_place(
    item: dict[str, Any],
    queries: list[str],
    timeout: int = 10,
    session: requests.Session | None = None,
) -> SearchResult:
    requester = session or requests
    had_error = False
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://search.naver.com/",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    for query in queries:
        try:
            response = requester.get(
                NAVER_WEB_SEARCH_ENDPOINT,
                headers=headers,
                params={"query": query},
                timeout=timeout,
            )
        except requests.RequestException:
            had_error = True
            continue

        if response.status_code != 200:
            had_error = True
            continue

        candidates = extract_naver_place_candidates(response.text)
        if not candidates:
            continue

        best: PlaceCandidate | None = None
        best_score = -1.0
        for candidate in candidates:
            candidate.score = score_naver_place_candidate(item, candidate)
            if candidate.score > best_score:
                best = candidate
                best_score = candidate.score

        if best and best.image and best_score >= 1.0:
            return SearchResult(link=best.image, had_api_error=False)

    return SearchResult(link=None, had_api_error=had_error)


def search_image_link_once(
    *,
    query: str | None = None,
    headers: dict[str, str],
    sleep_seconds: float,
    max_retries: int,
    title: str | None = None,
    timeout: int = 10,
    session: requests.Session | None = None,
) -> SearchResult:
    requester = session or requests
    effective_query = normalize_space(query or "")
    if not effective_query:
        effective_query = build_query(title or "")
    params = {
        "query": effective_query,
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
    query_mode: str,
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
        queries = build_queries(item, query_mode)
        if not queries:
            stats.no_result += 1
            if not dry_run:
                output_lines.append(json.dumps(item, ensure_ascii=False))
            continue

        search_result = SearchResult(link=None, had_api_error=False)
        if query_mode == "lodging":
            search_result = search_image_link_from_naver_place(
                item=item,
                queries=queries,
                session=session,
            )
        else:
            for query in queries:
                try:
                    search_result = search_image_link_once(
                        query=query,
                        headers=headers,
                        sleep_seconds=sleep_seconds,
                        max_retries=max_retries,
                        session=session,
                    )
                except RuntimeError:
                    raise
                except Exception:
                    search_result = SearchResult(link=None, had_api_error=True)
                if search_result.link:
                    break

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
    parser.add_argument("--query-mode", choices=["restaurant", "lodging", "generic"], default="restaurant")
    return parser.parse_args()


def main() -> int:
    load_env_candidates()
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
            query_mode=str(args.query_mode),
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
