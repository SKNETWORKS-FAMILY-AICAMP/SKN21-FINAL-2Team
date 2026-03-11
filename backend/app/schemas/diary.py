from datetime import date as dt_date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DiaryLinkedRoomResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class DiaryLinkedPlaceResponse(BaseModel):
    id: int
    chat_place_id: Optional[int] = None
    place_id: Optional[int] = None
    name: Optional[str] = None
    adress: Optional[str] = None
    image_path: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DiaryLinkedPlaceInput(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    adress: str = Field(min_length=1, max_length=255)
    image_path: Optional[str] = None
    longitude: float
    latitude: float
    place_id: Optional[int] = None
    chat_place_id: Optional[int] = None


class DiaryBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    entry_date: dt_date
    cover_image_path: Optional[str] = None
    linked_places: List[DiaryLinkedPlaceInput] = Field(default_factory=list, max_length=5)


class DiaryCreate(DiaryBase):
    pass


class DiaryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1)
    entry_date: Optional[dt_date] = None
    cover_image_path: Optional[str] = None
    linked_places: Optional[List[DiaryLinkedPlaceInput]] = Field(default=None, max_length=5)


class DiaryListItemResponse(BaseModel):
    id: int
    title: str
    content: str
    entry_date: dt_date
    cover_image_path: Optional[str] = None
    linked_places_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DiaryDetailResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    entry_date: dt_date
    cover_image_path: Optional[str] = None
    linked_places_count: int = 0
    linked_chat_room: Optional[DiaryLinkedRoomResponse] = None
    linked_places: List[DiaryLinkedPlaceResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
