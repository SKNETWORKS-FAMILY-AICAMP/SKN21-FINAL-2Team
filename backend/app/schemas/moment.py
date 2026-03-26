from datetime import date as dt_date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class MomentBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    entry_date: dt_date
    image_path: Optional[str] = None
    adress: Optional[str] = Field(default=None, max_length=255)
    longitude: Optional[float] = None
    latitude: Optional[float] = None


class MomentCreate(MomentBase):
    pass


class MomentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1)
    entry_date: Optional[dt_date] = None
    image_path: Optional[str] = None
    adress: Optional[str] = Field(default=None, max_length=255)
    longitude: Optional[float] = None
    latitude: Optional[float] = None


class MomentListItemResponse(BaseModel):
    id: int
    title: str
    content: str
    entry_date: dt_date
    image_path: Optional[str] = None
    adress: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MomentDetailResponse(MomentListItemResponse):
    user_id: int

    class Config:
        from_attributes = True
