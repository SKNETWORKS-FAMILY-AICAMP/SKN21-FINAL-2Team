import json as _json

def parse_payload(payload: dict) -> str:
    """
    payload에서 LLM이 사용하지 않는 불필요한 키를 제거하고 JSON 문자열로 반환한다.
    
    Args:
        payload (dict): payload

    Returns:
        str: JSON 문자열
    """
    filtered = {}
    for k, v in payload.items():
        if k in {"image", "image_urls", "mapx", "mapy", "map_url", "contentid", "id"}:
            continue
        if v is None or v == "" or v == [] or v == {}:
            continue
        filtered[k] = v

    payload_str = _json.dumps(filtered, ensure_ascii=False)

    return payload_str

