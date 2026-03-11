from datetime import date as dt_date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database.connection import db_manager
from app.models.diary import DiaryEntry, DiaryEntryPlace
from app.models.user import User
from app.schemas.diary import (
    DiaryCreate,
    DiaryDetailResponse,
    DiaryLinkedPlaceInput,
    DiaryListItemResponse,
    DiaryUpdate,
)
from app.utils.geocoder import GeoCoder
from app.utils.common import to_client_image_url
from app.utils.error_handler import AppException, ErrorCode
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/diaries", tags=["diaries"])


def _get_owned_diary_or_404(db: Session, diary_id: int, user_id: int) -> DiaryEntry:
    item = (
        db.query(DiaryEntry)
        .options(joinedload(DiaryEntry.linked_chat_room), joinedload(DiaryEntry.linked_places))
        .filter(DiaryEntry.id == diary_id, DiaryEntry.user_id == user_id)
        .first()
    )
    if not item:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Diary not found", 404)
    return item

def _apply_manual_place_snapshots(entry: DiaryEntry, places: List[DiaryLinkedPlaceInput]) -> None:
    entry.linked_places.clear()
    for place in places:
        entry.linked_places.append(
            DiaryEntryPlace(
                chat_place_id=place.chat_place_id,
                place_id=place.place_id,
                name=place.name,
                adress=place.adress,
                image_path=place.image_path,
                longitude=place.longitude,
                latitude=place.latitude,
            )
        )


def _serialize_diary_detail(item: DiaryEntry) -> DiaryDetailResponse:
    linked_room = None
    if item.linked_chat_room:
        linked_room = {
            "id": item.linked_chat_room.id,
            "title": item.linked_chat_room.title,
            "created_at": item.linked_chat_room.created_at,
        }

    linked_places = [
        {
            "id": place.id,
            "chat_place_id": place.chat_place_id,
            "place_id": place.place_id,
            "name": place.name,
            "adress": place.adress,
            "image_path": to_client_image_url(place.image_path),
            "longitude": place.longitude,
            "latitude": place.latitude,
            "created_at": place.created_at,
        }
        for place in item.linked_places
    ]

    return DiaryDetailResponse(
        id=item.id,
        user_id=item.user_id,
        title=item.title,
        content=item.content,
        entry_date=item.entry_date,
        cover_image_path=to_client_image_url(item.cover_image_path),
        linked_places_count=len(linked_places),
        linked_chat_room=linked_room,
        linked_places=linked_places,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=List[DiaryListItemResponse])
def list_diaries(
    query: str | None = Query(default=None),
    date_from: dt_date | None = Query(default=None),
    date_to: dt_date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    linked_count = func.count(DiaryEntryPlace.id).label("linked_places_count")
    stmt = (
        db.query(DiaryEntry, linked_count)
        .outerjoin(DiaryEntryPlace, DiaryEntryPlace.entry_id == DiaryEntry.id)
        .filter(DiaryEntry.user_id == current_user.id)
        .group_by(DiaryEntry.id)
    )

    if query:
        keyword = f"%{query.strip()}%"
        stmt = stmt.filter(or_(DiaryEntry.title.ilike(keyword), DiaryEntry.content.ilike(keyword)))
    if date_from:
        stmt = stmt.filter(DiaryEntry.entry_date >= date_from)
    if date_to:
        stmt = stmt.filter(DiaryEntry.entry_date <= date_to)

    rows = stmt.order_by(DiaryEntry.entry_date.desc(), DiaryEntry.id.desc()).all()

    result: List[DiaryListItemResponse] = []
    for item, linked_places_count in rows:
        cover_image_path = to_client_image_url(item.cover_image_path)
        result.append(
            DiaryListItemResponse(
                id=item.id,
                title=item.title,
                content=item.content,
                entry_date=item.entry_date,
                cover_image_path=cover_image_path,
                linked_places_count=int(linked_places_count or 0),
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return result


@router.post("", response_model=DiaryDetailResponse)
def create_diary(
    payload: DiaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    entry = DiaryEntry(
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
        entry_date=payload.entry_date,
        cover_image_path=payload.cover_image_path,
        linked_chat_room_id=None,
    )
    _apply_manual_place_snapshots(entry, payload.linked_places)
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return _serialize_diary_detail(_get_owned_diary_or_404(db, entry.id, current_user.id))


@router.get("/place-search")
def search_places(
    query: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    del current_user, db
    results = GeoCoder().search_places(query.strip())
    serialized = []
    for result in results:
        address = result.get("road_address") or result.get("jibun_address") or query.strip()
        if result.get("lat") is None or result.get("lng") is None:
            continue
        serialized.append(
            {
                "name": result.get("name") or query.strip(),
                "adress": address,
                "latitude": result.get("lat"),
                "longitude": result.get("lng"),
            }
        )
    return serialized


@router.get("/reverse-geocode")
def reverse_geocode_place(
    latitude: float = Query(),
    longitude: float = Query(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    del current_user, db
    result = GeoCoder().reverse_geocoder(latitude, longitude)
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


@router.get("/{diary_id}", response_model=DiaryDetailResponse)
def get_diary(
    diary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = _get_owned_diary_or_404(db, diary_id, current_user.id)
    return _serialize_diary_detail(item)


@router.patch("/{diary_id}", response_model=DiaryDetailResponse)
def update_diary(
    diary_id: int,
    payload: DiaryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = _get_owned_diary_or_404(db, diary_id, current_user.id)
    update_data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)

    if "linked_places" in update_data:
        _apply_manual_place_snapshots(item, payload.linked_places or [])

    for field in ("title", "content", "entry_date", "cover_image_path"):
        if field in update_data:
            setattr(item, field, update_data[field])

    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_diary_detail(_get_owned_diary_or_404(db, diary_id, current_user.id))


@router.delete("/{diary_id}")
def delete_diary(
    diary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = _get_owned_diary_or_404(db, diary_id, current_user.id)
    db.delete(item)
    db.commit()
    return {"ok": True}
