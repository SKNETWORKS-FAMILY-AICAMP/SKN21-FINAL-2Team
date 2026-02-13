from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests


class TourAPIError(Exception):
    pass


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def tourapi_get(
    base_url: str,
    endpoint: str,
    params: Dict[str, Any],
    timeout: float = 20.0,
    retries: int = 3,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{endpoint}"
    last_err: Optional[Exception] = None

    for _ in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                code = str(_safe_get(data, ["response", "header", "resultCode"], "")).strip()
                msg = str(_safe_get(data, ["response", "header", "resultMsg"], "")).strip()

                if code in ("0000", ""):
                    return data

                # 토큰/할당량 관련 메시지는 즉시 상위로 전달(중간저장 후 종료시키기 위함)
                token_like = ["SERVICE_KEY", "LIMITED_NUMBER", "ACCESS DENIED", "인증", "할당", "초과"]
                if any(k.lower() in msg.lower() for k in token_like):
                    raise TourAPIError(f"[{endpoint}] TOKEN_OR_QUOTA code={code}, msg={msg}")

                raise TourAPIError(f"[{endpoint}] API code={code}, msg={msg}")

            if r.status_code in (429, 500, 502, 503, 504):
                last_err = TourAPIError(f"[{endpoint}] HTTP {r.status_code}")
                continue

            raise TourAPIError(f"[{endpoint}] HTTP {r.status_code}: {r.text[:300]}")
        except Exception as e:
            last_err = e
            continue

    raise TourAPIError(f"[{endpoint}] request failed: {last_err}")


def extract_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = _safe_get(data, ["response", "body", "items", "item"], [])
    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def extract_total_count(data: Dict[str, Any]) -> int:
    v = _safe_get(data, ["response", "body", "totalCount"], 0)
    try:
        return int(v)
    except Exception:
        return 0
