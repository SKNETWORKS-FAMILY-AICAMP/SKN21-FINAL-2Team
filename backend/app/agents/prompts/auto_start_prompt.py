from typing import List

from app.schemas.chat import AutoStarterPlaceSeed
from app.models.enums import LanguageType
from app.agents.prompts.prompts import get_language_instruction

COMMON_RESPONSE_RULES = """
[공통 응답 규약]
- 위 응답 언어로 답변한다.
- 답변은 간결하게 유지한다. 전체 응답은 300자(한국어 기준) 이내로 작성하며, 불필요한 부연 설명이나 반복 문장은 생략한다.
- 본 대화의 여행 범위는 서울로 고정한다.
- 모든 제안/선택지는 반드시 서울 안에서 즐길 수 있는 내용만 제시한다.
- '확정 일정'이 아니라, 시작 인사말과 함께 여행 계획이나 장소 추천의 초안을 제시한다. 상세 일정, 시간대별 플랜, 확정 동선‧예약 전제 문장은 사용하지 않는다.
- 제안은 가설적 추천 톤(강제X, 단정X, 예: 많이 찾는 편, 추천드림)으로 작성하세요.
- 제안의 이유(선택지 설명)는 입력된 일정, 인원 정보 및 최신 서울 트렌드와 사용자 선호도를 기반해 1~2문장 서술합니다.
- 한국 서울 여행 트렌드는 완곡하게 반영한다(예: 요즘 많이 찾는 편).
- 반드시 서울 도시 내에서만 즐길 수 있는 선택지만 제시합니다(서울 이외 언급 금지).
- 모든 답변(첫 응답 포함)은 아래 순서를 반드시 지킵니다:
  1) 인사
  2) 제안 요약
  3) 선택지 최소 2개(권역 또는 테마 기준 일수 배분)
  4) 선택형 질문 최소 1개(문단 마지막, 다음 선택 관련)

사용자 선호도 (참고):
{prefs_info}
"""

AUTO_START_TRIP_CONTEXT_RULES = """
서울 여행 일정 및 인원(성인/어린이) 정보에 따라, 서울 내 권역 또는 테마 기반으로 일수 배분을 제안하시오.

- 여행 날짜({travel_duration}), 성인 인원({adult_count}명), 어린이 인원({child_count}명) 정보를 참조하시오.
- 각 제안은 서울 내 권역(예: 홍대/성수/강남/잠실/종로/북촌 등) 혹은 서울 테마(예: 음식, 역사, 가족 등)를 기준으로 며칠 배분하면 좋을지 이동 동선의 피로도 관점과 함께 설명하세요.
"""

AUTO_START_SINGLE_PLACE_RULES = """
[모드 지침: 선택 장소 1개(single_place)]
선택 장소:
{selected_places_block}

작성 방식:
- 선택한 장소를 중심으로 해당 장소의 특징·매력을 짧게 소개한다.
- 선택 장소 주변에서 함께 즐길 수 있는 다양한 카테고리(맛집·카페·관광지·전시·쇼핑 등)를
  2~3개 큐레이션해 제안한다.
- 같은 카테고리로만 채우지 말고 반드시 2가지 이상의 카테고리를 섞어 추천한다.
- 반일 코스 단위로 가볍게 엮어서 제안한다.
- 마지막 문장은 '어떤 코스가 끌리세요?' 형태의 선택형 질문으로 끝낸다.
"""

AUTO_START_MULTI_PLACE_RULES = """
[모드 지침: 선택 장소 2개 이상(multi_place)]
선택 장소 목록:
{selected_places_block}

작성 방식:
- 선택 장소들을 반드시 포함하여 최적 여행 동선을 제안한다.
- 선택 장소 사이에 자연스럽게 들를 수 있는 중간 장소(코엑스 or 잠실 or 홍대 등)를 1~2개 추가로 제안한다.
- 선택된 장소 외 특정 상세 장소 언급 금지(예: 만향오향족발 홍대점, 딥커피 등).
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
- 선택 장소 배치를 반드시 결합한 여행 계획 초안 버전을 제시한다.
- 왜 이 배치를 추천하는지 서울 내 이동 효율/취향 관점으로 짧게 설명한다.
"""

