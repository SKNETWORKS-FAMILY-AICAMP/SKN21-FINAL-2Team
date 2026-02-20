from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship

from app.models.orm import BaseModel
from app.models.enums import GenderType
from app.models.prefer import Prefer

class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    nickname = Column(String(255), nullable=True)
    profile_picture = Column(String(1000), nullable=True)
    gender = Column(Enum(GenderType))
    birthday = Column(DateTime, nullable=True)
    social_provider = Column(String(255))
    social_id = Column(String(255), unique=True)
    social_access_token = Column(String(255), nullable=True)
    social_refresh_token = Column(String(255), nullable=True)
    
    actor_prefer_id = Column(Integer, ForeignKey("prefers.id"))
    movie_prefer_id = Column(Integer, ForeignKey("prefers.id"))
    drama_prefer_id = Column(Integer, ForeignKey("prefers.id"))
    celeb_prefer_id = Column(Integer, ForeignKey("prefers.id"))
    variety_prefer_id = Column(Integer, ForeignKey("prefers.id"))

    with_yn = Column(Boolean, nullable=True)
    dog_yn = Column(Boolean, nullable=True)
    vegan_yn = Column(Boolean, nullable=True)
    country_code = Column(String(10), nullable=True, comment="Currency Code for Budget")
    is_join = Column(Boolean, default=False)
    is_prefer = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    actor_prefer = relationship(Prefer, foreign_keys=[actor_prefer_id])
    movie_prefer = relationship(Prefer, foreign_keys=[movie_prefer_id])
    drama_prefer = relationship(Prefer, foreign_keys=[drama_prefer_id])
    celeb_prefer = relationship(Prefer, foreign_keys=[celeb_prefer_id])
    variety_prefer = relationship(Prefer, foreign_keys=[variety_prefer_id])
    
    rooms = relationship("ChatRoom", back_populates="user")
