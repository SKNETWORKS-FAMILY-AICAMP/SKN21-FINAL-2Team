from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database.connection import get_db
from app.models.user import User
from app.schemas.user import UserResponse, Token, GoogleLoginRequest, RefreshRequest
from app.core.security import create_access_token, create_refresh_token, verify_refresh_token, verify_google_auth_code

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/google/callback",  response_model=Token)
def login_google(
    request: GoogleLoginRequest, 
    response: Response,                  
    db: Session = Depends(get_db),
):
    # 1. Google Auth Code 교환 및 검증
    # verify_google_auth_code는 {id_info, access_token, refresh_token, ...} 반환
    auth_result = verify_google_auth_code(request.code)
    if not auth_result:
        raise HTTPException(status_code=400, detail="Invalid Google Auth Code (Unknown Error)")
        
    if "error" in auth_result:
        raise HTTPException(status_code=400, detail=f"Google Auth Error: {auth_result['error']}")
    
    id_info = auth_result["id_info"]
    social_access_token = auth_result["access_token"]
    social_refresh_token = auth_result.get("refresh_token") # 없을 수도 있음

    email = id_info.get("email")
    name = id_info.get("name")
    
    # 2. 사용자 확인 또는 생성
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # 신규 사용자
        user = User(
            email=email,
            name=name,
            social_provider="google",
            social_id=id_info.get("sub"),
            social_access_token=social_access_token,
            social_refresh_token=social_refresh_token
        )
        db.add(user)
        db.commit()
    else:
        # 기존 사용자: 토큰 업데이트
        user.social_access_token = social_access_token
        if social_refresh_token:
            user.social_refresh_token = social_refresh_token
        db.add(user)
        db.commit()
        
    db.refresh(user)

    # 3. 앱 전용 토큰 발급 (Access + Refresh)
    access_token = create_access_token(user.email)
    refresh_token = create_refresh_token(user.email)
    
    # refresh_token을 쿠키로 저장 (브라우저가 보지 못하게)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,        # 배포(HTTPS)면 True
        samesite="lax",      # 프론트/백 도메인 분리 크면 "none" + secure 필요할 수 있음
        max_age=60 * 60 * 24 * 7,
        path="/",            # 보통 /
    )

    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    refresh_token = request.refresh_token

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Empty refresh token")
    
    # 1. 리프레시 토큰 검증
    email = verify_refresh_token(refresh_token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # 2. 사용자 확인
    user = db.query(User).filter(User.email == email).first()
    if not user:
         raise HTTPException(status_code=401, detail="User not found")
         
    # 3. 새로운 액세스 토큰 발급
    access_token = create_access_token(user.email)
    new_refresh_token = create_refresh_token(user.email)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(response: Response):
    # Refresh 토큰 쿠키 삭제로 사실상 로그아웃 처리
    response.delete_cookie(
        key="refresh_token",
        path="/",
    )
    return {"message": "logged out"}
