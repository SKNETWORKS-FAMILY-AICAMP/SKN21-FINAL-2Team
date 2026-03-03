from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Float, func, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT

from app.models.orm import BaseModel
from app.models.enums import RoleType

class ChatRoom(BaseModel):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    history = Column(Text, nullable=True)
    user = relationship("User", back_populates="rooms")
    messages = relationship("ChatMessage", back_populates="room")
    adult_num = Column(Integer, nullable=True)
    child_num = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    
class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"))
    message = Column(Text)
    role = Column(Enum(RoleType), default=RoleType.human)
    # SQLite 테스트 환경에서도 테이블 생성이 가능하도록 기본은 Text, MySQL에서는 LONGTEXT 사용
    image_path = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    bookmark_yn = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    room = relationship("ChatRoom", back_populates="messages")
    places = relationship("ChatPlace", back_populates="message")


class ChatPlace(BaseModel):
    __tablename__ = "chat_places"

    id = Column(Integer, primary_key=True, index=True)
    messages_id = Column(Integer, ForeignKey("chat_messages.id"))
    place_id = Column(Integer, nullable=True)
    name = Column(String(255), nullable=True)
    adress = Column(String(255), nullable=True)
    image_path = Column(String(255), nullable=True)
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    bookmark_yn = Column(Boolean, default=False)

    message = relationship("ChatMessage", back_populates="places")

