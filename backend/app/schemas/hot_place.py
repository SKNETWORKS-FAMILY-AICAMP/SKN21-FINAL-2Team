from pydantic import BaseModel
from typing import Optional


class HotPlaceBase(BaseModel):
    name: Optional[str] = None
    adress: Optional[str] = None
    feature: Optional[str] = None
    tag1: Optional[str] = None
    tag2: Optional[str] = None
    image_path: Optional[str] = None


class HotPlaceResponse(HotPlaceBase):
    id: int

    class Config:
        from_attributes = True
