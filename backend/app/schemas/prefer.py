from pydantic import BaseModel
from typing import Optional


class PreferResponse(BaseModel):
    type: str
    value: str


class SurveySubmitRequest(BaseModel):
    plan_prefer: Optional[str] = None
    vibe_prefer: Optional[str] = None
    places_prefer: Optional[str] = None
