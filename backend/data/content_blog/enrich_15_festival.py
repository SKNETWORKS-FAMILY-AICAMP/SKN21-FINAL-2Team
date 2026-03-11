"""
15_축제공연행사 llm_text 재생성 스크립트 (C안: 하이브리드)

[전략]
1. 콘텐츠당 다중 쿼리로 네이버 블로그 검색 (API description 활용)
2. description으로 관련성 점수 계산 → 관련 있는 상위 결과 선별
3. 선별된 상위 1~2개 결과 → 블로그 본문 크롤링
4. 수집된 컨텍스트(description + 본문) → OpenAI LLM으로 llm_text 생성
5. 결과를 JSONL에 업데이트하여 저장

[파일 위치]
- 스크립트: data/content_blog/enrich_15_festival.py
- 입력: data/image_add/15_축제공연행사_image_add.jsonl
- 출력: data/content_blog/15_축제공연행사_enriched.jsonl

[실행 방법]
cd backend
../.venv/bin/python data/content_blog/enrich_15_festival.py
또는 (테스트 시) -- limit 옵션 추가
../.venv/bin/python data/content_blog/enrich_15_festival.py --limit 3
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
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# ─────────────────────── 환경 설정 ───────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_SCRIPT_DIR))  # data/ -> backend/
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")
load_dotenv(_ENV_PATH, override=True)

NAVER_CLIENT_ID = os.getenv("NAVER_SEARCH_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"
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
    """HTML 태그 및 엔티티 제거"""
    text = re.sub(r"<[^>]+>", "", text)
    for ent, ch in [("&amp;","&"),("&lt;","<"),("&gt;",">"),
                    ("&quot;",'"'),("&#39;","'"),("&nbsp;"," ")]:
        text = text.replace(ent, ch)
    return text.strip()


def clean_text(text: str) -> str:
    """크롤링된 텍스트 정제"""
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
    """간단 토큰화"""
    if not text:
        return []
    return [t for t in re.findall(r"[A-Za-z0-9가-힣]+", text) if len(t) >= 2]


# ─────────────────────── 쿼리 생성 ───────────────────────

QUERY_TEMPLATES = {
    "공연": [
        '"{title}" {category} 소개 줄거리',
        '"{title}" {category} 후기 리뷰 관람',
        '"{title}" {place} 관람 후기 꿀팁',
    ],
    "전시": [
        '"{title}" 전시 소개 관람 정보',
        '"{title}" 전시 후기 리뷰',
        '"{title}" {place} 전시 관람',
    ],
    "축제": [
        '"{title}" 축제 소개 볼거리',
        '"{title}" 축제 후기 방문기',
        '"{title}" {place} 참여 후기',
    ],
    "기타": [
        '"{title}" 소개 후기',
        '"{title}" {place} 관람 후기',
    ],
}

def build_queries(item: dict) -> list[str]:
    """카테고리별 다중 검색 쿼리 생성"""
    category = item.get("category", "기타")
    title = item.get("title", "")
    place = item.get("place", "")
    templates = QUERY_TEMPLATES.get(category, QUERY_TEMPLATES["기타"])
    queries = []
    for tpl in templates:
        q = tpl.format(title=title, category=category, place=place)
        queries.append(q)
    return queries


# ─────────────────────── 네이버 블로그 검색 ───────────────────────

def search_blog(query: str, display: int = 5) -> list[dict]:
    """네이버 블로그 검색 API 호출"""
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "sort": "sim"}
    try:
        resp = requests.get(BLOG_SEARCH_URL, headers=headers, params=params, timeout=8)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            {
                "title": clean_html(item.get("title", "")),
                "description": clean_html(item.get("description", "")),
                "link": item.get("link", ""),
                "postdate": item.get("postdate", ""),
            }
            for item in items
        ]
    except Exception as e:
        print(f"  [검색 오류] {query[:40]}... → {e}")
        return []


# ─────────────────────── 관련성 스코어링 ───────────────────────

def score_result(result: dict, title_tokens: list[str], addr_tokens: list[str]) -> float:
    """description 기반 관련성 점수 계산"""
    text = f"{result['title']} {result['description']}".lower()
    score = 0.0
    # 제목 토큰 매칭 (높은 가중치)
    for token in title_tokens:
        if token.lower() in text:
            score += 2.0
    # 주소 토큰 매칭
    for token in addr_tokens:
        if token.lower() in text:
            score += 0.5
    # 해시태그만 있는 노이즈 감점
    hashtag_ratio = text.count("#") / max(len(text.split()), 1)
    if hashtag_ratio > 0.3:
        score -= 1.5
    return score


# ─────────────────────── 블로그 크롤링 ───────────────────────

def to_mobile_url(link: str) -> str:
    """blog.naver.com 링크 → 모바일 URL 변환"""
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


def crawl_blog_body(url: str, max_chars: int = 2000) -> str:
    """모바일 블로그 URL에서 본문 추출"""
    mobile_url = to_mobile_url(url)
    try:
        resp = requests.get(mobile_url, headers=CRAWL_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        selectors = [
            "div.se-main-container",
            "div#viewTypeSelector",
            "div.post-view",
            "div#postViewArea",
            "div.se_component_wrap",
        ]
        body = ""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                body = el.get_text(separator=" ", strip=True)
                break
        if not body:
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            body = soup.get_text(separator=" ", strip=True)

        body = clean_text(body)
        return body[:max_chars]
    except Exception as e:
        return ""


# ─────────────────────── 컨텍스트 수집 ───────────────────────

def collect_context(item: dict) -> str:
    """다중 쿼리 검색 → 스코어링 → 하이브리드 컨텍스트 생성"""
    title = item.get("title", "")
    addr = item.get("addr", "")
    title_tokens = tokenize(title)
    addr_tokens = tokenize(addr)

    queries = build_queries(item)
    all_results = []
    seen_links = set()

    for query in queries:
        results = search_blog(query, display=5)
        for r in results:
            if r["link"] not in seen_links:
                seen_links.add(r["link"])
                r["score"] = score_result(r, title_tokens, addr_tokens)
                all_results.append(r)
        time.sleep(0.3)  # rate limit

    # 점수 기준 정렬
    all_results.sort(key=lambda x: x["score"], reverse=True)

    if not all_results:
        return ""

    context_parts = []

    # 관련성 높은 상위 3개는 description 사용
    top_desc = [r for r in all_results if r["score"] >= 1.5][:5]
    for r in top_desc:
        if r["description"]:
            context_parts.append(f"[블로그 요약] {r['description']}")

    # 관련성 상위 1~2개는 본문 크롤링
    top_crawl = [r for r in all_results if r["score"] >= 3.0][:2]
    for r in top_crawl:
        print(f"    크롤링 중: {r['link'][:60]}...")
        body = crawl_blog_body(r["link"])
        if body and len(body) > 100:
            context_parts.append(f"[블로그 본문] {body}")
        time.sleep(0.5)

    return "\n\n".join(context_parts)


# ─────────────────────── LLM llm_text 생성 ───────────────────────

LLM_SYSTEM_PROMPT = """
당신은 서울의 공연, 전시, 축제 콘텐츠를 소개하는 검색 최적화 설명문 작성 전문가입니다.
이 설명은 VectorDB(Qdrant)에 저장되어 사용자의 여행/문화생활 관련 질문에 대한 검색 결과로 활용됩니다.

