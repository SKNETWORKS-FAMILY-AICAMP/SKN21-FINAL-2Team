from __future__ import annotations

import time
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
    timeout: float = 15.0,
    retries: int = 5,
    backoff_sec: float = 1.5,
) -> Dict[str, Any]:
    """
    TourAPI GET with simple retry/backoff.
    429/5xx에 대해 재시도.
    """
    url = f"{base_url.rstrip('/')}/{endpoint}"

    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            status = resp.status_code

            if status == 200:
                data = resp.json()
                # API 자체 오류 메시지 검사
                code = _safe_get(data, ["response", "header", "resultCode"], "")
                if str(code) not in ("0000", ""):
                    msg = _safe_get(data, ["response", "header", "resultMsg"], "Unknown API error")
                    raise TourAPIError(f"[{endpoint}] API error resultCode={code}, resultMsg={msg}")
                return data

            # 재시도 가능한 상태코드
            if status in (429, 500, 502, 503, 504):
                raise TourAPIError(f"[{endpoint}] HTTP {status}")

            # 그 외는 즉시 실패
            raise TourAPIError(f"[{endpoint}] HTTP {status}: {resp.text[:300]}")

        except Exception as e:
            last_err = e
            if attempt < retries:
                sleep_s = backoff_sec * attempt
                time.sleep(sleep_s)
                continue
            break

    raise TourAPIError(f"[{endpoint}] request failed after retries: {last_err}")


def extract_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    response.body.items.item 파싱
    item이 dict면 [dict], list면 그대로 반환.
    """
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
