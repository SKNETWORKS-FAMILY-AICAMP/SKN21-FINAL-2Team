from pydantic import BaseModel
from typing import Optional
from datetime import date as dt_date, datetime


class ReservationBase(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    date: Optional[dt_date] = None
    image_path: Optional[str] = None


class ReservationCreate(ReservationBase):
    pass


class ReservationUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    date: Optional[dt_date] = None
    image_path: Optional[str] = None


class ReservationResponse(ReservationBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
