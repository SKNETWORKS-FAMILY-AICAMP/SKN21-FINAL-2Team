import base64
import os
import re
import time
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.connection import db_manager
from app.models.country import Country
from app.models.user import User
from app.utils.error_handler import AppException, ErrorCode
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/common", tags=["common"])

class CountryResponse(BaseModel):
    code: str
    name: str

    class Config:
        from_attributes = True


class ImageUploadRequest(BaseModel):
    data_url: str
    folder: str = "misc"


class ImageUploadResponse(BaseModel):
    image_path: str

@router.get("/countries", response_model=List[CountryResponse])
def read_countries(db: Session = Depends(db_manager.get_db)):
    return db.query(Country).all()


@router.post("/upload-image", response_model=ImageUploadResponse)
def upload_image(
    payload: ImageUploadRequest,
    current_user: User = Depends(get_current_user),
):
    data_url = payload.data_url or ""
    m = re.match(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", data_url)
    if not m:
        raise AppException(ErrorCode.VALIDATION_ERROR, "Invalid image data URL", 400)

    mime_type, b64_data = m.group(1), m.group(2)
    ext = mime_type.split("/")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"
    if ext not in {"jpg", "png", "webp", "gif"}:
        raise AppException(ErrorCode.VALIDATION_ERROR, "Unsupported image format", 400)

    try:
        raw = base64.b64decode(b64_data, validate=True)
    except Exception as e:
        raise AppException(ErrorCode.VALIDATION_ERROR, f"Invalid base64 image data: {e}", 400)

    folder = re.sub(r"[^a-zA-Z0-9_-]", "", payload.folder or "misc") or "misc"
    upload_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "uploads")
    upload_root = os.path.abspath(upload_root)
    target_dir = os.path.join(upload_root, folder)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{current_user.id}_{int(time.time() * 1000)}.{ext}"
    target_path = os.path.join(target_dir, filename)
    with open(target_path, "wb") as f:
        f.write(raw)

    return ImageUploadResponse(image_path=f"/api/static/{folder}/{filename}")
