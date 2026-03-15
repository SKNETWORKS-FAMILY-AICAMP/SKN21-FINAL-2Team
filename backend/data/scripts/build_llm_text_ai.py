"""
llm_text 생성 스크립트 (OpenAI API 버전)
==========================================
입력: data/preprocessed/visitseoul_{카테고리}.json
출력: data/preprocessed/visitseoul_{카테고리}_ai.json (llm_text 필드 추가)

- GPT-4o-mini로 자연어 소개글 생성
- 비동기 + 동시 10개 요청으로 속도 개선
- 실패한 항목은 title + tags 기반 기본 텍스트로 대체
"""

import asyncio
import json
import os
from pathlib import Path

from openai import AsyncOpenAI

DATA_DIR = Path(__file__).resolve().parent.parent
PRE_DIR = DATA_DIR / "preprocessed"

MODEL = "gpt-4o-mini"
CONCURRENCY = 10   # 동시 요청 수

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
    tags = item.get("tags") or []
    if tags:
        parts.append(f"태그: {', '.join(tags)}")
    if v := item.get("summary"):
        parts.append(f"요약: {v}")
    if v := item.get("description"):
        # 너무 길면 앞 500자만
        parts.append(f"설명: {v[:500]}")
    return "\n".join(parts)


def fallback_text(item: dict) -> str:
    """API 실패 시 기본 텍스트"""
    title = item.get("title", "")
    tags = ", ".join(item.get("tags") or [])
    summary = item.get("summary") or item.get("description") or ""
    return f"{title}. {tags}. {summary[:200]}".strip()


async def generate_one(client: AsyncOpenAI, sem: asyncio.Semaphore, item: dict, idx: int, total: int) -> str:
    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(item)},
                ],
                max_tokens=400,
                temperature=0.5,
            )
            text = resp.choices[0].message.content.strip()
            if (idx + 1) % 50 == 0 or idx == 0:
                print(f"  진행: {idx + 1}/{total}")
            return text
        except Exception as e:
            print(f"  [오류] {idx + 1}/{total} - {item.get('title', '')}: {e}")
            return fallback_text(item)


async def process_async(category: str):
    in_path = PRE_DIR / f"visitseoul_{category}.json"
    out_path = PRE_DIR / f"visitseoul_{category}_ai.json"

    if not in_path.exists():
        print(f"  파일 없음: {in_path.name}")
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"  {category}: {len(data)}건 처리 시작")

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    sem = asyncio.Semaphore(CONCURRENCY)

    tasks = [
        generate_one(client, sem, item, i, len(data))
        for i, item in enumerate(data)
    ]
    llm_texts = await asyncio.gather(*tasks)

    result = []
    for item, text in zip(data, llm_texts):
        new_item = dict(item)
        new_item["llm_text"] = text
        result.append(new_item)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  저장 완료 → {out_path.name}")


def main():
    import sys
    category = sys.argv[1] if len(sys.argv) > 1 else "관광지"

    print("=" * 50)
    print(f"llm_text 생성 (OpenAI {MODEL})")
    print("=" * 50)
    asyncio.run(process_async(category))
    print("=" * 50)


if __name__ == "__main__":
    main()
