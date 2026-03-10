from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.models.orm import BaseModel


class DiaryEntry(BaseModel):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    entry_date = Column(Date, nullable=False, index=True)
    cover_image_path = Column(String(1000), nullable=True)
    linked_chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="diary_entries")
    linked_chat_room = relationship("ChatRoom", back_populates="diary_entries")
    linked_places = relationship(
        "DiaryEntryPlace",
        back_populates="entry",
        cascade="all, delete-orphan",
    )


class DiaryEntryPlace(BaseModel):
    __tablename__ = "diary_entry_places"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("diary_entries.id"), nullable=False, index=True)
    chat_place_id = Column(Integer, ForeignKey("chat_places.id"), nullable=True)
    place_id = Column(Integer, nullable=True)
    name = Column(String(255), nullable=True)
    adress = Column(String(255), nullable=True)
    image_path = Column(String(1000), nullable=True)
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    entry = relationship("DiaryEntry", back_populates="linked_places")
