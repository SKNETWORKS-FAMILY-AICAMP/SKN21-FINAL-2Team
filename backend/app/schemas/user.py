from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.orm import GenderType

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    gender: Optional[GenderType] = None
    
    
class UserUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[GenderType] = None
    actor_prefer_id: Optional[int] = None
    movie_prefer_id: Optional[int] = None
    drama_prefer_id: Optional[int] = None
    celeb_prefer_id: Optional[int] = None
    variety_prefer_id: Optional[int] = None
    with_yn: Optional[bool] = None
    dog_yn: Optional[bool] = None
    vegan_yn: Optional[bool] = None

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

class TokenData(BaseModel):
    email: Optional[str] = None

class GoogleLoginRequest(BaseModel):
    code: str # Google Auth Code

class RefreshRequest(BaseModel):
    refresh_token: str