### 작성 규칙
1. **필수 반영**: 공연명(title), 카테고리(category), 공연장소(place), 주소(addr), 공연기간(period)을 모두 포함하세요.
2. **내용 풍부화**: 제공된 [블로그 컨텍스트]에서 줄거리, 출연진, 볼거리, 분위기, 관람 팁 등을 자연스럽게 녹여내세요.
3. **검색 최적화**: 사용자가 검색할 법한 키워드(데이트, 가족 나들이, 클래식, 뮤지컬, 전시 추천 등)를 포함하세요.
4. **형식 제약**: 
   - 자연스러운 한국어 산문체로 작성 (목록/표/코드 금지)
   - URL, JSON 키, 메타 정보 출력 금지
   - 300~500자 내외
   - "이곳은~", "저곳은~" 같은 진부한 시작 지양
""".strip()


def generate_llm_text(item: dict, context: str) -> str:
    """OpenAI API로 llm_text 생성"""
    item_summary = {
        "title": item.get("title", ""),
        "category": item.get("category", ""),
        "place": item.get("place", ""),
        "addr": item.get("addr", ""),
        "period": item.get("period", ""),
    }

    user_msg = (
        f"아래 콘텐츠 정보와 블로그 컨텍스트를 바탕으로 검색 최적화된 설명문을 작성해줘.\n\n"
        f"[콘텐츠 정보]\n{json.dumps(item_summary, ensure_ascii=False, indent=2)}\n\n"
        f"[블로그 컨텍스트]\n{context[:3000] if context else '(수집된 블로그 내용 없음)'}"
    )

    try:
        resp = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [LLM 오류] {item.get('title','')} → {e}")
        return ""


# ─────────────────────── 메인 실행 ───────────────────────

def main():
    parser = argparse.ArgumentParser(description="축제공연행사 llm_text 재생성 스크립트")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 콘텐츠 수 (테스트용)")
    parser.add_argument("--start", type=int, default=0, help="시작 인덱스 (재시작 시 사용)")
    args = parser.parse_args()

    input_path = os.path.join(
        _BACKEND_DIR, "data", "image_add", "15_축제공연행사_image_add.jsonl"
    )
    output_path = os.path.join(
        _SCRIPT_DIR, "15_축제공연행사_enriched.jsonl"
    )
    log_path = os.path.join(
        _SCRIPT_DIR, f"enrich_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    with open(input_path, "r", encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    total = len(all_items)
    print(f"[INFO] 총 {total}개 콘텐츠 로드 완료")
    print(f"[INFO] 출력 경로: {output_path}")
    if args.limit:
        print(f"[INFO] 테스트 모드: 최대 {args.limit}개 처리")

    results = []
    log_lines = []

    for idx, item in enumerate(all_items):
        if idx < args.start:
            results.append(item)
            continue
        if args.limit is not None and (idx - args.start) >= args.limit:
            # 나머지는 원본 그대로
            results.extend(all_items[idx:])
            break

        title = item.get("title", "")
        category = item.get("category", "")
        print(f"\n[{idx+1}/{total}] {title} ({category})")

        # 1. 컨텍스트 수집
        context = collect_context(item)
        context_len = len(context)
        print(f"  컨텍스트 수집: {context_len}자")

        # 2. llm_text 생성
        llm_text = generate_llm_text(item, context)
        item["llm_text"] = llm_text
        results.append(item)

        log_line = f"[{idx+1}] {title} | context={context_len}자 | llm_text={len(llm_text)}자"
        log_lines.append(log_line)
        print(f"  llm_text 생성: {len(llm_text)}자")
        if llm_text:
            print(f"  미리보기: {llm_text[:100]}...")

        # 중간 저장 (10개마다)
        if (idx + 1) % 10 == 0:
            _save_jsonl(results, output_path)
            print(f"  [중간저장] {idx+1}개 저장 완료")

        time.sleep(0.5)

    # 최종 저장
    _save_jsonl(results, output_path)

    # 로그 저장
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"\n[완료] 결과 저장: {output_path}")
    print(f"[완료] 로그 저장: {log_path}")


def _save_jsonl(items: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
