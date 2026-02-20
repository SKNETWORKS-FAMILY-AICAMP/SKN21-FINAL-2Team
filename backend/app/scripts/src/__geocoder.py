from typing import Any, Dict, List, Optional, Tuple
import requests
from .__config import Settings, geocode_cache_path
from .__storage import read_json, write_json
from .__utils import _text, _to_float, _valid_xy

def _load_geocode_cache(settings: Settings) -> Dict[str, Any]:
    return read_json(geocode_cache_path(settings), default={}) or {}

def _save_geocode_cache(settings: Settings, cache: Dict[str, Any]) -> None:
    write_json(geocode_cache_path(settings), cache)

def _kakao_geocode(settings: Settings, query: str) -> Optional[Tuple[float, float]]:
    if not getattr(settings, "kakao_rest_api_key", ""): return None
    q = _text(query)
    if not q: return None
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"}
    try:
        r = requests.get(url, params={"query": q, "size": 1}, headers=headers, timeout=20)
        if r.status_code != 200: return None
        docs = r.json().get("documents") or []
        if not docs: return None
        x, y = _to_float(docs[0].get("x")), _to_float(docs[0].get("y"))
        if _valid_xy(x, y): return (x, y)
        return None
    except Exception: return None

def _naver_geocode(settings: Settings, query: str) -> Optional[Tuple[float, float]]:
    if not (settings.naver_client_id and settings.naver_client_secret): return None
    q = _text(query)
    if not q: return None
    url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {"X-NCP-APIGW-API-KEY-ID": settings.naver_client_id, "X-NCP-APIGW-API-KEY": settings.naver_client_secret}
    try:
        r = requests.get(url, params={"query": q}, headers=headers, timeout=20)
        if r.status_code != 200: return None
        addrs = r.json().get("addresses") or []
        if not addrs: return None
        x, y = float(addrs[0].get("x")), float(addrs[0].get("y"))
        if _valid_xy(x, y): return (x, y)
        return None
    except Exception: return None

def _geocode_with_cache(settings: Settings, query: str, cache: Dict[str, Any], geocode_calls: List[int], geocode_limit: int) -> Optional[Tuple[float, float]]:
    key = _text(query)
    if not key: return None
    if key in cache:
        v = cache.get(key)
        if isinstance(v, dict):
            x, y = _to_float(v.get("x")), _to_float(v.get("y"))
            if _valid_xy(x, y): return (x, y)
        return None
    if geocode_calls[0] >= geocode_limit: return None
    
    res = _kakao_geocode(settings, key) or _naver_geocode(settings, key)
    geocode_calls[0] += 1
    cache[key] = {"x": res[0], "y": res[1]} if res else {"x": None, "y": None}
    return res