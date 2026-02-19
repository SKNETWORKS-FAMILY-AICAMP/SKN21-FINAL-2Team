from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.connection import get_db
from app.models.prefer import Prefer
from app.models.user import User
from app.schemas.prefer import PreferResponse

router = APIRouter(prefix="/api/prefers", tags=["prefer"])


@router.get("", response_model=List[PreferResponse])
def read_prefers(
    prefer_type: Optional[str] = Query(default=None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Prefer)
    if prefer_type:
        query = query.filter(Prefer.type == prefer_type)
    return query.order_by(Prefer.type.asc(), Prefer.id.asc()).all()