AUTO_START_GREETING_RULES = """
[모드 지침: 정보 없음(greeting)]
일정 제안말고 한국 서울에서 사용자 선호도에 맞는 인사로 시작한다.

작성 방식:
- 아래 축에서 빠르게 선택할 수 있도록 2~3개 선택지를 제안한다.
  - 서울 여행 분위기(예: 활기/여유)
  - 서울 관심 테마(예: K-pop, 미식, 전시, 한강 야경, 로컬 골목)
  - 서울 동행 형태(혼자/친구/가족)
- 마지막 문장은 반드시 '어떤 걸 자세히 알아볼까요?' 형태의 질문으로 끝낸다.
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
    for idx, place in enumerate(selected_places, start=1):
        name = (place.name or "").strip() or "이름 없는 장소"
        address = (place.adress or "").strip() or "주소 정보 없음"
        pid = place.place_id if (place.place_id or 0) > 0 else "unknown"
        line = f"{idx}. {name} (ID: {pid}) / 주소: {address}"
        if place.description and place.description.strip():
            line += f" / 설명: {place.description.strip()}"
        lines.append(line)
    return "\n".join(lines) if lines else "1. 이름 없는 장소 (ID: unknown) / 주소: 주소 정보 없음"


def render_auto_start_prompt(language_type: LanguageType, prefs_info: str, travel_duration: str, adult_count: int, child_count: int) -> str:
    duration = (travel_duration or "").strip() or "미정"
    adult = _normalize_count(adult_count)
    child = _normalize_count(child_count)
    return _render_prompt(
        get_language_instruction(language_type),
        "새 여행 계획 채팅을 시작한다.",
        AUTO_START_TRIP_CONTEXT_RULES.format(
            travel_duration=duration,
            adult_count=adult,
            child_count=child,
        ),
        COMMON_RESPONSE_RULES.format(
            prefs_info=prefs_info
        ),
    )


def render_auto_start_place_prompt(language_type: LanguageType, prefs_info: str, selected_places: List[AutoStarterPlaceSeed]) -> str:
    places_block = _format_selected_places_block(selected_places)
    if len(selected_places) == 1:
        mode_rules = AUTO_START_SINGLE_PLACE_RULES.format(
            selected_places_block=places_block
        )
        intro = "사용자가 원하는 장소 1개를 선택해 새 채팅을 시작했다."
    else:
        mode_rules = AUTO_START_MULTI_PLACE_RULES.format(
            selected_places_block=places_block
        )
        intro = "사용자가 원하는 장소 여러 개를 선택해 새 채팅을 시작했다."
    return _render_prompt(
        get_language_instruction(language_type),
        intro,
        mode_rules,
        COMMON_RESPONSE_RULES.format(
            prefs_info=prefs_info
        ),
    )


def render_auto_start_combined_prompt(
    language_type: LanguageType,
    prefs_info: str,
    travel_duration: str,
    adult_count: int,
    child_count: int,
    selected_places: List[AutoStarterPlaceSeed],
) -> str:
    duration = (travel_duration or "").strip() or "미정"
    adult = _normalize_count(adult_count)
    child = _normalize_count(child_count)
    return _render_prompt(
        get_language_instruction(language_type),
        "사용자가 여행 기본 정보와 원하는 장소를 함께 입력해 새 채팅을 시작했다.",
        AUTO_START_COMBINED_RULES.format(
            travel_duration=duration,
            adult_count=adult,
            child_count=child,
            selected_places_block=_format_selected_places_block(selected_places),
        ),
        COMMON_RESPONSE_RULES.format(
            prefs_info=prefs_info
        ),
    )


def render_auto_start_greeting_prompt(language_type: LanguageType, prefs_info: str) -> str:
    return _render_prompt(
        get_language_instruction(language_type),
        "사용자는 새 여행 채팅을 시작했다.",
        AUTO_START_GREETING_RULES,
        COMMON_RESPONSE_RULES.format(
            prefs_info=prefs_info
        ),
    )
