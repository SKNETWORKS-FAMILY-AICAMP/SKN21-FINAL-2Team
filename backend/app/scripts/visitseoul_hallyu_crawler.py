import argparse
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://korean.visitseoul.net"
CONTENT_TYPE = "관광지"
CONTENT_TYPE_CODE = "12"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

ADDRESS_RE = re.compile(r"(?:주소|위치)\s*[:：]?\s*(.+)$")
ANGLE_BRACKET_RE = re.compile(r"<\s*([^<>]+?)\s*>")
SKIP_PREFIXES = ("Playlist ", "[")
INFO_PREFIXES = ("운영시간", "전화번호", "연락처", "교통편", "웹사이트", "홈페이지")
INFO_KEYWORDS = (
    "운영시간",
    "전화번호",
    "연락처",
    "교통편",
    "웹사이트",
    "홈페이지",
    "인스타그램",
    "instagram",
    "블로그",
    "blog",
    "카카오톡",
    "kakao",
)
BAD_TITLE_KEYWORDS = ("한류스타", "배우", "가수", "아이돌", "방송", "비밀", "전문숍", "플레이스")
DOMAIN_RE = re.compile(r"\b[\w.-]+\.(?:com|co\.kr|kr|net|at|org|io|me|tv|be)\b", re.IGNORECASE)
PLACE_SPLIT_RE = re.compile(r"[.!?]\s+")
PLACE_SUFFIX_HINTS = (
    "공방",
    "사진관",
    "클로젯",
    "스토어",
    "플래그십",
    "숍",
    "샵",
    "살롱",
    "하우스",
    "카페",
    "레코드",
    "요트",
    "주얼리",
    "공원",
    "섬",
    "숲",
    "면세점",
    "편집숍",
    "직영점",
    "플랫폼",
    "한남",
    "명동",
    "가로수길",
    "북촌",
    "통닭",
    "네일숍",
    "먹자골목",
    "마을",
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def absolutize_url(url: str, page_url: str) -> str:
    return urljoin(page_url, url.strip()) if url else ""


def strip_list_marker(text: str) -> str:
    return re.sub(r"^[\s○●•·▪■◆▶▷\-]+\s*", "", text).strip()


def update_query_param(url: str, **params: Any) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key, value in params.items():
        query[key] = [str(value)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def is_emphasized(node: Tag) -> bool:
    if node.name in {"h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"}:
        return True
    if node.find(["strong", "b"]):
        return True
    for tagged in node.find_all(True):
        style = (tagged.get("style") or "").replace(" ", "").lower()
        if "font-weight:700" in style or "font-weight:bold" in style:
            return True
    return False


def extract_place_name(title_text: str) -> str:
    matches = ANGLE_BRACKET_RE.findall(title_text)
    normalized = normalize_text(strip_list_marker(title_text))
    if matches and normalized.endswith(">"):
        return normalize_text(matches[-1])
    parts = [normalize_text(part) for part in PLACE_SPLIT_RE.split(normalized) if normalize_text(part)]
    if len(parts) > 1:
        tail = parts[-1]
        if len(tail) <= 50:
            return tail
    return normalized


def is_info_text(text: str) -> bool:
    normalized = strip_list_marker(normalize_text(text)).lower()
    return (
        any(normalized.startswith(keyword.lower()) for keyword in INFO_KEYWORDS)
        or "@" in normalized
        or "www." in normalized
        or "http" in normalized
        or bool(DOMAIN_RE.search(normalized))
    )


def extract_address(text: str) -> str:
    normalized = strip_list_marker(normalize_text(text))
    match = ADDRESS_RE.search(normalized)
    if not match:
        return ""
    address = normalize_text(match.group(1))
    if not address.startswith("서울"):
        return ""
    return address


def looks_like_place_name(text: str) -> bool:
    normalized = extract_place_name(text)
    if not normalized or len(normalized) > 80:
        return False
    if is_info_text(normalized):
        return False
    if any(keyword in normalized for keyword in BAD_TITLE_KEYWORDS) and not any(
        token in normalized for token in PLACE_SUFFIX_HINTS
    ):
        return False
    if normalized.endswith((".", "!", "?", ":", ";")):
        return False
    if "주소" in normalized or "위치" in normalized:
        return False
    if any(token in normalized for token in PLACE_SUFFIX_HINTS):
        return True
    if ANGLE_BRACKET_RE.search(text):
        return True
    if len(normalized.split()) <= 4 and len(normalized) <= 30:
        return True
    return False


def extract_place_name_from_intro(text: str) -> str:
    normalized = normalize_text(text)
    candidates: list[tuple[int, str]] = []

    quoted_pattern = re.compile(r"[<\"'“‘]\s*([^<>\"'“”‘’]{2,40})\s*[>\"'”’]\s*(?:은|는|이|가)")
    for match in quoted_pattern.finditer(normalized):
        candidate = extract_place_name(match.group(1))
        if looks_like_place_name(candidate):
            score = 10 + sum(token in candidate for token in PLACE_SUFFIX_HINTS)
            candidates.append((score, candidate))

    inline_pattern = re.compile(
        r"\b([A-Za-z0-9가-힣&().,\- ]{2,40})\s*(?:은|는|이|가)\s*(?:.+?)(?:공방|사진관|클로젯|스토어|플래그십|숍|샵|살롱|하우스|카페|레코드|요트|주얼리|공원|섬|숲|미술관|통닭|네일숍)"
    )
    for match in inline_pattern.finditer(normalized):
        candidate = extract_place_name(match.group(1))
        if looks_like_place_name(candidate):
            score = 5 + sum(token in candidate for token in PLACE_SUFFIX_HINTS)
            candidates.append((score, candidate))

    if not candidates:
        return ""

    candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return candidates[0][1]


def find_quoted_place_in_segment(segment: list[dict[str, Any]]) -> tuple[str, int] | None:
    quoted_pattern = re.compile(r"[<\"'“‘]\s*([^<>\"'“”‘’]{2,40})\s*[>\"'”’]\s*(?:은|는|이|가)?")
    text_indices = [i for i, block in enumerate(segment) if block["type"] == "text"]
    recent_indices = set(text_indices[-4:])
    for index in range(len(segment) - 1, -1, -1):
        block = segment[index]
        if block["type"] != "text":
            continue
        if index not in recent_indices:
            continue
        text = block["text"]
        if is_info_text(text) or extract_address(text):
            continue
        for match in quoted_pattern.finditer(text):
            candidate = extract_place_name(match.group(1))
            if looks_like_place_name(candidate):
                return candidate, index
    return None


def make_record(contentid: str, title: str, image: str, addr: str, introduction: str) -> dict[str, str]:
    record = {
        "contentid": contentid,
        "title": title,
        "contenttypeid": CONTENT_TYPE,
        "image": image,
        "usetime": "",
        "restdate": "",
        "parking": "",
        "addr": addr,
        "mapy": "",
        "mapx": "",
        "tel": "",
        "contenttypeid_code": CONTENT_TYPE_CODE,
    }
    if introduction:
        record["introduction"] = introduction
    return record


def should_skip_text(text: str) -> bool:
    return not text or text.startswith(SKIP_PREFIXES)


def should_capture_text_node(node: Tag, text: str) -> bool:
    if node.name in {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
        return True
    if node.name == "span" and (
        extract_address(text)
        or is_info_text(text)
    ):
        return True
    return False


def iter_content_blocks(content: Tag, page_url: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    seen = set()

    for node in content.descendants:
        if not isinstance(node, Tag):
            continue

        if node.name == "img":
            src = absolutize_url(node.get("src", ""), page_url)
            if not src:
                continue
            key = ("image", src)
            if key in seen:
                continue
            seen.add(key)
            blocks.append(
                {
                    "type": "image",
                    "src": src,
                    "alt": normalize_text(node.get("alt", "")),
                }
            )
            continue

        text = normalize_text(node.get_text(" ", strip=True))
        if not text:
            continue
        if not should_capture_text_node(node, text):
            continue
        key = ("text", node.name, text)
        if key in seen:
            continue
        seen.add(key)
        blocks.append(
            {
                "type": "text",
                "tag": node.name,
                "text": text,
                "emphasized": is_emphasized(node),
            }
        )

    return blocks


def score_title_candidate(block: dict[str, Any]) -> int:
    text = block["text"]
    score = 0

    if should_skip_text(text) or extract_address(text):
        return -10
    if is_info_text(text):
        return -10
    if not looks_like_place_name(text):
        return -10
    if ANGLE_BRACKET_RE.search(text):
        score += 4
    if block.get("emphasized"):
        score += 3
    if block.get("tag") in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        score += 2
    if len(text) <= 80:
        score += 2
    if len(text) <= 40:
        score += 1
    return score


def choose_title_block(segment: list[dict[str, Any]]) -> dict[str, Any] | None:
    best_block = None
    best_score = 0

    for block in reversed(segment):
        if block["type"] != "text":
            continue
        score = score_title_candidate(block)
        if score > best_score:
            best_score = score
            best_block = block
        if score >= 6:
            return block

    return best_block if best_score >= 4 else None


def extract_record_from_segment(
    article_key: str,
    record_index: int,
    segment: list[dict[str, Any]],
    address: str,
    fallback_image: str = "",
) -> dict[str, str] | None:
    quoted_candidate = find_quoted_place_in_segment(segment)
    title_block = choose_title_block(segment)
    title_idx = quoted_candidate[1] if quoted_candidate else (segment.index(title_block) if title_block else -1)

    image = ""
    for block in reversed(segment[: title_idx + 1] if title_idx >= 0 else segment):
        if block["type"] == "image":
            image = block["src"]
            break
    if not image:
        for block in reversed(segment):
            if block["type"] == "image":
                image = block["src"]
                break
    if not image:
        image = fallback_image

    intro_parts: list[str] = []
    for block in segment[title_idx + 1 if title_idx >= 0 else 0 :]:
        if block["type"] != "text":
            continue
        text = block["text"]
        if should_skip_text(text) or extract_address(text) or is_info_text(text):
            continue
        if score_title_candidate(block) >= 6 and intro_parts:
            break
        intro_parts.append(text)

    introduction = normalize_text(" ".join(intro_parts))
    title = quoted_candidate[0] if quoted_candidate else (extract_place_name(title_block["text"]) if title_block else "")
    intro_title = extract_place_name_from_intro(introduction)
    if intro_title and (
        not looks_like_place_name(title)
        or any(keyword in title for keyword in BAD_TITLE_KEYWORDS)
    ):
        title = intro_title
    elif not looks_like_place_name(title):
        title = intro_title
    if not looks_like_place_name(title):
        return None

    contentid = f"{article_key}_{record_index:02d}"
    return make_record(
        contentid=contentid,
        title=title,
        image=image,
        addr=address,
        introduction=introduction,
    )


def extract_page_payload(page_url: str, soup: BeautifulSoup) -> dict[str, Any]:
    content = soup.select_one("div.se-contents")
    if content is None:
        content = soup.select_one("div.text-area")
    if content is None:
        raise ValueError("본문 컨테이너(div.se-contents 또는 div.text-area)를 찾지 못했습니다.")

    page_title = normalize_text(
        (soup.select_one("meta[property='og:title']") or {}).get("content", "")
    )
    meta_description = normalize_text(
        (soup.select_one("meta[name='description']") or {}).get("content", "")
    )
    blocks = iter_content_blocks(content, page_url)
    body_text = normalize_text(
        " ".join(block["text"] for block in blocks if block["type"] == "text")
    )

    return {
        "url": page_url,
        "page_title": page_title,
        "meta_description": meta_description,
        "body_text": body_text,
        "blocks": blocks,
    }


def parse_place_blocks(page_url: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    article_key = urlparse(page_url).path.rstrip("/").split("/")[-1] or "visitseoul"
    records: list[dict[str, str]] = []
    segment: list[dict[str, Any]] = []
    last_address = ""
    last_image = ""

    def flush_shared_address_segment() -> None:
        nonlocal segment, last_address
        if not last_address or not segment:
            segment = []
            return
        record = extract_record_from_segment(
            article_key=article_key,
            record_index=len(records) + 1,
            segment=segment,
            address=last_address,
            fallback_image=last_image,
        )
        if record:
            records.append(record)
        segment = []
        last_address = ""

    for block in payload["blocks"]:
        if block["type"] == "image":
            last_image = block["src"]

        if (
            block["type"] == "text"
            and block["text"].startswith("Playlist ")
            and last_address
            and segment
        ):
            flush_shared_address_segment()

        segment.append(block)
        if block["type"] != "text":
            continue

        address = extract_address(block["text"])
        if not address:
            continue

        record = extract_record_from_segment(
            article_key=article_key,
            record_index=len(records) + 1,
            segment=segment[:-1],
            address=address,
            fallback_image=last_image,
        )
        if record:
            records.append(record)
        segment = []
        last_address = address

    flush_shared_address_segment()
    return records


def fetch_page(url: str, timeout: int = 30) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def extract_listing_total_pages(list_url: str, soup: BeautifulSoup) -> int:
    paging = soup.select_one(".paging-lst")
    if paging is None:
        return 1

    max_page = 1
    for anchor in paging.select("a[href]"):
        href = absolutize_url(anchor.get("href", ""), list_url)
        parsed = urlparse(href)
        cur_page = parse_qs(parsed.query).get("curPage", ["1"])[0]
        if cur_page.isdigit():
            max_page = max(max_page, int(cur_page))
    return max_page


def extract_listing_links(list_url: str, soup: BeautifulSoup) -> list[str]:
    section = soup.select_one("section.article-list-element")
    if section is None:
        return []

    links: list[str] = []
    seen = set()
    for anchor in section.select("ul.article-list li.item > a[href]"):
        href = absolutize_url(anchor.get("href", ""), list_url)
        parsed = urlparse(href)
        if "/hallyu/" not in parsed.path:
            continue
        if href in seen:
            continue
        seen.add(href)
        links.append(href)
    return links


def collect_listing_urls(list_url: str) -> list[str]:
    first_html = fetch_page(list_url)
    first_soup = BeautifulSoup(first_html, "lxml")
    total_pages = extract_listing_total_pages(list_url, first_soup)

    urls = extract_listing_links(list_url, first_soup)
    seen = set(urls)

    for page in range(2, total_pages + 1):
        page_url = update_query_param(list_url, curPage=page)
        html = fetch_page(page_url)
        soup = BeautifulSoup(html, "lxml")
        for url in extract_listing_links(page_url, soup):
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)

    return urls


def crawl_visitseoul_hallyu(urls: Iterable[str]) -> list[dict[str, str]]:
    all_records: list[dict[str, str]] = []
    for url in urls:
        html = fetch_page(url)
        soup = BeautifulSoup(html, "lxml")
        payload = extract_page_payload(url, soup)
        all_records.extend(parse_place_blocks(url, payload))
    return all_records


def write_output(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".jsonl":
        with output_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def crawl_raw_payloads(urls: Iterable[str]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for url in urls:
        try:
            html = fetch_page(url)
            soup = BeautifulSoup(html, "lxml")
            payloads.append(extract_page_payload(url, soup))
        except Exception as exc:
            print(f"skip {url} ({exc})")
    return payloads


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visit Seoul 한류/에디토리얼 게시물에서 장소 정보를 추출합니다."
    )
    parser.add_argument("urls", nargs="*", help="크롤링할 Visit Seoul 게시물 URL")
    parser.add_argument(
        "--list-url",
        action="append",
        default=[],
        help="한류 목록 URL. 여러 페이지를 순회해 상세 게시물 URL을 자동 수집합니다.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="backend/data/visitseoul_hallyu_places.json",
        help="출력 파일 경로 (.json 또는 .jsonl)",
    )
    parser.add_argument(
        "--raw-output",
        help="1차 크롤링 전체 본문 블록을 저장할 JSON 경로",
    )
    args = parser.parse_args()

    if not args.urls and not args.list_url:
        parser.error("최소 하나의 게시물 URL 또는 --list-url 이 필요합니다.")

    target_urls = list(args.urls)
    for list_url in args.list_url:
        target_urls.extend(collect_listing_urls(list_url))

    deduped_urls: list[str] = []
    seen_urls = set()
    for url in target_urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped_urls.append(url)

    raw_payloads = crawl_raw_payloads(deduped_urls)
    if args.raw_output:
        write_output(raw_payloads, Path(args.raw_output))

    records: list[dict[str, str]] = []
    for payload in raw_payloads:
        records.extend(parse_place_blocks(payload["url"], payload))
    write_output(records, Path(args.output))
    print(f"saved {len(records)} places to {args.output}")


if __name__ == "__main__":
    main()
