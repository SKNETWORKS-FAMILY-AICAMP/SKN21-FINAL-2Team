"""
보완 스크립트: step1_normalized.json을 읽어서 step2~5만 재실행.
(1단계 필터링·정규화는 이미 완료. Geocoding 결과는 step3_geocoded.json에서 재활용.)

실행:
    python backend/data/reclean_popup.py
"""

import json
import re
import sys
import os
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent
STEP_DIR = DATA_DIR / "preprocess_steps"
LLM_DIR  = DATA_DIR / "llm_result"

sys.path.insert(0, str(ROOT_DIR))
from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT_DIR / ".env")

from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

NONE_VALUES = [None, "", [], {}, 0, 0.0]


def save_step(data: list, filename: str) -> None:
    path = STEP_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[저장] {path} ({len(data)}건)")


# ── 강화된 clean_text ─────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
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
        "\u2000-\u206F"           # General Punctuation
        "\u20D0-\u20FF"           # Combining Diacritical Marks for Symbols
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    # 원문자 목록 기호 제거
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", text)
    # 유니코드 장식 괄호 제거
    text = re.sub(r"[⟪⟫〈〉《》「」『』【】〔〕]", "", text)
    # 과도한 연속 공백/줄바꿈 축소
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ── 2단계: 값 정제 (재실행) ───────────────────────────────────────────────────

def step2_clean(data: list) -> list:
    print("\n[2단계] 값 정제 재실행")
    ids = [item["contentid"] for item in data]
    if len(ids) != len(set(ids)):
        raise ValueError("[오류] contentid 중복!")

    result = []
    for item in data:
        cleaned = dict(item)
        if "introduction" in cleaned:
            cleaned["introduction"] = clean_text(cleaned["introduction"])
            if not cleaned["introduction"]:
                del cleaned["introduction"]
        cleaned = {k: v for k, v in cleaned.items() if v != "Unknown"}
        result.append(cleaned)

    print(f"  정제 완료: {len(result)}건")
    save_step(result, "step2_cleaned.json")
    return result


# ── 3단계: Geocoding 결과 재활용 ──────────────────────────────────────────────

def step3_reuse(step2_data: list) -> list:
    """step3_geocoded.json에서 Geocoding 필드(mapy, mapx, road_address, old_address)를 가져와 병합."""
    print("\n[3단계] Geocoding 결과 재활용")
    geo_path = STEP_DIR / "step3_geocoded.json"
    with open(geo_path, encoding="utf-8") as f:
        geo_list = json.load(f)
    geo_map = {item["contentid"]: item for item in geo_list}

    result = []
    for item in step2_data:
        merged = dict(item)
        geo = geo_map.get(item["contentid"], {})
        for key in ("mapy", "mapx", "road_address", "old_address"):
            if key in geo:
                merged[key] = geo[key]
        result.append(merged)

    save_step(result, "step3_geocoded.json")
    return result


# ── 4단계: llm_text 생성 ─────────────────────────────────────────────────────

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
        intro = item["introduction"][:500]
        lines.append(f"소개:\n{intro}")
    return "\n".join(lines)


def step4_generate_llm_text(data: list) -> list:
    print("\n[4단계] llm_text 재생성 (GPT-4o-mini)")
    result = []
    failed = 0
    for i, item in enumerate(data):
        enriched = dict(item)
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user",   "content": build_user_prompt(item)},
                ],
                max_tokens=600,
                temperature=0.7,
            )
            enriched["llm_text"] = response.choices[0].message.content.strip()
            print(f"  [{i+1}/{len(data)}] ✓ '{item['title']}'")
        except Exception as e:
            failed += 1
            enriched["llm_text"] = ""
            print(f"  [{i+1}/{len(data)}] ✗ '{item['title']}': {e}")
        result.append(enriched)
        time.sleep(0.5)

    print(f"  완료: 성공 {len(data)-failed}건, 실패 {failed}건")
    save_step(result, "step4_llm.json")
    return result


# ── 5단계: 최종 JSONL ────────────────────────────────────────────────────────

FINAL_FIELDS = [
    "contentid", "title", "contenttypeid", "image",
    "usetime", "restdate", "start_date", "end_date",
    "parking", "fee", "addr", "road_address", "old_address",
    "mapy", "mapx", "contenttypeid_code", "llm_text",
]


def step5_save_jsonl(data: list) -> None:
    print("\n[5단계] 최종 JSONL 저장")
    out_path = LLM_DIR / "99_팝업스토어_enriched.jsonl"
    skipped = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for item in data:
            if not item.get("llm_text"):
                skipped += 1
                continue
            record = {k: item[k] for k in FINAL_FIELDS if k in item}
            for k, v in item.items():
                if k not in record:
                    record[k] = v
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  저장 완료: {out_path}")
    print(f"  총 {len(data)-skipped}건 저장")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("보완 재처리: step2~5 재실행")
    print("=" * 60)

    # step1 결과 로드
    step1_path = STEP_DIR / "step1_normalized.json"
    with open(step1_path, encoding="utf-8") as f:
        step1_data = json.load(f)
    print(f"\nstep1 데이터 로드: {len(step1_data)}건")

    data = step2_clean(step1_data)
    data = step3_reuse(data)
    data = step4_generate_llm_text(data)
    step5_save_jsonl(data)

    print("\n" + "=" * 60)
    print("보완 재처리 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
