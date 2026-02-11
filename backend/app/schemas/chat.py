from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.orm import RoleType

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

class ChatRoomBase(BaseModel):
    title: str

class ChatRoomCreate(ChatRoomBase):
    pass

class ChatRoomResponse(ChatRoomBase):
    id: int
    user_id: int
    created_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True
