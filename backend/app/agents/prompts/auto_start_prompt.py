from typing import List

from app.schemas.chat import AutoStarterPlaceSeed

COMMON_RESPONSE_RULES = """
[공통 응답 규약]
- 본 대화의 여행 범위는 서울로 고정한다.
- 모든 제안/선택지는 반드시 서울 안에서 즐길 수 있는 내용만 제시한다.
- 첫 응답은 확정 일정표가 아니라 가벼운 제안 초안으로 작성한다.
- 첫 응답은 상세 시간표(시간대별 플랜)나 빡빡한 동선은 제시하지 않는다.
- 단정형 표현(예: 무조건, 반드시)은 쓰지 않고 추천 가설 톤으로 작성한다.
- '왜 이 제안인지'를 사용자 입력 정보/취향 기준으로 1~2줄 설명한다.
- 한국 서울 여행 트렌드는 완곡하게 반영한다(예: 요즘 많이 찾는 편).
- 답변 형식은 반드시 아래 순서를 지킨다.
  1) 인사
  2) 제안 요약
  3) 선택지 2~3개
  4) 선택형 질문 1개(문장 마지막)
"""

AUTO_START_TRIP_CONTEXT_RULES = """
[모드 지침: 일정+인원(trip_context)]
입력 정보:
- 여행 기간: {travel_duration}
- 성인 인원: {adult_count}명
- 어린이 인원: {child_count}명

작성 방식:
- 일수 배분 수준의 러프 제안만 한다.
- 서울 내 권역(예: 홍대/성수/강남/잠실 등) 또는 서울 테마 기준으로 며칠 배분하면 좋은지와 이동 피로도 관점을 함께 제안한다.
- 확정 동선이나 예약 전제 문장은 피한다.
"""

AUTO_START_SELECTED_PLACES_RULES = """
[모드 지침: 선택 장소(selected_places)]
선택 장소 목록:
{selected_places_block}

작성 방식:
- 선택 장소를 서울 권역 또는 서울 테마 기준으로 묶어서 제안한다.
- 반일 코스/야간 코스처럼 부담 없는 묶음 단위로 안내한다.
- 어떤 묶음을 우선할지 고를 수 있게 선택지를 만든다.
"""

AUTO_START_COMBINED_RULES = """
[모드 지침: 일정+인원+선택 장소(combined)]
입력 정보:
- 여행 기간: {travel_duration}
- 성인 인원: {adult_count}명
- 어린이 인원: {child_count}명

선택 장소 목록:
{selected_places_block}

작성 방식:
- 일수 배분 + 선택 장소 배치를 결합한 초안 버전만 제시한다.
- 남는 일수는 미정 슬롯으로 두고, 사용자가 후속 선택할 수 있게 둔다.
- 왜 이 배치를 추천하는지 서울 내 이동 효율/취향 관점으로 짧게 설명한다.
"""

AUTO_START_GREETING_RULES = """
[모드 지침: 정보 없음(greeting)]
사용자 입력 정보가 거의 없으므로, 일정 제안은 하지 않는다.

작성 방식:
- 인사 후 취향 탐색 중심으로 대화를 연다.
- 아래 축에서 빠르게 선택할 수 있도록 2~3개 선택지를 제안한다.
  - 서울 여행 분위기(예: 활기/여유)
  - 서울 관심 테마(예: K-pop, 미식, 전시, 한강 야경, 로컬 골목)
  - 서울 동행 형태(혼자/친구/가족)
- 마지막 문장은 반드시 '어떤 걸 자세히 알아볼까요?' 형태의 질문으로 끝낸다.
- primary_intent는 GENERAL로 설정한다.

# 사용자 취향:
{prefs_info}
"""


def _normalize_count(value: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else 0
    except (TypeError, ValueError):
        return 0


def _render_prompt(*sections: str) -> str:
    return "\n\n".join((section or "").strip() for section in sections if (section or "").strip()).strip()


def _format_selected_places_block(selected_places: List[AutoStarterPlaceSeed]) -> str:
    lines = []
    for idx, place in enumerate(selected_places[:5], start=1):
        name = (place.name or "").strip() or "이름 없는 장소"
        address = (place.adress or "").strip() or "주소 정보 없음"
        pid = place.place_id if (place.place_id or 0) > 0 else "unknown"
        lines.append(f"{idx}. {name} (ID: {pid}) / 주소: {address}")
    return "\n".join(lines) if lines else "1. 이름 없는 장소 (ID: unknown) / 주소: 주소 정보 없음"


def render_auto_start_prompt(travel_duration: str, adult_count: int, child_count: int) -> str:
    duration = (travel_duration or "").strip() or "미정"
    adult = _normalize_count(adult_count)
    child = _normalize_count(child_count)
    return _render_prompt(
        "새 여행 계획 채팅을 시작한다.",
        COMMON_RESPONSE_RULES,
        AUTO_START_TRIP_CONTEXT_RULES.format(
            travel_duration=duration,
            adult_count=adult,
            child_count=child,
        ),
    )


def render_auto_start_place_prompt(selected_places: List[AutoStarterPlaceSeed]) -> str:
    return _render_prompt(
        "사용자가 북마크한 장소를 선택해 새 채팅을 시작했다.",
        COMMON_RESPONSE_RULES,
        AUTO_START_SELECTED_PLACES_RULES.format(
            selected_places_block=_format_selected_places_block(selected_places),
        ),
    )


def render_auto_start_combined_prompt(
    travel_duration: str,
    adult_count: int,
    child_count: int,
    selected_places: List[AutoStarterPlaceSeed],
) -> str:
    duration = (travel_duration or "").strip() or "미정"
    adult = _normalize_count(adult_count)
    child = _normalize_count(child_count)
    return _render_prompt(
        "사용자가 여행 기본 정보와 선택 장소를 함께 입력해 새 채팅을 시작했다.",
        COMMON_RESPONSE_RULES,
        AUTO_START_COMBINED_RULES.format(
            travel_duration=duration,
            adult_count=adult,
            child_count=child,
            selected_places_block=_format_selected_places_block(selected_places),
        ),
    )


def render_auto_start_greeting_prompt(prefs_info: str) -> str:
    return _render_prompt(
        "사용자는 새 여행 채팅을 시작했다.",
        COMMON_RESPONSE_RULES,
        AUTO_START_GREETING_RULES.format(prefs_info=prefs_info),
    )
