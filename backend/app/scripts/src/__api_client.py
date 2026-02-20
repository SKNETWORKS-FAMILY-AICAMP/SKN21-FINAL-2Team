from typing import Any, Dict, List
import requests
from .__config import Settings

def _base_params(settings: Settings) -> Dict[str, Any]:
    return {
        "serviceKey": settings.tour_api_key,
        "MobileOS": settings.tour_mobile_os,
        "MobileApp": settings.tour_mobile_app,
        "_type": settings.tour_api_type,
    }

def _api_get(url: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _items(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = (resp.get("response") or {}).get("body") or {}
    items = (body.get("items") or {}).get("item")
    if items is None: return []
    if isinstance(items, list): return items
    return [items]

def _detail_intro(settings: Settings, content_id: str, ct: int) -> Dict[str, Any]:
    params = _base_params(settings)
    params.update({"contentId": content_id, "contentTypeId": ct})
    try:
        resp = _api_get(settings.tour_api_detail_intro_url, params)
        rows = _items(resp)
        return rows[0] if rows else {}
    except Exception: return {}

def _detail_info_rows(settings: Settings, content_id: str, ct: int, *, verbose: bool = False) -> List[Dict[str, Any]]:
    params = _base_params(settings)
    params.update({"contentId": str(content_id), "contentTypeId": str(ct), "pageNo": 1, "numOfRows": 100})
    try:
        resp = _api_get(settings.tour_api_detail_info_url, params)
        return _items(resp)
    except Exception as e:
        if verbose: print(f"[detailInfo2 EXCEPTION] ct={ct} {e}")
        return []

def _detail_pet_tour_rows(settings: Settings, content_id: str, ct: int, *, verbose: bool = False) -> List[Dict[str, Any]]:
    params = _base_params(settings)
    params.update({"contentId": str(content_id), "pageNo": 1, "numOfRows": 100})
    try:
        resp = _api_get(settings.tour_api_detail_pet_tour_url, params)
        r = resp.get("response") if isinstance(resp, dict) else None
        body = r.get("body") if isinstance(r, dict) else None
        items = body.get("items") if isinstance(body, dict) else None
        items = items.get("item") if isinstance(items, dict) else items
        
        if items is None: return []
        if isinstance(items, list): return items
        if isinstance(items, dict): return [items]
        return []
    except Exception as e:
        if verbose: print(f"[detailPetTour2 EXCEPTION] ct={ct} {e}")
        return []