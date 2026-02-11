from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Float, func, Boolean
from sqlalchemy.orm import relationship

from app.models.orm import BaseModel
from app.models.enums import RoleType

class ChatRoom(BaseModel):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="rooms")
    messages = relationship("ChatMessage", back_populates="room")

class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"))
    message = Column(Text)
    role = Column(Enum(RoleType), default=RoleType.human)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_path = Column(Text, nullable=True)
    bookmark_yn = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    room = relationship("ChatRoom", back_populates="messages")
