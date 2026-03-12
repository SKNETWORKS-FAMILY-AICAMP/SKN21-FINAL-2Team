"""
99_팝업스토어 llm_text 재생성 스크립트 (하이브리드)

[전략]
1. 콘텐츠 title 기반 쿼리로 네이버 웹문서(webkr) 검색
2. description 여러 개를 관련성 스코어링으로 필터링
3. 관련도 높은 상위 1~2개 URL 크롤링 (본문 수집)
4. description + 본문 조합 컨텍스트 → OpenAI LLM으로 llm_text 생성
5. 결과를 JSONL에 업데이트하여 저장

[파일 위치]
- 스크립트: data/content_blog/enrich_99_popup.py
- 입력:     data/llm_result/99_팝업스토어_enriched.jsonl
- 출력:     data/content_blog/99_팝업스토어_enriched.jsonl

[실행 방법]
cd backend
../.venv/bin/python data/content_blog/enrich_99_popup.py
../.venv/bin/python data/content_blog/enrich_99_popup.py --limit 3  # 테스트
"""

import os
import re
import sys
import json
import time
import argparse
import unicodedata
import requests
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# ─────────────────────── 환경 설정 ───────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_SCRIPT_DIR))  # content_blog/ -> data/ -> backend/
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")
load_dotenv(_ENV_PATH, override=True)

NAVER_CLIENT_ID     = os.getenv("NAVER_SEARCH_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")

WEBKR_SEARCH_URL = "https://openapi.naver.com/v1/search/webkr.json"
CRAWL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
OPENAI_MODEL = "gpt-4o-mini"

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ─────────────────────── 유틸 함수 ───────────────────────

def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    for ent, ch in [("&amp;","&"),("&lt;","<"),("&gt;",">"),
                    ("&quot;",'"'),("&#39;","'"),("&nbsp;"," ")]:
        text = text.replace(ent, ch)
    return text.strip()


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    for ch in ["\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"]:
        text = text.replace(ch, " ")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)
    text = re.sub(r"\S+\.(jpg|png|jpeg|gif|bmp)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[#*@_]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in re.findall(r"[A-Za-z0-9가-힣]+", text) if len(t) >= 2]


# ─────────────────────── 브랜드명 추출 ───────────────────────

# title에서 장소·형식 노이즈를 제거해 핵심 브랜드명(검색 키워드)만 추출
_STRIP_PATTERNS = [
    r"\s+(팝업스토어|팝업 스토어|POP-?UP STORE|팝업|POP-?UP)\b.*",
    r"\s+(IN|in)\s+\S+.*",
    r"\s+(롯데백화점|현대백화점|신세계|더현대|갤러리아|백화점|아트센터|몰|마트)\b.*",
]
_COLLAB_RE = re.compile(r"\s+[Xx×]\s+")

def extract_brand(title: str) -> str:
    brand = title.strip()
    for pat in _STRIP_PATTERNS:
        brand = re.sub(pat, "", brand, flags=re.IGNORECASE).strip()
    # "A X B" 형태는 앞쪽 브랜드만 사용
    if _COLLAB_RE.search(brand):
        brand = _COLLAB_RE.split(brand)[0].strip()
    return brand or title.split()[0]


# ─────────────────────── 쿼리 생성 ───────────────────────

def build_queries(item: dict) -> list[str]:
    """팝업스토어용 검색 쿼리 3개 생성"""
    title = item.get("title", "")
    addr  = item.get("addr", "")

    # 주소에서 지역명 추출 (예: "서울특별시 성동구" → "성수" 등은 생략, 구명 사용)
    addr_token = ""
    m = re.search(r"(서울|부산|경기|세종)\S*\s+(\S+구|\S+시)", addr)
    if m:
        addr_token = m.group(2)  # 예: "성동구", "송파구"

    return [
        f"{title}",                              # 제목 그대로 (웹문서 상단에 공식 팝업 소개 페이지)
        f"{extract_brand(title)} 팝업 후기",       # 브랜드명 + 후기
        f"{extract_brand(title)} 팝업 {addr_token}".strip(),  # 브랜드명 + 지역
    ]


# ─────────────────────── 네이버 웹문서 검색 ───────────────────────

def search_webkr(query: str, display: int = 5) -> list[dict]:
    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "sort": "sim"}
    try:
        resp = requests.get(WEBKR_SEARCH_URL, headers=headers, params=params, timeout=8)
        resp.raise_for_status()
        return [
            {
                "title":       clean_html(it.get("title", "")),
                "description": clean_html(it.get("description", "")),
                "link":        it.get("link", ""),
            }
            for it in resp.json().get("items", [])
        ]
    except Exception as e:
        print(f"  [검색 오류] {query[:40]}... → {e}")
        return []


