from typing import List

from app.schemas.chat import AutoStarterPlaceSeed

AUTO_START_PROMPT = """
새 여행 계획 채팅을 시작한다.
여행 기간: {travel_duration}
성인 인원: {adult_count}명
어린이 인원: {child_count}명
요구사항:
1) 사용자에게 먼저 친근하게 인사한다.
2) 위 조건을 반영한 맞춤 일정을 바로 제안한다.
3) 답변은 간결하고 실행 가능한 형태로 작성한다.
4) 필요하면 마지막에 한 가지 확인 질문만 덧붙인다.
"""


AUTO_START_PLACE_PROMPT = """
사용자가 북마크한 장소를 선택해 새 채팅을 시작했다.
아래 장소들을 기반으로 여행 일정을 제안한다.

선택 장소 목록:
{selected_places_block}

요구사항:
1) 사용자에게 먼저 친근하게 인사한다.
2) 선택한 장소를 중심으로 동선을 고려한 일정안을 제안한다.
3) 각 장소를 왜 추천하는지 간단히 설명한다.
4) 필요 시 마지막에 한 가지 확인 질문만 덧붙인다.
"""

AUTO_START_COMBINED_PROMPT = """
사용자가 여행 기본 정보와 선택 장소를 함께 입력해 새 채팅을 시작했다.
여행 기간: {travel_duration}
성인 인원: {adult_count}명
어린이 인원: {child_count}명

선택 장소 목록:
{selected_places_block}

요구사항:
1) 사용자에게 먼저 친근하게 인사한다.
2) 여행 기간/인원 조건을 반영해 일정안을 제안한다.
3) 선택 장소를 중심으로 가까운 동선을 고려해 구성한다.
4) 각 장소를 추천하는 이유를 짧게 설명한다.
5) 필요 시 마지막에 한 가지 확인 질문만 덧붙인다.
"""

AUTO_START_GREETING_PROMPT = """
사용자는 새 여행 채팅을 시작했습니다.
사용자 취향({prefs_info})을 기반으로 간단한 인사와 함께 한국 여행 정보에 대한 대화를 시작한다.

요구사항:
1) 사용자에게 먼저 친근하게 인사한다.
2) 일정은 제안하지 않고 한국 여행 정보에대한 대화로 시작한다.
3) 어떤 도움이 필요한지 다양하게 질문하는 방법으로 묻는다.
"""


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


def render_auto_start_greeting_prompt(prefs_info: str) -> str:
    return AUTO_START_GREETING_PROMPT.format(prefs_info=prefs_info).strip()
