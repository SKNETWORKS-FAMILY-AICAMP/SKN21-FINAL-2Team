from pydantic import BaseModel
from typing import Optional
from datetime import date


class ReservationBase(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    date: Optional[date] = None
    image_path: Optional[str] = None


class ReservationCreate(ReservationBase):
    pass


class ReservationResponse(ReservationBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
