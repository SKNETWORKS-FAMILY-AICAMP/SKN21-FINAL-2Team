from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.enums import RoleType

class ChatMessageBase(BaseModel):
    message: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_path: Optional[str] = None # Base64 string for upload, URL for download
    bookmark_yn: Optional[bool] = False

class ChatMessageCreate(ChatMessageBase):
    room_id: int
    role: RoleType = RoleType.human

class ChatMessageResponse(ChatMessageBase):
    id: int
    room_id: int
    role: RoleType
    created_at: datetime

    class Config:
        from_attributes = True

class ChatPlaceBase(BaseModel):
    place_id: Optional[int] = None
    name: Optional[str] = None
    adress: Optional[str] = None
    image_path: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    boomark_yn: Optional[bool] = False


class ChatPlaceResponse(ChatPlaceBase):
    id: int
    messages_id: int

    class Config:
        from_attributes = True


class ChatRoomBase(BaseModel):
    title: str


class ChatRoomCreate(ChatRoomBase):
    pass


class ChatRoomResponse(ChatRoomBase):
    id: int
    user_id: int
    created_at: datetime
    history: Optional[str] = None
    adult_num: Optional[int] = None
    child_num: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True
