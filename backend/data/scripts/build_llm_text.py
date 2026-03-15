"""
llm_text 생성 스크립트 (템플릿 + OpenAI 버전)
===============================================
입력: data/preprocessed/visitseoul_{카테고리}.json
출력: data/preprocessed/visitseoul_{카테고리}_template.json

형식:
    - 장소명: 북한산국립공원
    - 주소: 서울 성북구 보국문로 215
    - 주요 키워드: 등산코스, 서울힐링명소
    - 소개: <OpenAI가 생성한 자연어 소개>
"""

import asyncio
import json
import os
from pathlib import Path

from openai import AsyncOpenAI

DATA_DIR = Path(__file__).resolve().parent.parent
PRE_DIR = DATA_DIR / "preprocessed"

MODEL = "gpt-4o-mini"
CONCURRENCY = 10

SYSTEM_PROMPT = (
    "당신은 서울 여행 정보 작성 전문가입니다. "
    "주어진 장소 정보를 바탕으로, 사용자가 자연어로 검색했을 때 잘 매칭되도록 장소를 소개하는 글을 작성해주세요. "
    "장소의 특징, 분위기, 경험할 수 있는 것을 중심으로 300자 내외 한국어로 작성하세요. "
    "불필요한 인사말, 접두사 없이 소개 내용만 출력하세요."
)


def build_user_prompt(item: dict) -> str:
    parts = []
    if v := item.get("title"):
        parts.append(f"장소명: {v}")
    if v := item.get("category_depth"):
        parts.append(f"카테고리: {v}")
    if v := item.get("cuisine_kind"):
        parts.append(f"음식 종류: {v}")
    if v := item.get("restaurant_type"):
        parts.append(f"식당 유형: {v}")
    if v := item.get("halal"):
        parts.append(f"할랄 인증: {v}")
    if v := item.get("salam"):
        parts.append(f"살람(이슬람): {v}")
    if v := item.get("dietary"):
        parts.append(f"식이 유형: {v}")
    if v := item.get("menu"):
        parts.append(f"메뉴: {v[:200]}")
    tags = item.get("tags") or []
    if tags:
        parts.append(f"태그: {', '.join(tags)}")
    if v := item.get("summary"):
        parts.append(f"요약: {v}")
    if v := item.get("description"):
        parts.append(f"설명: {v[:500]}")
    return "\n".join(parts)


def fallback_intro(item: dict) -> str:
    return (item.get("summary") or item.get("description") or "")[:200]


def build_llm_text(item: dict, intro: str) -> str:
    lines = []
    if title := item.get("title"):
        lines.append(f"- 장소명: {title}")
    if addr := item.get("addr"):
        lines.append(f"- 주소: {addr}")
    tags = item.get("tags") or []
    if tags:
        lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if intro:
        lines.append(f"- 소개: {intro}")
    return "\n".join(lines)


async def generate_intro(client: AsyncOpenAI, sem: asyncio.Semaphore, item: dict, idx: int, total: int) -> str:
    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(item)},
                ],
                max_tokens=300,
                temperature=0.5,
            )
            text = resp.choices[0].message.content.strip()
            if (idx + 1) % 50 == 0 or idx == 0:
                print(f"  진행: {idx + 1}/{total}")
            return text
        except Exception as e:
            print(f"  [오류] {idx + 1}/{total} - {item.get('title', '')}: {e}")
            return fallback_intro(item)


async def process_async(category: str):
    in_path = PRE_DIR / f"visitseoul_{category}.json"
    out_path = PRE_DIR / f"visitseoul_{category}_template.json"

    if not in_path.exists():
        print(f"  파일 없음: {in_path.name}")
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"  {category}: {len(data)}건 처리 시작")

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    sem = asyncio.Semaphore(CONCURRENCY)

    tasks = [generate_intro(client, sem, item, i, len(data)) for i, item in enumerate(data)]
    intros = await asyncio.gather(*tasks)

    result = []
    for item, intro in zip(data, intros):
        new_item = dict(item)
        new_item["llm_text"] = build_llm_text(item, intro)
        result.append(new_item)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  저장 완료 → {out_path.name}")


def main():
    import sys
    category = sys.argv[1] if len(sys.argv) > 1 else "관광지"

    print("=" * 50)
    print(f"llm_text 생성 (템플릿 + OpenAI {MODEL})")
    print("=" * 50)
    asyncio.run(process_async(category))
    print("=" * 50)


if __name__ == "__main__":
    main()
