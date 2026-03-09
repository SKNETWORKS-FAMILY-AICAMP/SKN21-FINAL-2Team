import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DEFAULT_INPUT_PATH = "backend/data/llm_result/39_음식점_enriched.jsonl"
DEFAULT_OUTPUT_PATH = "backend/data/llm_result/39_음식점_enriched_image_filled.jsonl"
DEFAULT_REPORT_PATH = "backend/data/llm_result/39_음식점_enriched_visitkorea_report.json"

VISITKOREA_MAIN_URL = "https://korean.visitkorea.or.kr/main/main.do"
VISITKOREA_SEARCH_URL = "https://korean.visitkorea.or.kr/json/jsp/search_json.jsp"
VISITKOREA_DETAIL_URL = "https://korean.visitkorea.or.kr/detail/detail_view.do?cotid={cotid}"
VISITKOREA_SEARCH_CONTENT_TYPES = "recommend|course|attraction|festival|event|show|news|promotion"
VISITKOREA_SEARCH_FIELD = "TITLE/150,DISPLAY_TITLE/50,AREA_NAME/100,SIGUGUN_NAME/100,TAG_NAME/50,BODY/50,SUB_NAME/50"


@dataclass
class FillStats:
    total: int = 0
    target_missing: int = 0
    processed_targets: int = 0
    filled: int = 0
    skipped_existing: int = 0
    no_attraction: int = 0
    low_similarity: int = 0
    no_image: int = 0
    request_error: int = 0
    parse_error: int = 0


@dataclass
class CandidateMatch:
    candidate: dict[str, Any] | None
    similarity: float
    top_candidates: list[dict[str, Any]]


