from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationResponse, ReservationUpdate
from app.utils.error_handler import AppException, ErrorCode
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


@router.get("", response_model=List[ReservationResponse])
def list_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    return (
        db.query(Reservation)
        .filter(Reservation.user_id == current_user.id)
        .order_by(Reservation.id.desc())
        .all()
    )


@router.post("", response_model=ReservationResponse)
def create_reservation(
    payload: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = Reservation(
        user_id=current_user.id,
        category=payload.category,
        name=payload.name,
        date=payload.date,
        image_path=payload.image_path,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{reservation_id}", response_model=ReservationResponse)
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id, Reservation.user_id == current_user.id)
        .first()
    )
    if not item:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Reservation not found", 404)

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{reservation_id}")
def delete_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id, Reservation.user_id == current_user.id)
        .first()
    )
    if not item:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Reservation not found", 404)

    db.delete(item)
    db.commit()
    return {"ok": True}
