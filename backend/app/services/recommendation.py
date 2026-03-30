"""
오늘의 추천 — 메모리 캐시 + LLM 생성
====================================
채팅 턴마다 비동기로 추천 문구를 갱신하고,
마이페이지 접속 시에는 캐시만 읽어 빠르게 반환한다.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.llm_factory import LLMFactory
from app.agents.prompts.prompts import get_language_instruction
from app.models.enums import LanguageType


# ── 스키마 ──────────────────────────────────────────────
class RecommendationItem(BaseModel):
    id: str
    title: str
    description: str
    prompt: str


# ── 메모리 캐시 ────────────────────────────────────────
_cache: dict[int, RecommendationItem] = {}


def get_cached(user_id: int) -> Optional[RecommendationItem]:
    """캐시된 추천을 반환한다. 없으면 None."""
    return _cache.get(user_id)


def invalidate_cache(user_id: int) -> None:
    """특정 유저의 추천 캐시를 삭제한다."""
    _cache.pop(user_id, None)


# ── LLM 프롬프트 ───────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a conversation topic suggester for a Seoul travel chatbot.
Your goal is to propose ONE interesting conversation topic that makes the user think:
"Oh, I want to chat about this!"

IMPORTANT CONSTRAINTS:
- The chatbot can ONLY help with Seoul travel: recommending places, planning itineraries, suggesting restaurants/cafes/attractions, and answering Seoul travel questions.
- Topics MUST be something the chatbot can actually answer well — concrete Seoul travel topics like neighborhoods, food, sightseeing, activities, seasonal events, etc.
- Do NOT suggest overly niche, abstract, or non-travel topics that the chatbot cannot handle.
- Keep topics broad and appealing — think "popular travel magazine article" level, not "PhD thesis" level.

You are NOT recommending an action or a to-do.
You are suggesting a conversation topic — something the user would enjoy discussing with the chatbot.

Return EXACTLY this JSON format (no markdown, no extra text):
{{"title": "대화 주제 제목 (15자 이내)", "description": "이 주제로 대화하면 어떤 이야기를 나눌 수 있는지 설명 (2~3문장, 80~120자)", "prompt": "이 주제로 대화를 시작하는 자연스러운 첫 메시지"}}

Rules:
- title: 대화 주제처럼 느껴지는 짧고 호기심을 끄는 제목 (예: "성수동 카페 투어", "서울 야경 명소")
- description: "이 주제로 대화하면 ~에 대해 알아볼 수 있어요" 느낌으로 작성.
  구체적인 장소명이나 키워드를 포함해서 생동감 있게.
  80~120자 내외, 2~3문장.
- prompt: 사용자가 이 주제로 채팅을 시작할 때 보낼 자연스러운 첫 마디 (서울 여행 관련 질문 형태)
- JSON만 반환, 다른 텍스트 금지

{language_instruction}
"""

_USER_WITH_HISTORY = """\
[사용자 선호도]
{preferences}

[참고: 이미 대화한 주제 — 이것들과 겹치지 않으면 좋겠어요]
{histories}

위 선호도를 바탕으로, 서울 여행과 관련된 새로운 대화 주제 1개를 제안해줘.
이전 대화 주제는 참고만 하고 (겹치지 않도록), 주제 자체는 서울의 맛집, 명소, 활동, 동네 탐방 등 폭넓게 제안해줘.
누구나 흥미를 느낄 수 있는 포괄적인 서울 여행 주제가 좋아."""

_USER_WITH_PREFS_ONLY = """\
[사용자 선호도]
{preferences}

대화 이력은 없지만 위 선호도를 바탕으로, 사용자가 챗봇과 이야기해보고 싶어할 만한 서울 여행 대화 주제를 1개 제안해줘.
사용자의 취향에 맞는 구체적인 주제를 제안해줘."""

_USER_NO_HISTORY = """\
대화 이력도 선호도 정보도 없는 새로운 사용자입니다.
서울 여행이 처음인 외국인 관광객에게 추천할 만한 인기 여행 코스를 1개 만들어줘.
계절이나 최신 트렌드를 반영해서 구체적으로 작성해줘."""


