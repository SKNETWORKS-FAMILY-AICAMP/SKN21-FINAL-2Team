import argparse
import html
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


IMAGE_SEARCH_URL = "https://openapi.naver.com/v1/search/image"
SKIP_DOMAINS = (
    "pinterest.",
    "pinimg.com",
    "imgnews.naver.net",
    "shop-phinf.pstatic.net",
    "shopping.",
)
PREFER_DOMAINS = (
    "pup-review-phinf.pstatic.net",
    "tripcdn.com",
    "mypetlife.co.kr",
    "cloudfront.net",
    "ldb-phinf.pstatic.net",
)
PLACE_KEYWORDS = (
    "카페",
    "공방",
    "사진관",
    "사찰",
    "한옥",
    "마을",
    "바",
    "보드게임카페",
    "펍",
    "주점",
    "공간",
    "호텔",
    "극장",
    "공원",
    "선착장",
    "레코드",
    "스튜디오",
    "면세점",
    "뮤직라운지",
    "서가",
    "베이커리",
    "찻집",
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def extract_district(addr: str) -> str:
    normalized = normalize_text(addr)
    match = re.search(r"서울(?:특별시|시)?\s+([가-힣]+구)", normalized)
    return match.group(1) if match else "서울"


def infer_keyword(record: dict[str, Any]) -> str:
    blob = " ".join(
        normalize_text(record.get(key, "")) for key in ("title", "introduction")
    )
    for keyword in PLACE_KEYWORDS:
        if keyword in blob:
            return keyword
    return ""


def build_queries(record: dict[str, Any]) -> list[str]:
    title = normalize_text(record.get("title", ""))
    addr = normalize_text(record.get("addr", ""))
    district = extract_district(addr)
    keyword = infer_keyword(record)

    queries = [
        f"{title} {addr}",
        f"{title} {district}",
    ]
    if keyword:
        queries.extend(
            [
                f"{title} {keyword} {district}",
                f"{keyword} {title} {district}",
                f"{title} {keyword} 서울",
            ]
        )
    queries.append(title)

    seen = set()
    deduped: list[str] = []
    for query in queries:
        normalized = normalize_text(query)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


@dataclass
class Candidate:
    link: str
    title: str
    score: int
    query: str


def score_candidate(record: dict[str, Any], query: str, item: dict[str, Any]) -> int:
    title = normalize_text(record.get("title", "")).lower()
    keyword = infer_keyword(record).lower()
    district = extract_district(record.get("addr", "")).lower()
    item_title = normalize_text(html.unescape(item.get("title", ""))).lower()
    link = (item.get("link") or "").lower()

    if not link:
        return -100
    if any(domain in link for domain in SKIP_DOMAINS):
        return -50

    score = 0
    if title and title in item_title:
        score += 8
    if keyword and keyword in item_title:
        score += 4
    if district and district in item_title:
        score += 2
    if any(domain in link for domain in PREFER_DOMAINS):
        score += 5
    if any(token in link for token in (".jpg", ".jpeg", ".png", ".webp")):
        score += 2
    if "blog" in link or "post" in link or "review" in item_title:
        score += 1
    if query.lower() in item_title:
        score += 2
    return score


def search_best_image(record: dict[str, Any], headers: dict[str, str]) -> Candidate | None:
    best: Candidate | None = None

    for query in build_queries(record):
        response = requests.get(
            IMAGE_SEARCH_URL,
            headers=headers,
            params={"query": query, "display": 10, "filter": "large", "sort": "sim"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        for item in data.get("items") or []:
            candidate = Candidate(
                link=item.get("link") or "",
                title=normalize_text(html.unescape(item.get("title", ""))),
                score=score_candidate(record, query, item),
                query=query,
            )
            if best is None or candidate.score > best.score:
                best = candidate
        if best and best.score >= 10:
            return best

    return best


def fill_images(input_path: Path, output_path: Path | None = None, limit: int | None = None) -> tuple[int, int]:
    load_dotenv("backend/.env")
    client_id = os.getenv("NAVER_SEARCH_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_SEARCH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_SEARCH_CLIENT_ID / NAVER_SEARCH_CLIENT_SECRET is not configured.")

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    rows = [json.loads(line) for line in input_path.read_text().splitlines() if line.strip()]
    updated = 0
    checked = 0

    for row in rows:
        if limit is not None and checked >= limit:
            break
        if normalize_text(row.get("image", "")):
            continue

        checked += 1
        candidate = search_best_image(row, headers)
        if candidate and candidate.link:
            row["image"] = candidate.link
            updated += 1
            print(
                f"filled {row.get('contentid')} title={row.get('title')} "
                f"score={candidate.score} query={candidate.query} link={candidate.link}"
            )
        else:
            print(f"no-image {row.get('contentid')} title={row.get('title')}")

    target_path = output_path or input_path
    with target_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return checked, updated


def main() -> None:
    parser = argparse.ArgumentParser(description="네이버 이미지 검색 API로 이미지 URL을 채웁니다.")
    parser.add_argument("input", help="입력 JSONL 경로")
    parser.add_argument("-o", "--output", help="출력 JSONL 경로. 없으면 제자리 수정")
    parser.add_argument("--limit", type=int, help="처리할 최대 행 수")
    args = parser.parse_args()

    checked, updated = fill_images(
        input_path=Path(args.input),
        output_path=Path(args.output) if args.output else None,
        limit=args.limit,
    )
    print(f"checked={checked} updated={updated}")


if __name__ == "__main__":
    main()
