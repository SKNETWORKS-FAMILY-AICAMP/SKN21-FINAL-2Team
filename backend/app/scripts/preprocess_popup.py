"""
팝업스토어 원시 데이터를 벡터 DB 적재용 enriched JSONL로 변환하는 전처리 스크립트.

실행:
    python backend/data/preprocess_popup.py

단계:
    1단계: 필터링 및 필드 정규화 → step1_normalized.json
    2단계: 값 정제             → step2_cleaned.json
    3단계: Geocoding          → step3_geocoded.json
    4단계: llm_text 생성      → step4_llm.json
    5단계: 최종 JSONL 저장    → llm_result/99_팝업스토어_enriched.jsonl
"""

import json
import re
import sys
import os
import time
import unicodedata
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR = Path(__file__).resolve().parent                 # backend/data/
STEP_DIR = DATA_DIR / "preprocess_steps"
LLM_DIR  = DATA_DIR / "llm_result"

STEP_DIR.mkdir(exist_ok=True)
LLM_DIR.mkdir(exist_ok=True)

# sys.path에 backend 루트 추가 (GeoCoder 임포트용)
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# OpenAI 클라이언트 (4단계에서 사용)
from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# GeoCoder (3단계에서 사용)
from app.utils.geocoder import GeoCoder

# ── 상수 ────────────────────────────────────────────────────────────────────────
TODAY = datetime.today().date()              # 기간 만료 기준일 (실행 시점 날짜)
CONTENTID_START = 9000001                    # 9로 시작하는 7자리, 순번 증가
RAW_FILE = DATA_DIR / "99_팝업스토어.json"

# 네이버 검색 API
NAVER_CLIENT_ID     = os.getenv("NAVER_SEARCH_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET")
NAVER_WEBKR_URL     = "https://openapi.naver.com/v1/search/webkr.json"
CRAWL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# ──────────────────────────────────────────────────────────────────────────────
# 유틸 함수
# ──────────────────────────────────────────────────────────────────────────────

def save_step(data: list, filename: str) -> None:
    """중간 결과 파일 저장"""
    path = STEP_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[저장] {path} ({len(data)}건)")


def parse_schedule(schedule: str) -> tuple[str | None, str | None]:
    """
    '2026-01-09T00:00:00 ~ 2026-03-31T00:00:00' → ('2026-01-09', '2026-03-31')
    파싱 실패 시 (None, None) 반환
    """
    try:
        parts = schedule.split("~")
        start = datetime.fromisoformat(parts[0].strip()).strftime("%Y-%m-%d")
        end   = datetime.fromisoformat(parts[1].strip()).strftime("%Y-%m-%d")
        return start, end
    except Exception:
        return None, None


def clean_text(text: str) -> str:
    """introduction 텍스트 정제: 이모지, HTML 태그, 과도한 빈 줄 제거"""
    if not text:
        return text
    # HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)
    # 이모지 및 특수 유니코드 제거
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"   # Emoticons
        "\U0001F300-\U0001F5FF"   # Misc Symbols & Pictographs
        "\U0001F680-\U0001F6FF"   # Transport & Map
        "\U0001F700-\U0001F77F"   # Alchemical Symbols
        "\U0001F780-\U0001F7FF"   # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"   # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"   # Supplemental Symbols & Pictographs
        "\U0001FA00-\U0001FA6F"   # Chess Symbols
        "\U0001FA70-\U0001FAFF"   # Symbols and Pictographs Extended-A
        "\U0001D400-\U0001D7FF"   # 수식 유니코드 폰트 (𝑪, 𝐒, 𝗩 등)
        "\U00002300-\U000023FF"   # Misc Technical (⏰ 포함)
        "\U00002600-\U000026FF"   # Misc Symbols
        "\U00002700-\U000027BF"   # Dingbats
        "\U0001F1E0-\U0001F1FF"   # Flags
        "\uFE00-\uFE0F"           # Variation Selectors (️)
        "\uFE10-\uFE1F"           # Vertical Forms
        "\u2000-\u206F"           # General Punctuation (특수 공백 등)
        "\u20D0-\u20FF"           # Combining Diacritical Marks for Symbols
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    # 원문자 목록 기호 제거 (①②③ 등)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", text)
    # 유니코드 장식 꺾쇠(⟪⟫〈〉《》) 등 특수 괄호 정리 (필요 시 일반 괄호로 대체)
    text = re.sub(r"[⟪⟫〈〉《》「」『』【】〔〕]", "", text)
    # 과도한 연속 공백/줄바꿈 축소
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ──────────────────────────────────────────────────────────────────────────────
# 1단계: 필터링 및 필드 정규화
# ──────────────────────────────────────────────────────────────────────────────

