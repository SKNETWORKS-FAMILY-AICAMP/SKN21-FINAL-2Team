import sys
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.utils.security import get_current_user
from app.database.connection import db_manager
from app.models.user import User
from app.schemas.prefer import PreferResponse, SurveySubmitRequest
from app.schemas.user import UserResponse

# 선호도 조사 선택지 고정 데이터
SURVEY_DATA = [
    # 1. 여행 일정 타입
    {"type": "plan_prefer", "value": "빽빽한 일정"},
    {"type": "plan_prefer", "value": "느슨한 일정"},
    # 2. 여행 환경
    {"type": "vibe_prefer", "value": "붐비는 도시"},
    {"type": "vibe_prefer", "value": "한적한 자연"},
    # 3. 여행 관심사
    {"type": "places_prefer", "value": "맛집"},
    {"type": "places_prefer", "value": "역사적 명소"},
    {"type": "places_prefer", "value": "K-culture"},
]

router = APIRouter(prefix="/api/prefers", tags=["prefer"])


@router.get("", response_model=List[PreferResponse])
def read_prefers(
    prefer_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    선호도 조사 선택지 목록을 반환한다.
    type 쿼리 파라미터로 필터링 가능 (예: ?prefer_type=plan_prefer)
    """
    if prefer_type:
        return [item for item in SURVEY_DATA if item["type"] == prefer_type]
    return SURVEY_DATA


@router.patch("", response_model=UserResponse)
def submit_survey(
    survey: SurveySubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    """
    사용자가 선택한 선호도 조사 결과를 users 테이블에 저장한다.
    선택된 필드의 value 문자열을 해당 컬럼에 직접 저장하고 is_prefer=True로 업데이트.
    """
    update_data = survey.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    current_user.is_join = True
    current_user.is_prefer = True

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

