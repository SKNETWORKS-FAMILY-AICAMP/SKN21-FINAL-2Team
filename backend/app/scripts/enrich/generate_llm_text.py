"""llm_text + tags 생성 스크립트

전처리된 데이터에 OpenAI로 소개글(llm_text)을 생성하고,
tags가 없는 데이터는 llm_text에서 키워드를 추출하여 tags를 생성한다.

대상: tourapi_*, visitseoul_* (콘텐츠 카테고리 제외)
입력: data/preprocessed/{source}_{category}.json
출력: data/preprocessed/enrich/{source}_{category}_enrich.json

사용법:
    python -m app.scripts.enrich.generate_llm_text                      # 전체
    python -m app.scripts.enrich.generate_llm_text tourapi_관광지        # 개별
    python -m app.scripts.enrich.generate_llm_text visitseoul_음식점     # 개별
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

log = logging.getLogger(__name__)

_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_PATH)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
PRE_DIR = DATA_DIR / "preprocessed"
OUT_DIR = DATA_DIR / "enrich"

MODEL = "gpt-4o-mini"
CONCURRENCY = 10

# 대상 파일 (콘텐츠 카테고리 제외)
TARGETS = [
    "tourapi_관광지",
    "tourapi_문화시설",
    "tourapi_레포츠",
    "tourapi_숙박",
    "tourapi_음식점",
    "visitseoul_관광지",
    "visitseoul_숙박",
    "visitseoul_음식점",
    "visitseoul_투어",
]

SYSTEM_PROMPT = (
    "당신은 서울 여행 정보 작성 전문가입니다. "
    "주어진 장소 정보를 바탕으로, 사용자가 자연어로 검색했을 때 잘 매칭되도록 장소를 소개하는 글을 작성해주세요. "
    "장소의 특징, 분위기, 경험할 수 있는 것을 중심으로 300~500자 한국어로 작성하세요. "
    "반드시 완결된 문장으로 끝내세요. 문장이 중간에 잘리면 안 됩니다. "
    "불필요한 인사말, 접두사 없이 소개 내용만 출력하세요. 이모지는 사용하지 마세요."
)

TAGS_SYSTEM_PROMPT = (
    "주어진 장소 소개글에서 검색에 유용한 핵심 키워드를 5~10개 추출하세요. "
    "장소명, 지역명, 특징, 분위기, 활동 등을 포함하세요. "
    "날짜, 기간, 요금, 주소는 키워드에 포함하지 마세요. "
    "JSON 배열 형식으로만 출력하세요. 예: [\"키워드1\", \"키워드2\"]"
)


def _build_user_prompt(item: dict) -> str:
    """OpenAI에 보낼 장소 정보 프롬프트 구성."""
    parts = []
    if v := item.get("title"):
        parts.append(f"장소명: {v}")
    if v := item.get("category_depth"):
        parts.append(f"카테고리: {v}")
    if v := item.get("restaurant_type"):
        parts.append(f"식당 유형: {v}")
    if v := item.get("menu"):
        parts.append(f"메뉴: {v[:200]}")
    if v := item.get("fee"):
        parts.append(f"요금: {v[:200]}")
    if v := item.get("usetime"):
        parts.append(f"이용시간: {v}")
    if v := item.get("restdate"):
        parts.append(f"휴무일: {v}")
    if v := item.get("parking"):
        parts.append(f"주차: {v}")
    tags = item.get("tags") or []
    if tags:
        parts.append(f"태그: {', '.join(tags)}")
    if v := item.get("summary"):
        parts.append(f"요약: {v}")
    if v := item.get("description"):
        parts.append(f"설명: {v[:500]}")
    return "\n".join(parts)


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
    text = _LLM_EMOJI_RE.sub("", text)
    return re.sub(r"  +", " ", text).strip()


def _build_llm_text(item: dict, intro: str) -> str:
    """구조화 텍스트 + AI 소개글로 llm_text 구성."""
    lines = []
    if v := item.get("title"):
        lines.append(f"- 장소명: {v}")
    if v := item.get("addr"):
        lines.append(f"- 주소: {v}")
    if v := item.get("category_depth"):
        lines.append(f"- 카테고리: {v}")
    if v := item.get("usetime"):
        lines.append(f"- 이용시간: {v}")
    if v := item.get("fee"):
        lines.append(f"- 요금: {v[:200]}")
    tags = item.get("tags") or []
    if tags:
        lines.append(f"- 주요 키워드: {', '.join(tags)}")
    if intro:
        lines.append(f"- 소개: {intro}")
    return "\n".join(lines)


def _fallback_intro(item: dict) -> str:
    return (item.get("summary") or item.get("description") or "")[:200]


async def _generate_intro(
    client: AsyncOpenAI, sem: asyncio.Semaphore, item: dict, idx: int, total: int
) -> str:
    """OpenAI로 소개글 생성."""
    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(item)},
                ],
                max_tokens=600,
                temperature=0.5,
            )
            text = resp.choices[0].message.content.strip()
            if (idx + 1) % 50 == 0 or idx == 0:
                log.info("  소개글 진행: %d/%d", idx + 1, total)
            return text
        except Exception as e:
            log.warning("  [오류] %d/%d %s: %s", idx + 1, total, item.get("title", ""), e)
            return _fallback_intro(item)


async def _generate_tags(
    client: AsyncOpenAI, sem: asyncio.Semaphore, llm_text: str, idx: int, total: int
) -> list[str]:
    """llm_text에서 키워드 태그 추출."""
    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": TAGS_SYSTEM_PROMPT},
                    {"role": "user", "content": llm_text},
                ],
                max_tokens=100,
                temperature=0.3,
            )
            text = resp.choices[0].message.content.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            tags = json.loads(text)
            if isinstance(tags, list):
                return [t for t in tags if isinstance(t, str)]
        except Exception as e:
            log.warning("  [태그 오류] %d/%d: %s", idx + 1, total, e)
    return []


async def process(name: str):
    """단일 파일 처리: llm_text 생성 + tags 없는 데이터에 tags 추가."""
    in_path = PRE_DIR / f"{name}.json"
    out_path = OUT_DIR / f"{name}_enrich.json"

    if not in_path.exists():
        log.warning("  파일 없음: %s", in_path.name)
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        log.warning("  %s: 데이터 없음", name)
        return

    log.info("  %s: %d건 처리 시작", name, len(data))

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    sem = asyncio.Semaphore(CONCURRENCY)

    # 1단계: 소개글 생성
    intro_tasks = [_generate_intro(client, sem, item, i, len(data)) for i, item in enumerate(data)]
    intros = await asyncio.gather(*intro_tasks)

    # llm_text 구성
    result = []
    needs_tags_idx = []
    for i, (item, intro) in enumerate(zip(data, intros)):
        new_item = dict(item)
        new_item["llm_text"] = _strip_llm_emoji(_build_llm_text(item, intro))
        result.append(new_item)
        if not item.get("tags"):
            needs_tags_idx.append(i)

    # 2단계: tags 없는 데이터에 tags 생성
    if needs_tags_idx:
        log.info("  %s: tags 생성 %d건", name, len(needs_tags_idx))
        tags_tasks = [
            _generate_tags(client, sem, result[i]["llm_text"], i, len(needs_tags_idx))
            for i in needs_tags_idx
        ]
        tags_results = await asyncio.gather(*tags_tasks)
        for i, tags in zip(needs_tags_idx, tags_results):
            result[i]["tags"] = tags

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info("  저장 완료 → %s", out_path.name)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = TARGETS

    log.info("llm_text + tags 생성 (GPT-4o-mini)")
    log.info("대상: %s", ", ".join(targets))

    for name in targets:
        log.info("── %s ──", name)
        asyncio.run(process(name))

    log.info("완료")


if __name__ == "__main__":
    main()