# ─────────────────────── 관련성 스코어링 ───────────────────────

def score_result(result: dict, title_tokens: list[str], addr_tokens: list[str]) -> float:
    text = f"{result['title']} {result['description']}".lower()
    score = 0.0
    for token in title_tokens:
        if token.lower() in text:
            score += 2.0
    for token in addr_tokens:
        if token.lower() in text:
            score += 0.5
    # 해시태그 노이즈 감점
    hashtag_ratio = text.count("#") / max(len(text.split()), 1)
    if hashtag_ratio > 0.3:
        score -= 1.5
    return score


# ─────────────────────── 웹페이지 크롤링 ───────────────────────

# 크롤링 제외 도메인 (로그인 필요 or 파싱 불가)
_SKIP_DOMAINS = {"instagram.com", "twitter.com", "facebook.com", "youtube.com"}

def is_crawlable(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        return not any(d in domain for d in _SKIP_DOMAINS)
    except:
        return False


def crawl_page(url: str, max_chars: int = 2000) -> str:
    if not is_crawlable(url):
        return ""
    try:
        resp = requests.get(url, headers=CRAWL_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # 본문 후보 셀렉터 순서대로 시도
        selectors = [
            "div.se-main-container",  # 네이버 블로그
            "article",
            "div.content",
            "div.post-content",
            "div#content",
            "main",
        ]
        body = ""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                body = el.get_text(separator=" ", strip=True)
                break
        if not body:
            body = soup.get_text(separator=" ", strip=True)

        body = clean_text(body)
        return body[:max_chars]
    except Exception as e:
        return ""


# ─────────────────────── 컨텍스트 수집 (하이브리드) ───────────────────────

def collect_context(item: dict) -> str:
    """다중 쿼리 웹문서 검색 → 스코어링 → description + 크롤링 조합"""
    title       = item.get("title", "")
    addr        = item.get("addr", "")
    title_tokens = tokenize(title)
    addr_tokens  = tokenize(addr)

    queries = build_queries(item)
    all_results: list[dict] = []
    seen_links: set[str] = set()

    for query in queries:
        results = search_webkr(query, display=5)
        for r in results:
            if r["link"] not in seen_links:
                seen_links.add(r["link"])
                r["score"] = score_result(r, title_tokens, addr_tokens)
                all_results.append(r)
        time.sleep(0.3)

    if not all_results:
        return ""

    all_results.sort(key=lambda x: x["score"], reverse=True)

    context_parts: list[str] = []

    # 관련도 높은 상위 결과 description 수집 (score >= 1.5)
    top_desc = [r for r in all_results if r["score"] >= 1.5][:5]
    for r in top_desc:
        if r["description"]:
            context_parts.append(f"[웹 요약] {r['description']}")

    # 관련도 상위 1~2개 URL 크롤링 (score >= 3.0)
    top_crawl = [r for r in all_results if r["score"] >= 3.0][:2]
    for r in top_crawl:
        if not is_crawlable(r["link"]):
            continue
        print(f"    크롤링 중: {r['link'][:70]}...")
        body = crawl_page(r["link"])
        if body and len(body) > 100:
            context_parts.append(f"[웹 본문] {body}")
        time.sleep(0.5)

    # description만이라도 있으면 상위 3개 추가 (score 무관)
    if not context_parts:
        for r in all_results[:3]:
            if r["description"]:
                context_parts.append(f"[웹 요약] {r['description']}")

    return "\n\n".join(context_parts)


# ─────────────────────── LLM llm_text 생성 ───────────────────────

LLM_SYSTEM_PROMPT = """
당신은 팝업스토어와 이벤트 콘텐츠를 소개하는 검색 최적화 설명문 작성 전문가입니다.
이 설명은 VectorDB(Qdrant)에 저장되어 사용자의 팝업스토어/이벤트 관련 질문에 대한 검색 결과로 활용됩니다.

### 작성 규칙
1. **필수 반영**: 팝업명(title), 주소(addr), 운영기간(start_date~end_date), 운영시간(usetime), 입장료(fee)을 모두 포함하세요.
2. **내용 풍부화**: 제공된 [웹 컨텍스트]에서 어떤 굿즈/체험/이벤트가 있는지, 분위기, 방문 팁 등을 자연스럽게 녹여내세요.
3. **검색 최적화**: 사용자가 검색할 법한 키워드(데이트, 주말 나들이, 굿즈, 팝업, 한정판, 성수 팝업 등)를 포함하세요.
4. **형식 제약**:
   - 자연스러운 한국어 산문체로 작성 (목록/표/코드 금지)
   - URL, JSON 키, 메타 정보 출력 금지
   - 200~400자 내외
   - "이곳은~", "저곳은~" 같은 진부한 시작 지양
""".strip()


def generate_llm_text(item: dict, context: str) -> str:
    item_summary = {
        "title":      item.get("title", ""),
        "addr":       item.get("addr", ""),
        "usetime":    item.get("usetime", ""),
        "start_date": item.get("start_date", ""),
        "end_date":   item.get("end_date", ""),
        "fee":        item.get("fee", ""),
    }

    user_msg = (
        f"아래 팝업스토어 정보와 웹 컨텍스트를 바탕으로 검색 최적화된 설명문을 작성해줘.\n\n"
        f"[팝업스토어 정보]\n{json.dumps(item_summary, ensure_ascii=False, indent=2)}\n\n"
        f"[웹 컨텍스트]\n{context[:3000] if context else '(수집된 내용 없음)'}"
    )

    try:
        resp = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [LLM 오류] {item.get('title','')} → {e}")
        return ""


# ─────────────────────── 메인 실행 ───────────────────────

def _save_jsonl(items: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="팝업스토어 llm_text 재생성 스크립트")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 개수 (테스트용)")
    parser.add_argument("--start", type=int, default=0,    help="시작 인덱스 (재시작 시 사용)")
    args = parser.parse_args()

    _DATA_DIR   = os.path.join(_BACKEND_DIR, "data")
    input_path  = os.path.join(_DATA_DIR, "llm_result", "99_팝업스토어_enriched.jsonl")
    output_path = os.path.join(_SCRIPT_DIR, "99_팝업스토어_enriched.jsonl")
    log_path    = os.path.join(_SCRIPT_DIR, f"enrich_popup_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

    with open(input_path, "r", encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    total = len(all_items)
    print(f"[INFO] 총 {total}개 팝업스토어 로드 완료")
    print(f"[INFO] 출력 경로: {output_path}")
    if args.limit:
        print(f"[INFO] 테스트 모드: 최대 {args.limit}개 처리")

    results:   list[dict] = []
    log_lines: list[str]  = []

    for idx, item in enumerate(all_items):
        if idx < args.start:
            results.append(item)
            continue
        if args.limit is not None and (idx - args.start) >= args.limit:
            results.extend(all_items[idx:])
            break

        title = item.get("title", "")
        print(f"\n[{idx+1}/{total}] {title}")

        # 1. 컨텍스트 수집
        context     = collect_context(item)
        context_len = len(context)
        print(f"  컨텍스트 수집: {context_len}자")

        # 2. llm_text 생성
        llm_text         = generate_llm_text(item, context)
        item["llm_text"] = llm_text
        results.append(item)

        log_lines.append(f"[{idx+1}] {title} | context={context_len}자 | llm_text={len(llm_text)}자")
        print(f"  llm_text 생성: {len(llm_text)}자")
        if llm_text:
            print(f"  미리보기: {llm_text[:100]}...")

        # 10개마다 중간 저장
        if (idx + 1) % 10 == 0:
            _save_jsonl(results, output_path)
            print(f"  [중간저장] {idx+1}개 저장 완료")

        time.sleep(0.5)

    # 최종 저장
    _save_jsonl(results, output_path)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"\n[완료] 결과 저장: {output_path}")
    print(f"[완료] 로그 저장: {log_path}")


if __name__ == "__main__":
    main()
