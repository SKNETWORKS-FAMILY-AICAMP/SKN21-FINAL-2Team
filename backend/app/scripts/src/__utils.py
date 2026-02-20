import re
from typing import Any, Optional

def _text(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()

def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None

def _valid_xy(x: Optional[float], y: Optional[float]) -> bool:
    if x is None or y is None:
        return False
    return (120.0 <= x <= 132.0) and (33.0 <= y <= 39.5)

def _norm_name(name: str) -> str:
    s = _text(name)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s