def step1_normalize(raw: list) -> list:
    print("\n[1단계] 필터링 및 필드 정규화 시작")
    result = []
    contentid = CONTENTID_START

    for item in raw:
        # schedule 파싱
        start_date, end_date = parse_schedule(item.get("schedule", ""))

        # 기간 만료 팝업 제외 (종료일이 오늘 이전)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            if end_dt < TODAY:
                print(f"  [제외] '{item.get('name')}' (종료: {end_date})")
                continue

        record = {
            "contentid"       : str(contentid),
            "title"           : item.get("name", "").strip(),
            "contenttypeid"   : "팝업스토어",
            "contenttypeid_code": "99",
            "image"           : item.get("thumbnail", "").strip() or None,
            "addr"            : item.get("location", "").strip() or None,
            "usetime"         : item.get("hours", "").strip() or None,
            "start_date"      : start_date,
            "end_date"        : end_date,
            "restdate"        : "",
            "introduction"    : item.get("introduction", "").strip() or None,
        }

        # Unknown이 아닌 경우만 추가
        for field in ("parking", "fee"):
            val = item.get(field, "Unknown")
            if val and val != "Unknown":
                record[field] = val.strip()

        # None 값 키 제거
        record = {k: v for k, v in record.items() if v is not None}

        result.append(record)
        contentid += 1

    print(f"  원본 {len(raw)}건 → 정규화 후 {len(result)}건 (만료 {len(raw)-len(result)}건 제외)")
    save_step(result, "step1_normalized.json")
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 2단계: 값 정제
# ──────────────────────────────────────────────────────────────────────────────

def step2_clean(data: list) -> list:
    print("\n[2단계] 값 정제 시작")

    # contentid 중복 검사
    ids = [item["contentid"] for item in data]
    if len(ids) != len(set(ids)):
        raise ValueError("[오류] contentid 중복 발생!")

    result = []
    for item in data:
        cleaned = dict(item)
        if "introduction" in cleaned:
            cleaned["introduction"] = clean_text(cleaned["introduction"])
            if not cleaned["introduction"]:
                del cleaned["introduction"]
        # 잔여 Unknown 제거
        cleaned = {k: v for k, v in cleaned.items() if v != "Unknown"}
        result.append(cleaned)

    print(f"  정제 완료: {len(result)}건")
    save_step(result, "step2_cleaned.json")
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 3단계: Geocoding
# ──────────────────────────────────────────────────────────────────────────────

def step3_geocode(data: list) -> list:
    print("\n[3단계] Geocoding 시작")
    geocoder = GeoCoder()
    result = []
    failed = 0

    for i, item in enumerate(data):
        addr = item.get("addr", "")
        geocoded = dict(item)

        if addr:
            geo = geocoder.geocoder(addr)
            if geo:
                geocoded["mapy"] = str(geo["lat"])
                geocoded["mapx"] = str(geo["lng"])
                if geo.get("road_address"):
                    geocoded["road_address"] = geo["road_address"]
                if geo.get("jibun_address"):
                    geocoded["old_address"] = geo["jibun_address"]
                print(f"  [{i+1}/{len(data)}] ✓ '{item['title']}' → ({geo['lat']}, {geo['lng']})")
            else:
                failed += 1
                print(f"  [{i+1}/{len(data)}] ✗ Geocoding 실패: '{item['title']}'")
        else:
            failed += 1
            print(f"  [{i+1}/{len(data)}] ✗ 주소 없음: '{item['title']}'")

        result.append(geocoded)
        time.sleep(0.1)  # API 요청 간격

    print(f"  완료: 성공 {len(data)-failed}건, 실패 {failed}건")
    save_step(result, "step3_geocoded.json")
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 4단계: llm_text 생성 (네이버 웹문서 검색 + 크롤링 + introduction → GPT-4o-mini)
# ──────────────────────────────────────────────────────────────────────────────

