from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from fastapi import APIRouter, Depends

from app.database.connection import get_db
from app.models.hot_place import HotPlace
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/hot-places", tags=["hot-place"])


@router.get("", response_model=List[dict])
def get_hot_places(
    limit: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    hot_places 테이블에서 랜덤으로 limit개(기본 3개) 반환한다.
    """
    places = db.query(HotPlace).order_by(func.rand()).limit(limit).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "adress": p.adress,
            "feature": p.feature,
            "tag1": p.tag1,
            "tag2": p.tag2,
            "image_path": p.image_path,
        }
        for p in places
    ]
