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
from datetime import datetime
from pathlib import Path

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
TODAY = datetime(2026, 3, 4).date()          # 기간 만료 기준일
CONTENTID_START = 9000001                    # 9로 시작하는 7자리, 순번 증가
RAW_FILE = DATA_DIR / "99_팝업스토어.json"

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
            "restdate"        : f"{end_date}까지" if end_date else None,
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
# 4단계: llm_text 생성 (GPT-4o-mini)
# ──────────────────────────────────────────────────────────────────────────────

LLM_SYSTEM_PROMPT = """당신은 한국 팝업스토어 정보를 자연스럽고 생동감 있는 홍보 문장으로 변환하는 전문가입니다.
아래 정보를 바탕으로 해당 팝업스토어를 방문하고 싶게 만드는 설명문을 작성하세요.

규칙:
- 2~4개 문단, 총 150~300자 분량
- 이모지 사용 금지
- 장소, 기간, 운영시간 등 핵심 정보를 자연스럽게 녹여낼 것
- 관광지 안내문과 동일한 공식적이면서도 친근한 톤 유지
- 마케팅 표현(최대 규모, 놓치지 마세요 등) 최소화"""


def build_user_prompt(item: dict) -> str:
    lines = [f"팝업스토어명: {item.get('title', '')}"]
    if item.get("addr"):
        lines.append(f"위치: {item['addr']}")
    if item.get("start_date") and item.get("end_date"):
        lines.append(f"운영기간: {item['start_date']} ~ {item['end_date']}")
    if item.get("usetime"):
        lines.append(f"운영시간: {item['usetime']}")
    if item.get("fee"):
        lines.append(f"입장료: {item['fee']}")
    if item.get("parking"):
        lines.append(f"주차: {item['parking']}")
    if item.get("introduction"):
        intro = item["introduction"][:500]  # 너무 길면 잘라냄
        lines.append(f"소개:\n{intro}")
    return "\n".join(lines)


def step4_generate_llm_text(data: list) -> list:
    print("\n[4단계] llm_text 생성 시작 (GPT-4o-mini)")
    result = []
    failed = 0

    for i, item in enumerate(data):
        enriched = dict(item)
        prompt = build_user_prompt(item)
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=600,
                temperature=0.7,
            )
            llm_text = response.choices[0].message.content.strip()
            enriched["llm_text"] = llm_text
            print(f"  [{i+1}/{len(data)}] ✓ '{item['title']}'")
        except Exception as e:
            failed += 1
            print(f"  [{i+1}/{len(data)}] ✗ 실패 '{item['title']}': {e}")
            enriched["llm_text"] = ""  # 빈 값으로 유지 (5단계에서 제외 여부 결정)

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
    "parking", "fee", "addr", "road_address", "old_address",
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

            # 필드 순서 정리 (FINAL_FIELDS 순서대로, 존재하는 것만)
            record = {k: item[k] for k in FINAL_FIELDS if k in item}
            # 위에 없는 나머지 키도 포함
            for k, v in item.items():
                if k not in record:
                    record[k] = v

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
