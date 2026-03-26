from datetime import date as dt_date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.models.moment import Moment
from app.models.user import User
from app.schemas.moment import (
    MomentCreate,
    MomentDetailResponse,
    MomentListItemResponse,
    MomentUpdate,
)
from app.utils.geocoder import GeoCoder
from app.utils.common import to_client_image_url
from app.utils.error_handler import AppException, ErrorCode
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/moments", tags=["moments"])


def _get_owned_moment_or_404(db: Session, moment_id: int, user_id: int) -> Moment:
    item = (
        db.query(Moment)
        .filter(Moment.id == moment_id, Moment.user_id == user_id)
        .first()
    )
    if not item:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Moment not found", 404)
    return item


def _serialize_moment_detail(item: Moment) -> MomentDetailResponse:
    return MomentDetailResponse(
        id=item.id,
        user_id=item.user_id,
        title=item.title,
        content=item.content,
        entry_date=item.entry_date,
        image_path=to_client_image_url(item.image_path),
        adress=item.adress,
        longitude=item.longitude,
        latitude=item.latitude,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=List[MomentListItemResponse])
def list_moments(
    query: str | None = Query(default=None),
    date_from: dt_date | None = Query(default=None),
    date_to: dt_date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    stmt = db.query(Moment).filter(Moment.user_id == current_user.id)

    if query:
        keyword = f"%{query.strip()}%"
        stmt = stmt.filter(or_(Moment.title.ilike(keyword), Moment.content.ilike(keyword)))
    if date_from:
        stmt = stmt.filter(Moment.entry_date >= date_from)
    if date_to:
        stmt = stmt.filter(Moment.entry_date <= date_to)

    rows = stmt.order_by(Moment.entry_date.desc(), Moment.id.desc()).all()

    return [
        MomentListItemResponse(
            id=item.id,
            title=item.title,
            content=item.content,
            entry_date=item.entry_date,
            image_path=to_client_image_url(item.image_path),
            adress=item.adress,
            longitude=item.longitude,
            latitude=item.latitude,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in rows
    ]


@router.post("", response_model=MomentDetailResponse)
def create_moment(
    payload: MomentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = Moment(
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
        entry_date=payload.entry_date,
        image_path=payload.image_path,
        adress=payload.adress,
        longitude=payload.longitude,
        latitude=payload.latitude,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_moment_detail(item)


@router.get("/place-search")
async def search_places(
    query: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    del current_user, db
    results = await GeoCoder.get_instance().search_places(query.strip())
    serialized = []
    for result in results:
        address = result.get("road_address") or result.get("jibun_address") or query.strip()
        if result.get("lat") is None or result.get("lon") is None:
            continue
        serialized.append(
            {
                "name": result.get("name") or query.strip(),
                "adress": address,
                "latitude": result.get("lat"),
                "longitude": result.get("lon"),
            }
        )
    return serialized


@router.get("/reverse-geocode")
async def reverse_geocode_place(
    latitude: float = Query(),
    longitude: float = Query(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    del current_user, db
    result = await GeoCoder.get_instance().reverse_geocoder(latitude, longitude)
    if not result:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Address not found", 404)

    address = result.get("road_address") or result.get("jibun_address")
    if not address:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Address not found", 404)

    return {
        "adress": address,
        "latitude": latitude,
        "longitude": longitude,
    }


@router.get("/{moment_id}", response_model=MomentDetailResponse)
def get_moment(
    moment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = _get_owned_moment_or_404(db, moment_id, current_user.id)
    return _serialize_moment_detail(item)


@router.patch("/{moment_id}", response_model=MomentDetailResponse)
def update_moment(
    moment_id: int,
    payload: MomentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = _get_owned_moment_or_404(db, moment_id, current_user.id)
    update_data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)

    for field in ("title", "content", "entry_date", "image_path", "adress", "longitude", "latitude"):
        if field in update_data:
            setattr(item, field, update_data[field])

    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_moment_detail(item)


@router.delete("/{moment_id}")
def delete_moment(
    moment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = _get_owned_moment_or_404(db, moment_id, current_user.id)
    db.delete(item)
    db.commit()
    return {"ok": True}
