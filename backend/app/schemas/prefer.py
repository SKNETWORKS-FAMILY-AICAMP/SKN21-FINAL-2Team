from pydantic import BaseModel
from typing import Optional


class PreferResponse(BaseModel):
    id: int
    category: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None
    image_path: Optional[str] = None

    class Config:
        from_attributes = True
