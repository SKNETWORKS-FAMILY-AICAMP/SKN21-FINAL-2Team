from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship

from app.models.orm import BaseModel
from app.models.enums import GenderType
from app.models.country import Country

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

        return "\n".join(lines) if lines else "특별한 선호도 정보 없음"
