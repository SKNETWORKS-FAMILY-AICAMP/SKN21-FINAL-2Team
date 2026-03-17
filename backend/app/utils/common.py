import os
import re
import urllib.parse
from typing import Any, Optional

from app.utils.config import DEBUG_MODE


def dprint(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)


def normalize_text(value: str) -> str:
    """비교용 문자열 정규화."""
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def getattr_safe(obj: Any, key: str, default: Any = None) -> Any:
    """
    객체에서 키에 해당하는 값을 가져온다.
    
    Args:
        obj (Any): 객체
        key (str): 키
        default (Any): 기본값

    Returns:
        Any: 키에 해당하는 값
    """

    if obj is None:
        return default

    if hasattr(obj, key):
        return getattr(obj, key)
    elif isinstance(obj, dict):
        return obj.get(key, default)
    else:
        return default


def is_remote_image_url(value: Optional[str]) -> bool:
    text = (value or "").strip().lower()
    return text.startswith("http://") or text.startswith("https://") or text.startswith("data:image")


def _get_upload_root() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
    )


def _get_s3_public_base() -> str:
    return os.environ.get("S3_PUBLIC_BASE_URL", "").rstrip("/")


def to_client_image_url(value: Optional[str]) -> str:
    """저장된 path를 프론트엔드 표시용 URL로 변환.

    - 이미 절대 URL(http/https/data:image) → 그대로 반환
    - /api/static/ 레거시 path → 그대로 반환
    - 상대 path (folder/filename) → S3 base URL 또는 /api/static/ 접두어
    """
    text = (value or "").strip()
    if not text:
        return ""
    if is_remote_image_url(text) or text.startswith("/api/static/"):
        return text
    s3_base = _get_s3_public_base()
    if s3_base:
        return f"{s3_base}/{text.lstrip('/')}"
    return f"/api/static/{text.lstrip('/')}"


def to_vision_image_input(value: Optional[str]) -> str:
    """저장된 path를 비전 모델 입력에 적합한 형태로 변환 (절대 URL 또는 절대 로컬 파일 path)."""
    text = (value or "").strip()
    if not text:
        return ""
    if is_remote_image_url(text):
        return text
    if text.startswith("/api/static/"):
        # 레거시: 로컬 절대 path로 변환
        return os.path.join(_get_upload_root(), text[len("/api/static/"):])
    s3_base = _get_s3_public_base()
    if s3_base:
        return f"{s3_base}/{text.lstrip('/')}"
    return os.path.join(_get_upload_root(), text.lstrip("/"))


def in_seoul_bbox(lat, lng) -> bool:
    return (37.413 <= lat <= 37.701) and (126.734 <= lng <= 127.269)


def build_naver_map_url(query: str, center_lat: float, center_lng: float) -> str:
    """네이버 지도 검색 URL 생성."""
    encoded_query = urllib.parse.quote(query)
    return f"https://map.naver.com/v5/search/{encoded_query}?c=15.00,{center_lng},{center_lat},0,dh"

