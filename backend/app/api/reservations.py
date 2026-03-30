import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationResponse, ReservationUpdate
from app.utils.common import to_client_image_url
from app.utils.error_handler import AppException, ErrorCode
from app.utils.security import get_current_user
from app.utils.db_utils import get_owned_resource_or_404
from app.services.ocr_service import extract_datetime_from_image

# 로컬 업로드 루트 (main.py와 동일한 경로)
_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "..", "data", "uploads"
)

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _to_response(item: Reservation) -> ReservationResponse:
    """DB 모델 → 응답 스키마 변환. image_path를 표시 가능한 URL로 변환."""
    return ReservationResponse(
        id=item.id,
        user_id=item.user_id,
        category=item.category,
        name=item.name,
        date=item.date,
        image_path=to_client_image_url(item.image_path) or None,
        details=item.details,
    )


@router.post("/ocr")
async def ocr_reservation_image(
    file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    이미지에서 예약 날짜·시간을 OCR로 추출합니다.

    두 가지 방식 지원:
    1) file 업로드: 새로 선택한 이미지를 multipart/form-data로 전송
    2) image_path 전달: DB에 저장된 상대 경로(또는 https:// URL)를 문자열로 전송
       → 백엔드가 직접 파일을 읽거나 S3/URL에서 다운로드해 처리
    """
    if file is not None:
        # 방식 1: 직접 업로드된 파일
        # 주의: 이미지 파일인지 간단히 검증
        if not file.content_type or not file.content_type.startswith("image/"):
            raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "이미지 파일만 업로드 가능합니다.", 400)
        image_bytes = await file.read()

    elif image_path:
        # 방식 2: 저장된 이미지 경로 또는 URL → 백엔드가 직접 읽음
        if image_path.startswith("http://") or image_path.startswith("https://"):
            # S3 또는 외부 URL: httpx로 다운로드
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(image_path)
                    resp.raise_for_status()
                    image_bytes = resp.content
            except Exception as e:
                raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, f"이미지 다운로드 실패: {e}", 400)
        else:
            # 로컬 파일: uploads 디렉토리 기준 상대 경로
            local_path = os.path.abspath(
                os.path.join(_UPLOAD_DIR, image_path.lstrip("/"))
            )
            # 주의: 경로 탈출 공격 방지 — uploads 디렉토리 외부 접근 차단
            if not local_path.startswith(os.path.abspath(_UPLOAD_DIR)):
                raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "유효하지 않은 이미지 경로입니다.", 400)
            if not os.path.isfile(local_path):
                raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "이미지 파일을 찾을 수 없습니다.", 404)
            with open(local_path, "rb") as f:
                image_bytes = f.read()
    else:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "file 또는 image_path 중 하나를 제공해야 합니다.", 400)

    result = await extract_datetime_from_image(image_bytes, category)
    return result



@router.get("", response_model=List[ReservationResponse])
def list_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    items = (
        db.query(Reservation)
        .filter(Reservation.user_id == current_user.id)
        .order_by(Reservation.id.desc())
        .all()
    )
    return [_to_response(r) for r in items]


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
        details=payload.details,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_response(item)


@router.patch("/{reservation_id}", response_model=ReservationResponse)
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = get_owned_resource_or_404(
        db, Reservation, reservation_id, current_user.id,
        ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Reservation not found"
    )

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_response(item)


@router.delete("/{reservation_id}")
def delete_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    item = get_owned_resource_or_404(
        db, Reservation, reservation_id, current_user.id,
        ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Reservation not found"
    )

    db.delete(item)
    db.commit()
    return {"ok": True}