LLM_SYSTEM_PROMPT = """
당신은 한국 팝업스토어 정보를 검색 최적화된 설명문으로 변환하는 전문가입니다.
이 설명문은 VectorDB에 저장되어 사용자의 팝업스토어 관련 질문에 대한 검색 결과로 활용됩니다.

### 작성 규칙
1. **필수 반영**: 팝업스토어명, 위치(addr), 운영기간을 반드시 포함하세요.
2. **내용 풍부화**: 제공된 [팝플리 소개] 및 [웹 컨텍스트]에서 콘셉트, 전시 구성, 굿즈, 체험 요소 등을 자연스럽게 녹여내세요.
3. **검색 최적화**: 사용자가 검색할 법한 키워드(데이트 코스, 팝업 추천, 한정판 굿즈 등)를 포함하세요.
4. **형식 제약**:
   - 자연스러운 한국어 산문체로 작성 (목록/표/이모지 금지)
   - 300~500자 내외
   - 마케팅 과장 표현 최소화
""".strip()


# ── 네이버 웹문서 검색 유틸 ────────────────────────────────────────────────────

def _clean_html(text: str) -> str:
    """HTML 태그 및 엔티티 제거"""
    text = re.sub(r"<[^>]+>", "", text)
    for ent, ch in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        text = text.replace(ent, ch)
    return text.strip()


def _clean_crawled(text: str) -> str:
    """크롤링 텍스트 정제"""
    text = unicodedata.normalize("NFC", text)
    for ch in ["\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"]:
        text = text.replace(ch, " ")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> list[str]:
    """간단 토큰화 (2자 이상)"""
    return [t for t in re.findall(r"[A-Za-z0-9가-힣]+", text or "") if len(t) >= 2]


def _search_web(query: str, display: int = 5) -> list[dict]:
    """네이버 웹문서 검색 API 호출"""
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "sort": "sim"}
    try:
        resp = requests.get(NAVER_WEBKR_URL, headers=headers, params=params, timeout=8)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            {
                "title": _clean_html(it.get("title", "")),
                "description": _clean_html(it.get("description", "")),
                "link": it.get("link", ""),
            }
            for it in items
        ]
    except Exception as e:
        print(f"    [웹문서 검색 오류] {query[:40]}... → {e}")
        return []


def _score_result(result: dict, title_tokens: list[str], addr_tokens: list[str]) -> float:
    """검색 결과 관련성 점수 계산"""
    text = f"{result['title']} {result['description']}".lower()
    score = 0.0
    for token in title_tokens:
        if token.lower() in text:
            score += 2.0
    for token in addr_tokens:
        if token.lower() in text:
            score += 0.5
    return score


def _crawl_page(url: str, max_chars: int = 2000) -> str:
    """웹페이지 본문 추출"""
    try:
        resp = requests.get(url, headers=CRAWL_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        body = soup.get_text(separator=" ", strip=True)
        return _clean_crawled(body)[:max_chars]
    except Exception:
        return ""


def collect_context(item: dict) -> str:
    """
    팝업스토어 1건에 대한 컨텍스트 수집:
    1) 네이버 웹문서 검색 (description)
    2) 관련성 높은 상위 1~2개 페이지 크롤링
    3) 팝플리 introduction 텍스트
    → 세 소스를 결합하여 반환
    """
    title = item.get("title", "")
    addr  = item.get("addr", "")
    title_tokens = _tokenize(title)
    addr_tokens  = _tokenize(addr)

    # 검색 쿼리 2종
    queries = [
        f'"{title}" 팝업스토어 소개 체험',
        f'"{title}" 팝업 후기 굿즈',
    ]

    all_results: list[dict] = []
    seen_links: set[str] = set()
    for query in queries:
        for r in _search_web(query, display=5):
            if r["link"] not in seen_links:
                seen_links.add(r["link"])
                r["score"] = _score_result(r, title_tokens, addr_tokens)
                all_results.append(r)
        time.sleep(0.3)

    all_results.sort(key=lambda x: x["score"], reverse=True)

    context_parts: list[str] = []

    # 관련성 높은 상위 결과 → description 수집
    top_desc = [r for r in all_results if r["score"] >= 1.5][:5]
    for r in top_desc:
        if r["description"]:
            context_parts.append(f"[웹문서 요약] {r['description']}")

    # 관련성 상위 1~2개 → 본문 크롤링
    top_crawl = [r for r in all_results if r["score"] >= 3.0][:2]
    for r in top_crawl:
        print(f"    크롤링 중: {r['link'][:60]}...")
        body = _crawl_page(r["link"])
        if body and len(body) > 100:
            context_parts.append(f"[웹문서 본문] {body}")
        time.sleep(0.5)

    # 팝플리 introduction 추가
    intro = item.get("introduction", "")
    if intro:
        context_parts.append(f"[팝플리 소개] {intro[:800]}")

    return "\n\n".join(context_parts)


def generate_llm_text(item: dict, context: str) -> str:
    """컨텍스트를 바탕으로 GPT-4o-mini로 llm_text 생성"""
    item_summary = {
        "title":      item.get("title", ""),
        "addr":       item.get("addr", ""),
        "start_date": item.get("start_date", ""),
        "end_date":   item.get("end_date", ""),
        "usetime":    item.get("usetime", ""),
        "fee":        item.get("fee", ""),
        "parking":    item.get("parking", ""),
    }
    user_msg = (
        f"아래 팝업스토어 정보와 컨텍스트를 바탕으로 검색 최적화된 설명문을 작성해줘.\n\n"
        f"[팝업스토어 정보]\n{json.dumps(item_summary, ensure_ascii=False, indent=2)}\n\n"
        f"[수집된 컨텍스트]\n{context[:3000] if context else '(수집된 정보 없음)'}"
    )
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"    [LLM 오류] {item.get('title', '')} → {e}")
        return ""


