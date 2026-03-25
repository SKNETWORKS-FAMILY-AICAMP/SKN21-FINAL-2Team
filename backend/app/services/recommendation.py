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


# ── LLM 프롬프트 ───────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a Seoul travel recommendation assistant.
Your job is to suggest a COMPLETELY NEW travel topic that the user hasn't explored yet.
You must AVOID recommending anything similar to what the user already discussed.

Return EXACTLY this JSON format (no markdown, no extra text):
{{"title": "추천 제목 (15자 이내)", "description": "추천 설명 (2~3문장, 80~120자)", "prompt": "챗봇에 전달할 대화 시작 메시지"}}

Rules:
- title: 호기심을 자극하는 짧고 임팩트 있는 제목
- description: 사용자가 읽고 "이거 해보고 싶다!" 라고 느낄 수 있도록 작성.
  첫 문장은 구체적인 장소명, 음식, 활동을 넣어 생동감 있게.
  두번째 문장은 왜 지금 가봐야 하는지 이유나 매력 포인트를 설명.
  80~120자 내외의 2~3문장으로 작성.
- prompt: 사용자가 챗봇에 보낼 자연스러운 요청 메시지
- 반드시 한국어로 작성
- JSON만 반환, 다른 텍스트 금지
"""

_USER_WITH_HISTORY = """\
[사용자 선호도]
{preferences}

[이미 대화한 주제 — 이 주제들은 절대 추천하지 마세요]
{histories}

위 대화 이력은 사용자가 이미 탐색한 주제입니다.
이 주제들과 겹치지 않는, 완전히 새로운 서울 여행 주제를 1개 추천해줘.
사용자의 선호도를 참고하되, 이전 대화와 다른 지역/카테고리/활동을 제안해야 합니다.
예: 맛집 대화를 했다면 → 문화/체험/쇼핑/야경 등 다른 카테고리로 추천."""

_USER_WITH_PREFS_ONLY = """\
[사용자 선호도]
{preferences}

대화 이력은 없지만 위 선호도를 바탕으로 사용자가 관심을 가질 만한 서울 여행 추천을 1개 만들어줘.
사용자의 취향에 딱 맞는 구체적인 코스나 장소를 제안해줘."""

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
) -> RecommendationItem:
    """LLM으로 추천 문구 1개를 생성하고 캐시에 저장한다."""
    import json as _json

    llm = LLMFactory.get_llm()
    prefs_text = _build_preferences_text(preferences)
    has_history = histories and any(h.strip() for h in histories)
    has_prefs = prefs_text != "선호도 정보 없음"

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

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
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
) -> None:
    """fire-and-forget 용 래퍼. 예외가 터져도 조용히 로깅만 한다."""
    try:
        item = await generate_recommendation(user_id, histories, preferences)
        print(f"[Recommendation] Cached for user {user_id}: {item.title}")
    except Exception as e:
        print(f"[Recommendation] Background generation failed: {e}")
