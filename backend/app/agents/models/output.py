from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# # Intent Output
class IntentType(str, Enum):
    PLACE_INQUIRY = "PLACE_INQUIRY" # 장소 검색
    TRIP_PLANNING = "TRIP_PLANNING" # 여행 계획
    BOOKING = "BOOKING" # 예약
    REVIEWS = "REVIEWS" # 리뷰
    BUDGET = "BUDGET"   # 예산
    ITINERARY_SAVE = "ITINERARY_SAVE" # 일정 저장
    INFO_QA = "INFO_QA" # 정보 검색
    IMAGE_SIMILAR = "IMAGE_SIMILAR" # 이미지 검색


class InputType(str, Enum):
    TEXT = "text"   
    IMAGE = "image"
    BOTH = "both"


class IntentSlots(BaseModel):
    input_type: InputType = Field(default=InputType.TEXT, description="사용자 입력 데이터 타입")
    location: Optional[str] = Field(default=None, description="여행지 (도시 | 지역)")
    category: Optional[Literal["관광지", "문화시설", "축제공연행사", "레포츠", "숙박", "음식점"]] = Field(default=None, description="사용자 입력에서 추출된 카테고리")
    dates: Optional[str] = Field(default=None, description="여행 날짜 (내일 | yyyy-mm-dd)")
    duration: Optional[str] = Field(default=None, description="여행 기간 (1박 2일 | 3일)")
    party_size: Optional[int] = Field(default=None, description="인원수")
    budget_level: Optional[Literal["low", "medium", "high"]] = Field(default=None, description="예산 범위 (가성비/저렴/싸게: low, 보통/적당히: medium, 럭셔리/비싸도: high)")
    nice_to_have: Optional[str] = Field(default=None, description="있으면 좋은 조건")


class IntentOutput(BaseModel):
    intents: List[IntentType]
    primary_intent: IntentType
    slots: IntentSlots
    summary_title: Optional[str] = Field(default=None, description="사용자의 질문 내용을 10자 이내로 요약한 문장 (현재 채팅방 제목으로 사용)")
    summary_message: str = Field(default="", description="대화 요약")


# # Planner Output
class PlannerItineraryItem(BaseModel):
    """여행 일정 항목"""
    day: int = Field(description="일차 (당일치기면 1)")
    time_slot: str = Field(description="morning | afternoon | evening")
    activity: str = Field(description="활동 설명")
    search_query: str = Field(description="장소 검색용 키워드")
    category: str = Field(description="관광지 | 문화시설 | 축제공연행사 | 레포츠 | 숙박 | 음식점")


class PlannerOutput(BaseModel):
    """Planner LLM 출력 스키마"""
    itinerary: List[PlannerItineraryItem] = Field(description="시간순/일차별 여행 일정")
    missing_slots: List[str] = Field(default_factory=list, description="부족한 정보 목록")
    followup_question: Optional[str] = Field(
        default=None,
        description=(
            "부족한 정보가 있을 때, 사용자의 대화 맥락과 취향을 고려한 자연스럽고 친근한 후속 질문. "
            "예: '혹시 서울 여행은 며칠 정도 생각하고 계세요? 1박2일이면 핵심 명소 위주로, "
            "2박3일이면 숨은 명소까지 넣어볼 수 있어요 😊'"
        )
    )
