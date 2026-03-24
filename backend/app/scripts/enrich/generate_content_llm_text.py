"""콘텐츠(열린데이터광장 + 팝플리) llm_text + tags 생성 스크립트

네이버 검색 API로 컨텍스트 수집 → OpenAI로 llm_text 생성 → tags 추출

- 문화행사: 네이버 블로그 검색
- 팝업스토어: 네이버 웹문서(webkr) 검색

대상: seoul_culture_문화행사, popply_팝업스토어
입력: data/preprocessed/{name}.json
출력: data/preprocessed/enrich/{name}_enrich.json

사용법:
    python -m app.scripts.enrich.generate_content_llm_text
    python -m app.scripts.enrich.generate_content_llm_text seoul_culture_문화행사
    python -m app.scripts.enrich.generate_content_llm_text popply_팝업스토어 --limit 3
"""

import json
import logging
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

log = logging.getLogger(__name__)

_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_PATH)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
PRE_DIR = DATA_DIR / "preprocessed"
OUT_DIR = DATA_DIR / "enrich"

NAVER_CLIENT_ID = os.getenv("NAVER_SEARCH_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET")
OPENAI_MODEL = "gpt-4o-mini"

TARGETS = ["seoul_culture_문화행사", "popply_팝업스토어"]

CRAWL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
_SKIP_DOMAINS = {"instagram.com", "twitter.com", "facebook.com", "youtube.com"}

_LLM_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U0001D400-\U0001D7FF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002B50"
    "\U0000203C-\U00002BFF"
    "]+",
    flags=re.UNICODE,
)


def _strip_llm_emoji(text: str) -> str:
    """LLM 생성 텍스트에서 이모지 제거."""
    text = _LLM_EMOJI_RE.sub("", text)
    return re.sub(r"  +", " ", text).strip()

TAGS_SYSTEM_PROMPT = (
    "주어진 소개글에서 검색에 유용한 핵심 키워드를 5~10개 추출하세요. "
    "행사명, 장소명, 지역명, 장르, 특징 등을 포함하세요. "
    "날짜, 기간, 요금, 주소는 키워드에 포함하지 마세요. "
    "JSON 배열 형식으로만 출력하세요. 예: [\"키워드1\", \"키워드2\"]"
)

PLACE_EXTRACT_PROMPT_POPUP = (
    "아래 팝업스토어 설명에서 팝업이 열리는 장소(건물/매장)의 이름만 추출하세요. "
    "주소, 층수, 번지는 제외하고 장소명만 출력하세요. "
    "장소명을 알 수 없으면 빈 문자열을 출력하세요. "
    "장소명만 출력하세요. 다른 설명 없이."
)

PLACE_EXTRACT_PROMPT_CULTURE = (
    "아래 문화행사의 장소 정보에서 네이버 지도에 검색 가능한 장소명만 추출하세요. "
    "홀 이름(B홀, 소나무홀 등), 층수, 부가 설명(※우천 시 등)은 제거하세요. "
    "여러 장소가 나열되어 있으면 대표 장소 1개만 출력하세요. "
    "장소명만 출력하세요. 다른 설명 없이."
)

# ─────────────────────── 공통 유틸 ───────────────────────


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    for ent, ch in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        text = text.replace(ent, ch)
    return text.strip()


