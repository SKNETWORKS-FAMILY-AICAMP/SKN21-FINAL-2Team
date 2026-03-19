from sqlalchemy import Column, Integer, String, Enum, DateTime, Date, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship

from app.models.orm import BaseModel
from app.models.enums import GenderType, LanguageType

# 국적별 여행 선호 경향 (테스트용 하드코딩)
# level 1: 여행 스타일, level 2: + 음식, level 3: + 선호 지역
NATIONALITY_HINTS = {
    "CN": {
        "style": "K-콘텐츠 체험·쇼핑(올리브영·다이소)·SNS 인증샷 중심, 효율적 동선 선호",
        "food": "길거리 음식(떡볶이·붕어빵), 매콤·짭짤한 한식(삼겹살·부대찌개) 선호",
        "area": "성수·한남·연남·광장시장·한강",
    },
    "JP": {
        "style": "감성 카페 투어·K-Beauty·디자이너 브랜드 쇼핑, 슬로우 여행",
        "food": "정갈한 음식(비빔밥·불고기·삼계탕)·디저트 선호, 매운 음식 못 먹음",
        "area": "성수·한남·서촌·삼청동",
    },
    "US": {
        "style": "숨은 명소 탐방·자연(등산)·역사 문화 체험, 여유로운 일정",
        "food": "전통 한식(된장찌개·김밥·생선구이) 선호, 매운 음식 못 먹음",
        "area": "성수·한남·북촌·용산·북한산",
    },
}

# 테스트 레벨 설정: 1 = 스타일만, 2 = +음식, 3 = +선호지역
NATIONALITY_HINT_LEVEL = 3


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    nickname = Column(String(255), nullable=True)
    profile_picture = Column(String(1000), nullable=True)
    gender = Column(Enum(GenderType))
    social_provider = Column(String(255))
    social_id = Column(String(255), unique=True)
    social_access_token = Column(String(255), nullable=True)
    social_refresh_token = Column(String(255), nullable=True)

    # 선호도 조사 및 특이사항
    plan_prefer = Column(String(255), nullable=True)
    vibe_prefer = Column(String(255), nullable=True)
    places_prefer = Column(String(255), nullable=True)
    extra_prefer1 = Column(String(255), nullable=True)
    extra_prefer2 = Column(String(255), nullable=True)
    extra_prefer3 = Column(String(255), nullable=True)

    country_code = Column(String(10), nullable=True, comment="ISO Country Code")
    birthday = Column(Date, nullable=True, comment="생년월일")
    language = Column(Enum(LanguageType), default=LanguageType.en, nullable=False, comment="UI Language Preference")
    is_join = Column(Boolean, default=False)
    is_prefer = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    rooms = relationship("ChatRoom", back_populates="user")
    reservations = relationship("Reservation", back_populates="user")
    diary_entries = relationship("DiaryEntry", back_populates="user")

    def build_preferences(self) -> str:
        """
        prefs_info 문자열을 반환합니다.
        """

        lines = []

        if self.plan_prefer:
            lines.append(f"- 여행 일정 스타일: **{self.plan_prefer}**")
        if self.vibe_prefer:
            lines.append(f"- 선호 여행 환경: **{self.vibe_prefer}**")
        if self.places_prefer:
            lines.append(f"- 관심 장소 유형: **{self.places_prefer}**")
        
        # 추가 선호도 정보
        if self.extra_prefer1:
            lines.append(f"- 추가 선호도 1: {self.extra_prefer1}")
        if self.extra_prefer2:
            lines.append(f"- 추가 선호도 2: {self.extra_prefer2}")
        if self.extra_prefer3:
            lines.append(f"- 추가 선호도 3: {self.extra_prefer3}")

        # 국적별 여행 선호 경향
        if self.country_code and self.country_code in NATIONALITY_HINTS:
            hint = NATIONALITY_HINTS[self.country_code]
            parts = [f"여행 스타일: {hint['style']}"]
            if NATIONALITY_HINT_LEVEL >= 2:
                parts.append(f"음식: {hint['food']}")
            if NATIONALITY_HINT_LEVEL >= 3:
                parts.append(f"선호 지역: {hint['area']}")
            lines.append(f"- 국적별 여행 선호 경향: {' / '.join(parts)}")

        return "\n".join(lines) if lines else "특별한 선호도 정보 없음"
