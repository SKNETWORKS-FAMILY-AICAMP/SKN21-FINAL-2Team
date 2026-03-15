import re
import urllib.parse
from typing import Any, Optional


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


def to_client_image_url(value: Optional[str]) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if text.startswith("/api/static/") or is_remote_image_url(text):
        return text
    return f"/api/static/{text.lstrip('/')}"


def in_seoul_bbox(lat, lng) -> bool:
    return (37.413 <= lat <= 37.701) and (126.734 <= lng <= 127.269)


def build_naver_map_url(query: str, center_lat: float, center_lng: float) -> str:
    """네이버 지도 검색 URL 생성."""
    encoded_query = urllib.parse.quote(query)
    return f"https://map.naver.com/v5/search/{encoded_query}?c=15.00,{center_lng},{center_lat},0,dh"