def is_missing_image(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def normalize_search_response(raw_text: str) -> dict[str, Any]:
    text = raw_text.replace("\n", "").replace("\r", "").replace("\t", "")
    text = re.sub(r",\s*,\s*]", "]", text)
    text = re.sub(r",\s*,\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    text = re.sub(r",\s*}", "}", text)

    # Keep only the outer-most JSON object boundary when trailing artifacts exist.
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise json.JSONDecodeError("Invalid JSON boundary", text, 0)
    text = text[start_idx : end_idx + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some responses still include extra closing brackets at the end.
        # Trim suffix progressively and parse the longest valid object.
        for i in range(len(text) - 1, start_idx, -1):
            if text[i] != "}":
                continue
            candidate = text[start_idx : i + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise


def normalize_title(text: str) -> str:
    text = re.sub(r"<!HS>|<!HE>", "", text or "", flags=re.IGNORECASE)
    text = text.strip().lower()
    text = re.sub(r"[^0-9a-z가-힣]+", "", text)
    return text


def similarity_score(source_title: str, candidate_title: str) -> float:
    a = normalize_title(source_title)
    b = normalize_title(candidate_title)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def extract_attraction_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    data = payload.get("Data")
    if not isinstance(data, list):
        return candidates

    for bucket in data:
        if not isinstance(bucket, dict):
            continue
        groups = bucket.get("Result")
        if not isinstance(groups, list):
            continue

        for group in groups:
            if not isinstance(group, dict):
                continue
            type_name = str(group.get("ContentTypeName", "")).strip().lower()
            if type_name != "attraction":
                continue
            group_result = group.get("GroupResult")
            if not isinstance(group_result, list):
                continue
            for item in group_result:
                if isinstance(item, dict):
                    candidates.append(item)
    return candidates


def select_best_candidate(title: str, candidates: list[dict[str, Any]]) -> CandidateMatch:
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in candidates:
        candidate_title = str(candidate.get("TITLE", ""))
        score = similarity_score(title, candidate_title)
        scored.append((score, candidate))

    if not scored:
        return CandidateMatch(candidate=None, similarity=0.0, top_candidates=[])

    scored.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [
        {
            "title": re.sub(r"<!HS>|<!HE>", "", str(item.get("TITLE", ""))),
            "cotid": item.get("COT_ID", ""),
            "score": round(score, 4),
        }
        for score, item in scored[:3]
    ]
    return CandidateMatch(candidate=scored[0][1], similarity=scored[0][0], top_candidates=top_candidates)


def extract_representative_image_url(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    og_image = soup.select_one('meta[property="og:image"]')
    if og_image and og_image.get("content"):
        return urljoin(page_url, og_image["content"].strip())

    for selector in [
        ".detail_top_wrap img",
        ".detail_topWrap img",
        ".top_visual img",
        ".gallery_wrap img",
        ".img_typeBox img",
    ]:
        element = soup.select_one(selector)
        if element and element.get("src"):
            return urljoin(page_url, element["src"].strip())

    html_text = str(soup)
    image_url_pattern = re.compile(
        r"https?://(?:cdn|tong)\.visitkorea\.or\.kr/[^\s\"']+\.(?:jpg|jpeg|png|webp)",
        flags=re.IGNORECASE,
    )
    match = image_url_pattern.search(html_text)
    if match:
        return match.group(0)

    image_id_pattern = re.compile(r'"IMAGE_URL"\s*:\s*"([0-9a-fA-F-]{16,})"')
    id_match = image_id_pattern.search(html_text)
    if id_match:
        return f"https://cdn.visitkorea.or.kr/img/call?cmd=VIEW&id={id_match.group(1)}"

    return None


class VisitKoreaClient:
    def __init__(self, headless: bool = True, timeout: int = 20):
        self.headless = headless
        self.timeout = timeout
        self.http_session = requests.Session()
        self._driver = None
        self._initialized = False

    def open(self) -> None:
        if self._initialized:
            return
        driver = self._create_webdriver()
        driver.get(VISITKOREA_MAIN_URL)
        time.sleep(1)
        user_agent = driver.execute_script("return navigator.userAgent")
        cookies = driver.get_cookies()
        driver.quit()

        self.http_session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "*/*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Origin": "https://korean.visitkorea.or.kr",
                "Referer": "https://korean.visitkorea.or.kr/search/search_list.do",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        for cookie in cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            domain = cookie.get("domain")
            if not name or value is None:
                continue
            self.http_session.cookies.set(name, value, domain=domain)
        self._initialized = True

    def close(self) -> None:
        self.http_session.close()

    def _create_webdriver(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
        except ImportError as exc:
            raise RuntimeError("selenium is not installed. Install selenium and ChromeDriver.") from exc

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1400,1400")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        return webdriver.Chrome(service=Service(), options=options)

    def search(self, query: str) -> dict[str, Any]:
        self.open()
        data = {
            "query": query,
            "collection": "content",
            "contentTypeNameValue": VISITKOREA_SEARCH_CONTENT_TYPES,
            "startCount": 0,
            "contentSearchField": VISITKOREA_SEARCH_FIELD,
            "sort": "RANK/DESC",
            "totalContentCount": 3,
            "totalMediaCount": 10,
            "totalNewsCount": 10,
            "listCount": 10,
            "groupFlag": "Y",
            "contentCategoryFlag": "N",
            "contentCategoryWeight": "",
            "category": "",
            "spellerSearchFlag": "N",
        }
        response = self.http_session.post(VISITKOREA_SEARCH_URL, data=data, timeout=self.timeout)
        response.raise_for_status()
        return normalize_search_response(response.text)

    def fetch_detail_html(self, cotid: str) -> str:
        self.open()
        detail_url = VISITKOREA_DETAIL_URL.format(cotid=cotid)
        headers = {
            "User-Agent": self.http_session.headers.get("User-Agent", ""),
            "Accept-Language": self.http_session.headers.get("Accept-Language", ""),
            "Referer": "https://korean.visitkorea.or.kr/search/search_list.do",
        }
        response = self.http_session.get(detail_url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.text


def process_jsonl(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    limit: int | None,
    similarity_threshold: float,
    sleep_seconds: float,
    timeout: int,
    headless: bool,
    client: VisitKoreaClient | None = None,
) -> FillStats:
    stats = FillStats()
    failures: list[dict[str, Any]] = []
    output_lines: list[str] = []

    with input_path.open("r", encoding="utf-8") as rf:
        lines = rf.readlines()
    stats.total = len(lines)

    own_client = client is None
    vk_client = client or VisitKoreaClient(headless=headless, timeout=timeout)

    try:
        if own_client:
            vk_client.open()

        for index, line in enumerate(lines, start=1):
            raw = line.strip()
            if not raw:
                stats.parse_error += 1
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                stats.parse_error += 1
                continue

            if not is_missing_image(item.get("image")):
                stats.skipped_existing += 1
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            stats.target_missing += 1
            if limit is not None and stats.processed_targets >= limit:
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            stats.processed_targets += 1
            title = str(item.get("title", "")).strip()
            if not title:
                stats.low_similarity += 1
                failures.append(
                    {
                        "contentid": item.get("contentid", ""),
                        "title": title,
                        "reason": "empty_title",
                        "top_candidates": [],
                    }
                )
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            try:
                search_payload = vk_client.search(title)
            except Exception as exc:
                stats.request_error += 1
                failures.append(
                    {
                        "contentid": item.get("contentid", ""),
                        "title": title,
                        "reason": f"search_error:{type(exc).__name__}",
                        "top_candidates": [],
                    }
                )
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            attraction_candidates = extract_attraction_candidates(search_payload)
            if not attraction_candidates:
                stats.no_attraction += 1
                failures.append(
                    {
                        "contentid": item.get("contentid", ""),
                        "title": title,
                        "reason": "no_attraction",
                        "top_candidates": [],
                    }
                )
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            match = select_best_candidate(title, attraction_candidates)
            if not match.candidate or match.similarity < similarity_threshold:
                stats.low_similarity += 1
                failures.append(
                    {
                        "contentid": item.get("contentid", ""),
                        "title": title,
                        "reason": f"low_similarity:{match.similarity:.4f}",
                        "top_candidates": match.top_candidates,
                    }
                )
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            cotid = str(match.candidate.get("COT_ID", "")).strip()
            if not cotid:
                stats.no_image += 1
                failures.append(
                    {
                        "contentid": item.get("contentid", ""),
                        "title": title,
                        "reason": "missing_cotid",
                        "top_candidates": match.top_candidates,
                    }
                )
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            try:
                detail_html = vk_client.fetch_detail_html(cotid)
            except Exception as exc:
                stats.request_error += 1
                failures.append(
                    {
                        "contentid": item.get("contentid", ""),
                        "title": title,
                        "reason": f"detail_error:{type(exc).__name__}",
                        "top_candidates": match.top_candidates,
                    }
                )
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            detail_url = VISITKOREA_DETAIL_URL.format(cotid=cotid)
            image_url = extract_representative_image_url(detail_html, detail_url)
            if not image_url:
                stats.no_image += 1
                failures.append(
                    {
                        "contentid": item.get("contentid", ""),
                        "title": title,
                        "reason": "no_image",
                        "top_candidates": match.top_candidates,
                    }
                )
                output_lines.append(json.dumps(item, ensure_ascii=False))
                continue

            item["image"] = image_url
            stats.filled += 1
            output_lines.append(json.dumps(item, ensure_ascii=False))

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

            if stats.processed_targets % 20 == 0:
                print(
                    f"[PROGRESS] line={index}/{stats.total} targets={stats.processed_targets} filled={stats.filled}"
                )
    finally:
        if own_client:
            vk_client.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as wf:
        for out_line in output_lines:
            wf.write(out_line + "\n")

    report = {
        "summary": {
            "total": stats.total,
            "target_missing": stats.target_missing,
            "processed_targets": stats.processed_targets,
            "filled": stats.filled,
            "skipped_existing": stats.skipped_existing,
            "no_attraction": stats.no_attraction,
            "low_similarity": stats.low_similarity,
            "no_image": stats.no_image,
            "request_error": stats.request_error,
            "parse_error": stats.parse_error,
        },
        "failures": failures,
    }
    with report_path.open("w", encoding="utf-8") as rf:
        json.dump(report, rf, ensure_ascii=False, indent=2)

    return stats


def _parse_bool(value: str) -> bool:
    return str(value).lower() in {"1", "true", "t", "yes", "y", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill missing image fields in JSONL using VisitKorea search/detail crawling."
    )
    parser.add_argument("--input-path", default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-path", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--similarity-threshold", type=float, default=0.65)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--headless", default="true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    report_path = Path(args.report_path)
    if not input_path.exists():
        print(f"[ERROR] input file not found: {input_path}")
        return 1

    try:
        stats = process_jsonl(
            input_path=input_path,
            output_path=output_path,
            report_path=report_path,
            limit=args.limit,
            similarity_threshold=float(args.similarity_threshold),
            sleep_seconds=float(args.sleep),
            timeout=int(args.timeout),
            headless=_parse_bool(args.headless),
        )
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        return 1

    print("[SUMMARY]")
    print(f"total={stats.total}")
    print(f"target_missing={stats.target_missing}")
    print(f"processed_targets={stats.processed_targets}")
    print(f"filled={stats.filled}")
    print(f"skipped_existing={stats.skipped_existing}")
    print(f"no_attraction={stats.no_attraction}")
    print(f"low_similarity={stats.low_similarity}")
    print(f"no_image={stats.no_image}")
    print(f"request_error={stats.request_error}")
    print(f"parse_error={stats.parse_error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