def step4_generate_llm_text(data: list) -> list:
    print("\n[4단계] llm_text 생성 시작 (네이버 웹문서 검색 + 크롤링 + introduction → GPT-4o-mini)")
    result = []
    failed = 0

    for i, item in enumerate(data):
        enriched = dict(item)
        title = item.get("title", "")
        print(f"  [{i+1}/{len(data)}] '{title}'")

        # 1. 컨텍스트 수집
        context = collect_context(item)
        print(f"    컨텍스트 수집: {len(context)}자")

        # 2. llm_text 생성
        llm_text = generate_llm_text(item, context)
        if llm_text:
            enriched["llm_text"] = llm_text
            print(f"    llm_text: {len(llm_text)}자")
        else:
            failed += 1
            enriched["llm_text"] = ""
            print(f"    ✗ llm_text 생성 실패")

        result.append(enriched)
        time.sleep(0.5)  # rate limit 대응

    print(f"  완료: 성공 {len(data)-failed}건, 실패 {failed}건")
    save_step(result, "step4_llm.json")
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 5단계: 최종 JSONL 저장
# ──────────────────────────────────────────────────────────────────────────────

# 최종 JSONL에 포함할 필드 (ingest_data 방식에 맞춤, contenttypeid_code 포함해야 함)
FINAL_FIELDS = [
    "contentid", "title", "contenttypeid", "image",
    "usetime", "restdate", "start_date", "end_date",
    "parking", "fee", "addr",
    "mapy", "mapx", "contenttypeid_code", "llm_text",
]


def step5_save_jsonl(data: list) -> None:
    print("\n[5단계] 최종 JSONL 저장 시작")
    out_path = LLM_DIR / "99_팝업스토어_enriched.jsonl"
    skipped = 0

    with open(out_path, "w", encoding="utf-8") as f:
        for item in data:
            # llm_text 없는 항목은 제외
            if not item.get("llm_text"):
                skipped += 1
                print(f"  [제외] llm_text 없음: '{item.get('title')}'")
                continue

            # FINAL_FIELDS 순서대로, 존재하는 필드만 저장
            record = {k: item[k] for k in FINAL_FIELDS if k in item}

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    total = len(data) - skipped
    print(f"  저장 완료: {out_path}")
    print(f"  총 {total}건 저장 (llm_text 없어 제외: {skipped}건)")


# ──────────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("팝업스토어 데이터 전처리 시작")
    print(f"기준일: {TODAY}")
    print("=" * 60)

    # 원시 데이터 로드
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    print(f"\n원시 데이터 로드 완료: {len(raw)}건")

    # 단계별 실행
    data = step1_normalize(raw)
    data = step2_clean(data)
    data = step3_geocode(data)
    data = step4_generate_llm_text(data)
    step5_save_jsonl(data)

    print("\n" + "=" * 60)
    print("전처리 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
