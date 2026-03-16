"""
Step 5: OpenAI 기반 llm_text 보강 (선택적)
==========================================
preprocessed JSON에서 장소 정보를 읽어 OpenAI GPT-4o-mini로
자연어 소개글을 생성한 뒤 llm_text를 교체한다.

- template 버전: 구조화된 텍스트 + AI 소개글 결합
- ai 버전: AI 소개글만 사용

Step 3의 template llm_text로도 충분하지만,
더 자연스러운 소개글이 필요할 때 이 스크립트를 사용한다.

입력: data/preprocessed/visitseoul_{카테고리}.json 또는 visitkorea_{카테고리}.json
출력: data/preprocessed/{입력파일명}_template.json 또는 _ai.json

사용법:
  cd backend
  python -u data/scripts/visitkorea/step5_generate_text.py 관광지
  python -u data/scripts/visitkorea/step5_generate_text.py 관광지 --mode ai
  python -u data/scripts/visitkorea/step5_generate_text.py 관광지 --source visitkorea
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI

DATA_DIR = Path(__file__).resolve().parents[2]
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
    if v := item.get("title"):          parts.append(f"장소명: {v}")
    if v := item.get("category_depth"): parts.append(f"카테고리: {v}")
    if v := item.get("cuisine_kind"):   parts.append(f"음식 종류: {v}")
    if v := item.get("restaurant_type"):parts.append(f"식당 유형: {v}")
    if v := item.get("halal"):          parts.append(f"할랄 인증: {v}")
    if v := item.get("salam"):          parts.append(f"살람(이슬람): {v}")
    if v := item.get("dietary"):        parts.append(f"식이 유형: {v}")
    if v := item.get("menu"):           parts.append(f"메뉴: {v[:200]}")
    if v := item.get("room_type"):      parts.append(f"객실 유형: {v}")
    if v := item.get("fee"):            parts.append(f"요금: {v[:200]}")
    if v := item.get("usetime"):        parts.append(f"체크인/체크아웃: {v}")
    tags = item.get("tags") or []
    if tags:                            parts.append(f"태그: {', '.join(tags)}")
    if v := item.get("summary"):        parts.append(f"요약: {v}")
    if v := item.get("description"):    parts.append(f"설명: {v[:500]}")
    return "\n".join(parts)


def fallback_intro(item: dict) -> str:
    return (item.get("summary") or item.get("description") or "")[:200]


def fallback_text(item: dict) -> str:
    title = item.get("title", "")
    tags = ", ".join(item.get("tags") or [])
    summary = item.get("summary") or item.get("description") or ""
    return f"{title}. {tags}. {summary[:200]}".strip()


def build_template_llm_text(item: dict, intro: str) -> str:
    """template 모드: 구조화 텍스트 + AI 소개글"""
    lines = []
    if title := item.get("title"):   lines.append(f"- 장소명: {title}")
    if addr := item.get("addr"):     lines.append(f"- 주소: {addr}")
    if v := item.get("usetime"):     lines.append(f"- 체크인/체크아웃: {v}")
    if v := item.get("room_type"):   lines.append(f"- 객실 유형: {v}")
    if v := item.get("fee"):         lines.append(f"- 요금: {v[:200]}")
    tags = item.get("tags") or []
    if tags:                         lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if intro:                        lines.append(f"- 소개: {intro}")
    return "\n".join(lines)


async def generate_one(client: AsyncOpenAI, sem: asyncio.Semaphore,
                        item: dict, idx: int, total: int, mode: str) -> str:
    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(item)},
                ],
                max_tokens=400 if mode == "ai" else 300,
                temperature=0.5,
            )
            text = resp.choices[0].message.content.strip()
            if (idx + 1) % 50 == 0 or idx == 0:
                print(f"  진행: {idx + 1}/{total}")
            return text
        except Exception as e:
            print(f"  [오류] {idx + 1}/{total} - {item.get('title', '')}: {e}")
            return fallback_text(item) if mode == "ai" else fallback_intro(item)


async def process_async(category: str, mode: str = "template", source: str = "visitseoul"):
    in_path = PRE_DIR / f"{source}_{category}.json"
    suffix = "_template" if mode == "template" else "_ai"
    out_path = PRE_DIR / f"{source}_{category}{suffix}.json"

    if not in_path.exists():
        print(f"  파일 없음: {in_path.name}")
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"  {source}_{category}: {len(data)}건 처리 시작 (mode={mode})")

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    sem = asyncio.Semaphore(CONCURRENCY)

    tasks = [generate_one(client, sem, item, i, len(data), mode) for i, item in enumerate(data)]
    generated = await asyncio.gather(*tasks)

    result = []
    for item, text in zip(data, generated):
        new_item = dict(item)
        if mode == "template":
            new_item["llm_text"] = build_template_llm_text(item, text)
        else:
            new_item["llm_text"] = text
        result.append(new_item)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  저장 완료 → {out_path.name}")


def main():
    category = sys.argv[1] if len(sys.argv) > 1 else "관광지"
    mode = "template"
    source = "visitseoul"

    for i, arg in enumerate(sys.argv):
        if arg == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
        if arg == "--source" and i + 1 < len(sys.argv):
            source = sys.argv[i + 1]

    print("=" * 50)
    print(f"llm_text 생성 (OpenAI {MODEL}, mode={mode}, source={source})")
    print("=" * 50)
    asyncio.run(process_async(category, mode=mode, source=source))
    print("=" * 50)


if __name__ == "__main__":
    main()
