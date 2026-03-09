from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# # Intent Output
class IntentType(str, Enum):
    GENERAL = "GENERAL" # 일반
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


class CategoryType(str, Enum):
    TOURIST_ATTRACTION = "관광지"
    CULTURAL_FACILITY = "문화시설"
    FESTIVAL_PERFORMANCE_EVENT = "축제공연행사"
    LEISURE = "레포츠"
    ACCOMMODATION = "숙박"
    RESTAURANT = "음식점"

class PlannerNeedType(str, Enum): # 계획 필수 타입 
    DATES = "여행 날짜"
    PARTY_SIZE = "여행 인원"


class IntentSlots(BaseModel):
    input_type: InputType = Field(default=InputType.TEXT, description="사용자 입력 데이터 타입")
    location: Optional[str] = Field(default=None, description="구체적인 도시나 지역 여행지")
    category: Optional[CategoryType] = Field(default=None, description="사용자 입력에서 추출된 카테고리")
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
    time_slot: Literal["morning", "afternoon", "evening"] = Field(description="시간대")
    activity: str = Field(description="활동 설명")
    search_query: str = Field(description="Qdrant 검색에 유리한 구체적 한국어 키워드 (사용자 선호 반영)")
    category: CategoryType = Field(description="장소 카테고리")


class PlannerOutput(BaseModel):
    """Planner LLM 출력 스키마"""
    itinerary: List[PlannerItineraryItem] = Field(description="최소 1개 이상의 시간순/일차별 여행 일정")
    missing_slots: List[PlannerNeedType] = Field(default_factory=list, description="일정 계획 진행에 반드시 필요한 누락 정보 목록 (예: 여행 인원)")
    followup_question: str = Field(
        description=(
            "항상 생성되는 후속 질문 1문장. duration 누락 시 여행 기간을 재질문하고 문장에 반드시 '여행일정'을 포함"
        )
    )
