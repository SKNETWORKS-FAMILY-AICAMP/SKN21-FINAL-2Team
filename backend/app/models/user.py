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
