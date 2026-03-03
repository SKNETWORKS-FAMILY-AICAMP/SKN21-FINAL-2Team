from typing import List

from app.schemas.chat import AutoStarterPlaceSeed
from app.services.prompts import (
    AUTO_START_PROMPT,
    AUTO_START_PLACE_PROMPT,
    AUTO_START_COMBINED_PROMPT,
    AUTO_START_GREETING_PROMPT,
)


def _normalize_count(value: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else 0
    except (TypeError, ValueError):
        return 0


def render_auto_start_prompt(travel_duration: str, adult_count: int, child_count: int) -> str:
    duration = (travel_duration or "").strip() or "미정"
    adult = _normalize_count(adult_count)
    child = _normalize_count(child_count)
    return AUTO_START_PROMPT.format(
        travel_duration=duration,
        adult_count=adult,
        child_count=child,
    ).strip()


def render_auto_start_place_prompt(selected_places: List[AutoStarterPlaceSeed]) -> str:
    lines = []
    for idx, place in enumerate(selected_places[:5], start=1):
        name = (place.name or "").strip() or "이름 없는 장소"
        address = (place.adress or "").strip() or "주소 정보 없음"
        pid = place.place_id if (place.place_id or 0) > 0 else "unknown"
        lines.append(f"{idx}. {name} (ID: {pid}) / 주소: {address}")

    selected_places_block = "\n".join(lines) if lines else "1. 이름 없는 장소 (ID: unknown) / 주소: 주소 정보 없음"
    return AUTO_START_PLACE_PROMPT.format(selected_places_block=selected_places_block).strip()


def render_auto_start_combined_prompt(
    travel_duration: str,
    adult_count: int,
    child_count: int,
    selected_places: List[AutoStarterPlaceSeed],
) -> str:
    duration = (travel_duration or "").strip() or "미정"
    adult = _normalize_count(adult_count)
    child = _normalize_count(child_count)

    lines = []
    for idx, place in enumerate(selected_places[:5], start=1):
        name = (place.name or "").strip() or "이름 없는 장소"
        address = (place.adress or "").strip() or "주소 정보 없음"
        pid = place.place_id if (place.place_id or 0) > 0 else "unknown"
        lines.append(f"{idx}. {name} (ID: {pid}) / 주소: {address}")

    selected_places_block = "\n".join(lines) if lines else "1. 이름 없는 장소 (ID: unknown) / 주소: 주소 정보 없음"
    return AUTO_START_COMBINED_PROMPT.format(
        travel_duration=duration,
        adult_count=adult,
        child_count=child,
        selected_places_block=selected_places_block,
    ).strip()


def render_auto_start_greeting_prompt() -> str:
    return AUTO_START_GREETING_PROMPT.strip()
