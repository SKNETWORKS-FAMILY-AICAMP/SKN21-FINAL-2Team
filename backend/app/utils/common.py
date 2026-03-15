import json as _json
from typing import Any, Optional


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", (value or "")).lower()


def parse_payload(payload: dict, exclude_keys: list = ["image", "image_urls", "mapx", "mapy", "map_url", "contentid", "id"]) -> str:
    """
    payload에서 LLM이 사용하지 않는 불필요한 키를 제거하고 JSON 문자열로 반환한다.
    
    Args:
        payload (dict): payload

    Returns:
        str: JSON 문자열
    """
    filtered = {}
    for k, v in payload.items():
        if k in exclude_keys:
            continue
        if v is None or v == "" or v == [] or v == {}:
            continue
        filtered[k] = v

    payload_str = _json.dumps(filtered, ensure_ascii=False)

    return payload_str


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
