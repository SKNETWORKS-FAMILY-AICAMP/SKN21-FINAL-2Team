import base64
import os
import re
import time
import urllib.parse
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.user import User
from app.utils.error_handler import AppException, ErrorCode
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/common", tags=["common"])

class ImageUploadRequest(BaseModel):
    data_url: str
    folder: str = "misc"


class ImageUploadResponse(BaseModel):
    image_path: str  # relative path: folder/filename (e.g. "chat/123_timestamp.jpg")


def _parse_s3_uri(uri: str):
    """Parse s3://bucket/prefix/ → (bucket, prefix)"""
    parsed = urllib.parse.urlparse(uri)
    bucket = parsed.netloc
    prefix = parsed.path.strip("/")
    return bucket, prefix


def _upload_to_s3(raw: bytes, s3_key: str, content_type: str) -> None:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    file_server_url = os.environ.get("FILE_SERVER_URL", "")
    bucket, _ = _parse_s3_uri(file_server_url)

    region = os.environ.get("AWS_REGION", "ap-northeast-2")
    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    try:
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=raw,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as e:
        raise AppException(ErrorCode.INTERNAL_SERVER_ERROR, f"S3 upload failed: {e}", 500)


def _upload_local(raw: bytes, folder: str, filename: str) -> None:
    upload_root = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "uploads")
    )
    target_dir = os.path.join(upload_root, folder)
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, filename), "wb") as f:
        f.write(raw)


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
    filename = f"{current_user.id}_{int(time.time() * 1000)}.{ext}"

    file_server_url = os.environ.get("FILE_SERVER_URL", "")
    if file_server_url.startswith("s3://"):
        _, s3_prefix = _parse_s3_uri(file_server_url)
        s3_key = f"{s3_prefix}/{folder}/{filename}" if s3_prefix else f"{folder}/{filename}"
        _upload_to_s3(raw, s3_key, mime_type)
    else:
        _upload_local(raw, folder, filename)

    # DB에는 상대 path만 저장 (folder/filename)
    return ImageUploadResponse(image_path=f"{folder}/{filename}")
