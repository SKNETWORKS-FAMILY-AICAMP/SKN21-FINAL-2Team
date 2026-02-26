from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.orm import GenderType

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    nickname: Optional[str] = None
    profile_picture: Optional[str] = None
    gender: Optional[GenderType] = None
    birthday: Optional[datetime] = None
    
    # Survey Prefers
    plan_prefer_id: Optional[int] = None
    member_prefer_id: Optional[int] = None
    transport_prefer_id: Optional[int] = None
    age_prefer_id: Optional[int] = None
    vibe_prefer_id: Optional[int] = None

    # Content Prefers
    movie_prefer_id: Optional[int] = None
    drama_prefer_id: Optional[int] = None
    variety_prefer_id: Optional[int] = None

    country_code: Optional[str] = None
    is_join: Optional[bool] = None
    is_prefer: Optional[bool] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[GenderType] = None
    birthday: Optional[datetime] = None
    
    plan_prefer_id: Optional[int] = None
    member_prefer_id: Optional[int] = None
    transport_prefer_id: Optional[int] = None
    age_prefer_id: Optional[int] = None
    vibe_prefer_id: Optional[int] = None

    movie_prefer_id: Optional[int] = None
    drama_prefer_id: Optional[int] = None
    variety_prefer_id: Optional[int] = None

    country_code: Optional[str] = None
    is_join: Optional[bool] = None
    is_prefer: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    social_provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str # Add refresh token
    token_type: str
    is_join: bool = False
    profile_picture: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None

class GoogleLoginRequest(BaseModel):
    code: str # Google Auth Code

class RefreshRequest(BaseModel):
    refresh_token: str