def _clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    for ch in ["\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"]:
        text = text.replace(ch, " ")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[#*@_]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in re.findall(r"[A-Za-z0-9가-힣]+", text) if len(t) >= 2]


def _score_result(result: dict, title_tokens: list[str], addr_tokens: list[str]) -> float:
    text = f"{result['title']} {result['description']}".lower()
    score = 0.0
    for token in title_tokens:
        if token.lower() in text:
            score += 2.0
    for token in addr_tokens:
        if token.lower() in text:
            score += 0.5
    hashtag_ratio = text.count("#") / max(len(text.split()), 1)
    if hashtag_ratio > 0.3:
        score -= 1.5
    return score


# ─────────────────────── 네이버 검색 ───────────────────────


def _search_naver(query: str, search_type: str = "blog", display: int = 5) -> list[dict]:
    """네이버 블로그/웹문서 검색."""
    url = (
        "https://openapi.naver.com/v1/search/blog.json"
        if search_type == "blog"
        else "https://openapi.naver.com/v1/search/webkr.json"
    )
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    try:
        resp = requests.get(url, headers=headers, params={"query": query, "display": display, "sort": "sim"}, timeout=8)
        resp.raise_for_status()
        return [
            {
                "title": _clean_html(it.get("title", "")),
                "description": _clean_html(it.get("description", "")),
                "link": it.get("link", ""),
            }
            for it in resp.json().get("items", [])
        ]
    except Exception as e:
        log.warning("  [검색 오류] %s → %s", query[:40], e)
        return []


# ─────────────────────── 크롤링 ───────────────────────


def _to_mobile_blog_url(link: str) -> str:
    if "m.blog.naver.com" in link:
        return link
    parsed = urlparse(link)
    qs = parse_qs(parsed.query)
    if "blogId" in qs and "logNo" in qs:
        return f"https://m.blog.naver.com/{qs['blogId'][0]}/{qs['logNo'][0]}"
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 2:
        return f"https://m.blog.naver.com/{parts[0]}/{parts[1]}"
    return link


def _crawl_page(url: str, is_blog: bool = False, max_chars: int = 2000) -> str:
    domain = urlparse(url).netloc.lower()
    if any(d in domain for d in _SKIP_DOMAINS):
        return ""
    if is_blog:
        url = _to_mobile_blog_url(url)
    try:
        resp = requests.get(url, headers=CRAWL_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        selectors = ["div.se-main-container", "article", "div.content", "div.post-content", "main"]
        body = ""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                body = el.get_text(separator=" ", strip=True)
                break
        if not body:
            body = soup.get_text(separator=" ", strip=True)
        return _clean_text(body)[:max_chars]
    except Exception:
        return ""


# ─────────────────────── 문화행사 (블로그 검색) ───────────────────────

_CULTURE_QUERY_TEMPLATES = {
    "공연": ['"{title}" 공연 소개 줄거리', '"{title}" 공연 후기 리뷰', '"{title}" {place} 관람 후기'],
    "전시": ['"{title}" 전시 소개 관람', '"{title}" 전시 후기 리뷰', '"{title}" {place} 전시'],
    "축제": ['"{title}" 축제 소개 볼거리', '"{title}" 축제 후기 방문기', '"{title}" {place} 참여 후기'],
    "기타": ['"{title}" 소개 후기', '"{title}" {place} 관람 후기'],
}

_CULTURE_LLM_PROMPT = (
    "당신은 서울의 공연, 전시, 축제 콘텐츠를 소개하는 검색 최적화 설명문 작성 전문가입니다.\n"
    "이 설명은 VectorDB에 저장되어 사용자의 여행/문화생활 관련 질문에 대한 검색 결과로 활용됩니다.\n\n"
    "### 작성 규칙\n"
    "1. 필수 반영: 행사명, 카테고리, 장소, 주소, 기간을 모두 포함\n"
    "2. 내용 풍부화: 블로그 컨텍스트에서 줄거리, 출연진, 볼거리, 분위기, 관람 팁\n"
    "3. 검색 최적화: 데이트, 가족 나들이, 전시 추천 등 키워드 포함\n"
    "4. 자연스러운 한국어 산문체, 300~500자, URL/JSON 키 출력 금지\n"
    "5. 반드시 완결된 문장으로 끝내세요. 문장이 중간에 잘리면 안 됩니다\n"
    "6. 이모지는 사용하지 마세요"
)


def _get_culture_category(item: dict) -> str:
    cat = item.get("category_depth", "")
    if "전시" in cat or "미술" in cat:
        return "전시"
    if "축제" in cat:
        return "축제"
    if any(k in cat for k in ["공연", "연극", "뮤지컬", "콘서트", "클래식", "국악", "무용"]):
        return "공연"
    return "기타"


def _collect_culture_context(item: dict) -> str:
    title = item.get("title", "")
    place = item.get("place", "")
    addr = item.get("addr") or place or ""
    title_tokens = _tokenize(title)
    addr_tokens = _tokenize(addr)

    cat = _get_culture_category(item)
    templates = _CULTURE_QUERY_TEMPLATES.get(cat, _CULTURE_QUERY_TEMPLATES["기타"])
    queries = [t.format(title=title, place=place) for t in templates]

    all_results = []
    seen = set()
    for q in queries:
        for r in _search_naver(q, search_type="blog"):
            if r["link"] not in seen:
                seen.add(r["link"])
                r["score"] = _score_result(r, title_tokens, addr_tokens)
                all_results.append(r)
        time.sleep(0.3)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    parts = []
    for r in [r for r in all_results if r["score"] >= 1.5][:5]:
        if r["description"]:
            parts.append(f"[블로그 요약] {r['description']}")
    for r in [r for r in all_results if r["score"] >= 3.0][:2]:
        body = _crawl_page(r["link"], is_blog=True)
        if body and len(body) > 100:
            parts.append(f"[블로그 본문] {body}")
        time.sleep(0.5)
    return "\n\n".join(parts)


def _generate_culture_llm_text(client: OpenAI, item: dict, context: str) -> str:
    info = {
        "title": item.get("title", ""),
        "category": item.get("category_depth", ""),
        "place": item.get("place", ""),
        "addr": item.get("addr") or item.get("place", ""),
        "period": f"{item.get('STRTDATE', '')} ~ {item.get('END_DATE', '')}",
    }
    user_msg = (
        f"아래 콘텐츠 정보와 블로그 컨텍스트를 바탕으로 검색 최적화된 설명문을 작성해줘.\n\n"
        f"[콘텐츠 정보]\n{json.dumps(info, ensure_ascii=False, indent=2)}\n\n"
        f"[블로그 컨텍스트]\n{context[:3000] if context else '(수집된 블로그 내용 없음)'}"
    )
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": _CULTURE_LLM_PROMPT}, {"role": "user", "content": user_msg}],
            temperature=0.7, max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning("  [LLM 오류] %s: %s", item.get("title", ""), e)
        return ""


# ─────────────────────── 팝업스토어 (웹문서 검색) ───────────────────────

_STRIP_PATTERNS = [
    r"\s+(팝업스토어|팝업 스토어|POP-?UP STORE|팝업|POP-?UP)\b.*",
    r"\s+(IN|in)\s+\S+.*",
    r"\s+(롯데백화점|현대백화점|신세계|더현대|갤러리아|백화점)\b.*",
]
_COLLAB_RE = re.compile(r"\s+[Xx×]\s+")


def _extract_brand(title: str) -> str:
    brand = title.strip()
    for pat in _STRIP_PATTERNS:
        brand = re.sub(pat, "", brand, flags=re.IGNORECASE).strip()
    if _COLLAB_RE.search(brand):
        brand = _COLLAB_RE.split(brand)[0].strip()
    return brand or title.split()[0]


_POPUP_LLM_PROMPT = (
    "당신은 팝업스토어와 이벤트 콘텐츠를 소개하는 검색 최적화 설명문 작성 전문가입니다.\n"
    "이 설명은 VectorDB에 저장되어 사용자의 팝업스토어/이벤트 관련 질문에 대한 검색 결과로 활용됩니다.\n\n"
    "### 작성 규칙\n"
    "1. 필수 반영: 팝업명, 주소, 운영기간, 운영시간, 입장료\n"
    "2. 내용 풍부화: 웹 컨텍스트에서 굿즈/체험/이벤트, 분위기, 방문 팁\n"
    "3. 검색 최적화: 데이트, 주말 나들이, 굿즈, 팝업, 한정판 등 키워드 포함\n"
    "4. 자연스러운 한국어 산문체, 200~400자, URL/JSON 키 출력 금지\n"
    "5. 반드시 완결된 문장으로 끝내세요. 문장이 중간에 잘리면 안 됩니다\n"
    "6. 이모지는 사용하지 마세요"
)


def _collect_popup_context(item: dict) -> str:
    title = item.get("title", "")
    addr = item.get("addr", "")
    title_tokens = _tokenize(title)
    addr_tokens = _tokenize(addr)

    addr_token = ""
    m = re.search(r"(서울|부산|경기)\S*\s+(\S+구|\S+시)", addr)
    if m:
        addr_token = m.group(2)

    queries = [
        title,
        f"{_extract_brand(title)} 팝업 후기",
        f"{_extract_brand(title)} 팝업 {addr_token}".strip(),
    ]

    all_results = []
    seen = set()
    for q in queries:
        for r in _search_naver(q, search_type="webkr"):
            if r["link"] not in seen:
                seen.add(r["link"])
                r["score"] = _score_result(r, title_tokens, addr_tokens)
                all_results.append(r)
        time.sleep(0.3)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    parts = []
    for r in [r for r in all_results if r["score"] >= 1.5][:5]:
        if r["description"]:
            parts.append(f"[웹 요약] {r['description']}")
    for r in [r for r in all_results if r["score"] >= 3.0][:2]:
        body = _crawl_page(r["link"])
        if body and len(body) > 100:
            parts.append(f"[웹 본문] {body}")
        time.sleep(0.5)
    if not parts:
        for r in all_results[:3]:
            if r["description"]:
                parts.append(f"[웹 요약] {r['description']}")
    return "\n\n".join(parts)


def _generate_popup_llm_text(client: OpenAI, item: dict, context: str) -> str:
    info = {
        "title": item.get("title", ""),
        "addr": item.get("addr", ""),
        "usetime": item.get("usetime", ""),
        "startDate": item.get("startDate", ""),
        "endDate": item.get("endDate", ""),
        "fee": item.get("fee", ""),
    }
    user_msg = (
        f"아래 팝업스토어 정보와 웹 컨텍스트를 바탕으로 검색 최적화된 설명문을 작성해줘.\n\n"
        f"[팝업스토어 정보]\n{json.dumps(info, ensure_ascii=False, indent=2)}\n\n"
        f"[웹 컨텍스트]\n{context[:3000] if context else '(수집된 내용 없음)'}"
    )
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": _POPUP_LLM_PROMPT}, {"role": "user", "content": user_msg}],
            temperature=0.7, max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning("  [LLM 오류] %s: %s", item.get("title", ""), e)
        return ""


# ─────────────────────── llm_text 조립 ───────────────────────


def _build_llm_text(item: dict, intro: str, is_popup: bool = False) -> str:
    lines = []
    label = "팝업명" if is_popup else "행사명"
    if v := item.get("title"):
        lines.append(f"- {label}: {v}")
    if v := item.get("place"):
        lines.append(f"- 장소: {v}")
    if v := item.get("addr"):
        lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"):
        lines.append(f"- 카테고리: {v}")
    start = item.get("STRTDATE") or item.get("startDate")
    end = item.get("END_DATE") or item.get("endDate")
    if start:
        lines.append(f"- 기간: {start} ~ {end or ''}")
    if v := item.get("usetime"):
        lines.append(f"- 운영시간: {v}")
    if v := item.get("fee"):
        lines.append(f"- 요금: {v}")
    if intro:
        lines.append(f"- 소개: {intro}")
    return "\n".join(lines)


# ─────────────────────── 메인 처리 ───────────────────────


def process(name: str, limit: int | None = None):
    in_path = PRE_DIR / f"{name}.json"
    out_path = OUT_DIR / f"{name}_enrich.json"

    if not in_path.exists():
        log.warning("  파일 없음: %s", in_path.name)
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    if limit:
        data = data[:limit]

    if not data:
        log.warning("  %s: 데이터 없음", name)
        return

    is_popup = "popply" in name
    log.info("  %s: %d건 처리 시작", name, len(data))

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    results = []

    for idx, item in enumerate(data):
        title = item.get("title", "")
        log.info("  [%d/%d] %s", idx + 1, len(data), title)

        # 1. 네이버 검색 컨텍스트 수집
        if is_popup:
            context = _collect_popup_context(item)
        else:
            context = _collect_culture_context(item)
        log.info("    컨텍스트: %d자", len(context))

        # 2. LLM llm_text 생성
        if is_popup:
            intro = _generate_popup_llm_text(client, item, context)
        else:
            intro = _generate_culture_llm_text(client, item, context)

        new_item = dict(item)

        # 2-1. place 추출 (팝업: description에서, 문화행사: place 원본에서 정리)
        if is_popup and not item.get("place"):
            try:
                desc = item.get("description", "")
                resp = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": PLACE_EXTRACT_PROMPT_POPUP},
                        {"role": "user", "content": desc},
                    ],
                    max_tokens=50, temperature=0,
                )
                place = resp.choices[0].message.content.strip()
                if place:
                    new_item["place"] = place
                    log.info("    place 추출: %s", place)
            except Exception as e:
                log.warning("    place 추출 실패: %s", e)
        elif not is_popup and item.get("place"):
            try:
                resp = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": PLACE_EXTRACT_PROMPT_CULTURE},
                        {"role": "user", "content": item["place"]},
                    ],
                    max_tokens=50, temperature=0,
                )
                place = resp.choices[0].message.content.strip()
                if place and place != item["place"]:
                    log.info("    place 보정: %s → %s", item["place"][:30], place)
                    new_item["place"] = place
            except Exception as e:
                log.warning("    place 보정 실패: %s", e)

        new_item["llm_text"] = _strip_llm_emoji(_build_llm_text(new_item, intro, is_popup))
        log.info("    llm_text: %d자", len(new_item["llm_text"]))

        # 3. tags 생성
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": TAGS_SYSTEM_PROMPT},
                    {"role": "user", "content": new_item["llm_text"]},
                ],
                max_tokens=100, temperature=0.3,
            )
            raw_tags = resp.choices[0].message.content.strip()
            raw_tags = re.sub(r"^```(?:json)?\s*", "", raw_tags)
            raw_tags = re.sub(r"\s*```$", "", raw_tags)
            tags = json.loads(raw_tags)
            new_item["tags"] = [t for t in tags if isinstance(t, str)] if isinstance(tags, list) else []
        except Exception:
            new_item["tags"] = []

        results.append(new_item)

        # 10건마다 중간 저장
        if (idx + 1) % 10 == 0:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            log.info("    [중간저장] %d건", idx + 1)

        time.sleep(0.5)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log.info("  저장 완료 → %s (%d건)", out_path.name, len(results))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    limit = None
    targets = []
    for arg in sys.argv[1:]:
        if arg == "--limit" or arg.startswith("--limit="):
            continue
        targets.append(arg)
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    if not targets:
        targets = TARGETS

    log.info("콘텐츠 llm_text + tags 생성 (네이버 검색 + GPT-4o-mini)")
    log.info("대상: %s", ", ".join(targets))

    for name in targets:
        log.info("── %s ──", name)
        process(name, limit=limit)

    log.info("완료")


if __name__ == "__main__":
    main()