def _build_preferences_text(preferences: dict | None) -> str:
    """사용자 선호도 딕셔너리를 텍스트로 변환한다."""
    if not preferences:
        return "선호도 정보 없음"

    lines = []
    if preferences.get("plan_prefer"):
        lines.append(f"- 여행 일정 스타일: {preferences['plan_prefer']}")
    if preferences.get("vibe_prefer"):
        lines.append(f"- 선호 여행 환경: {preferences['vibe_prefer']}")
    if preferences.get("places_prefer"):
        lines.append(f"- 관심 장소 유형: {preferences['places_prefer']}")

    extras = [preferences.get(f"extra_prefer{i}") for i in range(1, 4)]
    extras = [e for e in extras if e]
    if extras:
        lines.append(f"- 추가 선호: {', '.join(extras)}")

    return "\n".join(lines) if lines else "선호도 정보 없음"


# ── 생성 함수 ──────────────────────────────────────────
async def generate_recommendation(
    user_id: int,
    histories: list[str] | None = None,
    preferences: dict | None = None,
    language: str | None = None,
) -> RecommendationItem:
    """LLM으로 추천 문구 1개를 생성하고 캐시에 저장한다."""
    import json as _json

    llm = LLMFactory.get_llm()
    prefs_text = _build_preferences_text(preferences)
    has_history = histories and any(h.strip() for h in histories)
    has_prefs = prefs_text != "선호도 정보 없음"

    lang_instruction = get_language_instruction(language or "ko", name_instruction=False)

    if has_history:
        combined = "\n".join(f"- {h}" for h in histories if h.strip())
        user_msg = _USER_WITH_HISTORY.format(
            preferences=prefs_text,
            histories=combined,
        )
    elif has_prefs:
        user_msg = _USER_WITH_PREFS_ONLY.format(preferences=prefs_text)
    else:
        user_msg = _USER_NO_HISTORY

    system_prompt = _SYSTEM_PROMPT.format(language_instruction=lang_instruction)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg),
    ]

    try:
        response = await llm.ainvoke(messages)
        text = response.content.strip()

        # JSON 파싱 — 여러 형태 대응
        # 1) ```json ... ``` 블록 제거
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                p = part.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                if p.startswith("{"):
                    text = p
                    break

        # 2) JSON 앞뒤의 불필요한 텍스트 제거
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        # 3) 작은따옴표 → 큰따옴표 변환
        import re
        text = re.sub(r"'(\s*:\s*)", r'"\1', text)
        text = re.sub(r"(:\s*)'", r'\1"', text)
        text = re.sub(r"'(\s*[,}])", r'"\1', text)
        text = re.sub(r"([{,]\s*)'", r'\1"', text)

        data = _json.loads(text)
        item = RecommendationItem(
            id=f"rec-{uuid.uuid4().hex[:8]}",
            title=data["title"],
            description=data["description"],
            prompt=data["prompt"],
        )
    except Exception as e:
        print(f"[Recommendation] LLM 생성 실패 (user_id={user_id}): {e}")
        print(f"[Recommendation] Raw response: {response.content[:200] if response else 'N/A'}")
        # fallback
        item = RecommendationItem(
            id="rec-fallback",
            title="서울 인기 명소 탐방",
            description="명동, 홍대, 성수동 핫플레이스 코스 짜볼까요?",
            prompt="홍대 카페랑 맛집 코스 추천해줘",
        )

    _cache[user_id] = item
    return item


async def generate_recommendation_background(
    user_id: int,
    histories: list[str] | None = None,
    preferences: dict | None = None,
    language: str | None = None,
) -> None:
    """fire-and-forget 용 래퍼. 예외가 터져도 조용히 로깅만 한다."""
    try:
        item = await generate_recommendation(user_id, histories, preferences, language)
        print(f"[Recommendation] Cached for user {user_id}: {item.title}")
    except Exception as e:
        print(f"[Recommendation] Background generation failed: {e}")
