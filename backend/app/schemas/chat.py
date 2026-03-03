from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal
from datetime import datetime, date
from app.models.enums import RoleType

class ChatMessageBase(BaseModel):
    message: str
    latitude: float = 0.0
    longitude: float = 0.0
    image_path: Optional[str] = None # Base64 string for upload, URL for download

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def _normalize_coords(cls, value):
        if value in (None, "", 0, 0.0):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

class ChatMessageCreate(ChatMessageBase):
    room_id: int
    role: RoleType = RoleType.human
    save_user_message: bool = True

class ChatRoomBase(BaseModel):
    title: str


class ChatRoomCreate(ChatRoomBase):
    pass


class ChatPlaceBase(BaseModel):
    place_id: int = 0
    name: Optional[str] = None
    adress: Optional[str] = None
    image_path: Optional[str] = None
    longitude: float = 0.0
    latitude: float = 0.0
    bookmark_yn: Optional[bool] = False

    @field_validator("place_id", mode="before")
    @classmethod
    def _normalize_place_id(cls, value):
        if value in (None, "", 0, 0.0):
            return 0
        try:
            parsed = int(value)
            return parsed if parsed > 0 else 0
        except (TypeError, ValueError):
            return 0

    @field_validator("longitude", "latitude", mode="before")
    @classmethod
    def _normalize_place_coords(cls, value):
        if value in (None, "", 0, 0.0):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class ChatPlaceResponse(ChatPlaceBase):
    id: int
    messages_id: int

    class Config:
        from_attributes = True


class ChatMessageResponse(ChatMessageBase):
    id: int
    room_id: int
    role: RoleType
    created_at: datetime
    places: List[ChatPlaceResponse] = []

    class Config:
        from_attributes = True


class ChatRoomResponse(ChatRoomBase):
    id: int
    user_id: int
    created_at: datetime
    bookmark_yn: bool = False
    history: Optional[str] = None
    adult_num: Optional[int] = None
    child_num: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True


class BookmarkedRoomResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    bookmark_yn: bool = False
    latest_message_preview: Optional[str] = None


class BookmarkedPlaceResponse(BaseModel):
    id: int
    place_id: int = 0
    name: Optional[str] = None
    adress: Optional[str] = None
    image_path: Optional[str] = None
    longitude: float = 0.0
    latitude: float = 0.0
    bookmark_yn: bool = False
    messages_id: int
    room_id: int
    room_title: str

    @field_validator("place_id", mode="before")
    @classmethod
    def _normalize_bookmarked_place_id(cls, value):
        if value in (None, "", 0, 0.0):
            return 0
        try:
            parsed = int(value)
            return parsed if parsed > 0 else 0
        except (TypeError, ValueError):
            return 0

    @field_validator("longitude", "latitude", mode="before")
    @classmethod
    def _normalize_bookmarked_place_coords(cls, value):
        if value in (None, "", 0, 0.0):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


AutoStartMode = Literal["trip_context", "selected_places", "combined", "greeting"]


class AutoStarterTripContext(BaseModel):
    travel_duration: str = ""
    adult_count: int = 0
    child_count: int = 0

    @field_validator("adult_count", "child_count", mode="before")
    @classmethod
    def _normalize_count(cls, value):
        try:
            parsed = int(value)
            return parsed if parsed >= 0 else 0
        except (TypeError, ValueError):
            return 0


class AutoStarterPlaceSeed(BaseModel):
    name: Optional[str] = None
    adress: Optional[str] = None
    place_id: int = 0

    @field_validator("place_id", mode="before")
    @classmethod
    def _normalize_place_id_seed(cls, value):
        try:
            parsed = int(value)
            return parsed if parsed > 0 else 0
        except (TypeError, ValueError):
            return 0


class AutoStartChatRoomRequest(BaseModel):
    mode: AutoStartMode
    trip_context: Optional[AutoStarterTripContext] = None
    selected_places: Optional[List[AutoStarterPlaceSeed]] = None
    save_user_message: bool = False
