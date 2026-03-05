import os

import requests as req
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import db_manager
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.utils.error_handler import AppException, ErrorCode
from app.utils.security import get_current_user
from app.database.connection import db_manager

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_user_me(user_update: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    # 업데이트할 필드만 추출 (exclude_unset=True)
    update_data = user_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/reset-profile-picture", response_model=UserResponse)
def reset_user_profile_picture_to_google(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    if not current_user.social_access_token:
        raise AppException(ErrorCode.VALIDATION_ERROR, "No linked Google access token", 400)

    def fetch_google_picture(access_token: str):
        response = req.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            pic = data.get("picture")
            return pic if isinstance(pic, str) and pic.strip() else None
        return None

    picture = fetch_google_picture(current_user.social_access_token)

    if not picture and current_user.social_refresh_token:
        token_endpoint = "https://oauth2.googleapis.com/token"
        token_res = req.post(
            token_endpoint,
            data={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "refresh_token": current_user.social_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
        if token_res.status_code == 200:
            token_data = token_res.json()
            refreshed_access = token_data.get("access_token")
            if isinstance(refreshed_access, str) and refreshed_access.strip():
                current_user.social_access_token = refreshed_access
                picture = fetch_google_picture(refreshed_access)

    if not picture:
        raise AppException(ErrorCode.GOOGLE_AUTH_FAILED, "Failed to fetch Google profile image", 400)

    current_user.profile_picture = picture
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
