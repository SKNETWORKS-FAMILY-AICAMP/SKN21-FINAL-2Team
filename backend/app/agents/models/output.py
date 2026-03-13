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
    POPUP_STORE = "팝업스토어"

    @classmethod
    def description(cls) -> str:
        """카테고리 값과 대표 키워드 예시를 LLM에 전달하기 위한 설명 문자열."""
        hints = {
            "관광지":      "관광명소, 유적지, 테마파크, 해수욕장, 섬, 자연경관, 궁",
            "문화시설":    "박물관, 미술관, 도서관, 공연장, 전시관, 영화관",
            "축제공연행사": "축제, 공연, 콘서트, 이벤트, 전시회, 페스티벌",
            "레포츠":      "스포츠, 등산, 서핑, 수영, 캠핑, 번지점프, 패러글라이딩, 야외 레저",
            "숙박":        "호텔, 펜션, 게스트하우스, 리조트, 모텔, 에어비앤비",
            "음식점":      "음식점, 카페, 식당, 레스토랑, 맛집, 한식, 양식, 일식, 비빔밥, 분식, 치킨, 피자",
            "팝업스토어":  "팝업스토어, 브랜드 팝업, 한정판 전시 매장, 굿즈",
        }
        lines = [f"- {item.value}: {hints.get(item.value, item.name)}" for item in cls]
        return "\n".join(lines)


class IntentLocation(BaseModel):
    name: Optional[str] = Field(default=None, description="구체적인 도시나 지역 여행지")
    lat: Optional[float] = Field(default=None, description="location 위도")
    long: Optional[float] = Field(default=None, description="location 경도")


class IntentSlots(BaseModel):
    input_type: InputType = Field(default=InputType.TEXT, description="사용자 입력 데이터 타입")
    location: Optional[IntentLocation] = Field(default=None, description="도시나 지역 여행지, 주소등 장소 정보")
    categories: Optional[List[CategoryType]] = Field(default=None, description="사용자 입력에서 추출된 여러 카테고리 리스트")
    dates: Optional[str] = Field(default=None, description="여행 날짜 (내일 | yyyy-mm-dd)")
    duration: Optional[str] = Field(default=None, description="여행 기간 (1박 2일 | 3일)")
    party_size: Optional[int] = Field(default=None, description="인원수")
    budget_level: Optional[Literal["low", "medium", "high"]] = Field(default=None, description="예산 범위 (가성비/저렴/싸게: low, 보통/적당히: medium, 럭셔리/비싸도: high)")
    nice_to_have: Optional[str] = Field(default=None, description="있으면 좋은 조건")


class IntentOutput(BaseModel):
    update_user_input: Optional[str] = Field(
        default=None,
        description="사용자 입력이 단답이거나 의도가 불명확할 때, 직전 대화 맥락을 반영해 보강한 사용자 요청 문장. 이 값이 있으면 아래 intents/slots는 반드시 이 문장 기준으로 추출하십시오.",
    )
    intents: List[IntentType] = Field(description="사용자의 의도")
    primary_intent: IntentType = Field(description="사용자의 주요 의도")
    slots: IntentSlots = Field(description="사용자 입력에서 추출된 슬롯")
    summary_title: Optional[str] = Field(default=None, description="사용자의 질문 내용을 10자 이내로 요약한 문장 (현재 채팅방 제목으로 사용)")
    summary_message: str = Field(default="", description="대화 요약")


# # Planner Output
class PlannerNeedType(str, Enum): # 계획 필수 타입 
    DATES = "여행 날짜"
    PARTY_SIZE = "여행 인원"


class PlannerItineraryItem(BaseModel):
    """여행 일정 항목"""
    day: int = Field(description="일차 (당일치기면 1)")
    time_slot: Literal["morning", "afternoon", "evening"] = Field(description="시간대")
    activity: str = Field(description="활동 설명")
    category: CategoryType = Field(description="장소 카테고리")
    search_query: str = Field(description="Qdrant 검색에 유리한 구체적 한국어 키워드 (사용자 선호 반영)")


class PlannerOutput(BaseModel):
    """Planner LLM 출력 스키마"""
    itinerary: List[PlannerItineraryItem] = Field(description="최소 1개 이상의 시간순/일차별 여행 일정")
    missing_slots: List[PlannerNeedType] = Field(default_factory=list, description="일정 계획 진행에 반드시 필요한 누락 정보 목록 (예: 여행 인원)")
    followup_question: str = Field(
        description=(
            "항상 생성되는 후속 질문 1문장. duration 누락 시 여행 기간을 재질문하고 문장에 반드시 '여행일정'을 포함"
        )
    )


class PlaceInfo(BaseModel):
    """Executor 노드가 구성한 장소 정보 (DB 저장 전 중간 표현)"""
    place_id: str = ""       # contentid (Qdrant) 또는 "" (Tavily)
    name: str = ""
    address: str = ""        # ORM 컬럼명은 adress(오타) — chat.py에서만 매핑
    image_path: str = ""
    longitude: float = 0.0
    latitude: float = 0.0
