from typing import Any, Dict, List, Optional, Tuple
from .__config import Settings, places_jsonl_path
from .__storage import read_jsonl
from .__utils import _text, _to_float, _valid_xy, _norm_name
from .__geocoder import _geocode_with_cache

FEE_KEYS = {"입장료", "이용요금", "이용요금(입장료)"}

def _extract_fees_from_detail_info(rows):
    if not rows: return []
    fees = []
    for r in rows:
        k, v = (r.get("infoname") or "").strip(), (r.get("infotext") or "").strip()
        if k in FEE_KEYS and v: fees.append({"name": k, "text": v})
    return fees

def _pet_first_and_drop_id(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows: return None
    d = dict(rows[0]) if isinstance(rows[0], dict) else None
    if not d: return None
    d.pop("contentid", None); d.pop("contentId", None)
    return d

def _build_place_index(settings: Settings) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for ct in [12, 14, 15, 28, 32, 39]:
        for row in read_jsonl(places_jsonl_path(settings, ct)):
            cid = _text(row.get("contentid"))
            if not cid: continue
            x, y = _to_float(row.get("mapx")), _to_float(row.get("mapy"))
            if _valid_xy(x, y): out[cid] = (x, y)
    return out

def _shape_common(ct: int, base: Dict[str, Any], intro: Dict[str, Any], pet_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    labels = {12: "관광지", 14: "문화시설", 15: "축제공연행사", 28: "레포츠", 32: "숙박", 39: "음식점"}
    return {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": labels.get(ct, str(ct)),
        "image": _text(base.get("firstimage")),
        "usetime": _text(intro.get("usetime") or intro.get("usetimeTourinfo") or base.get("usetime")),
        "restdate": _text(intro.get("restdate") or base.get("restdate")),
        "parking": _text(intro.get("parking") or base.get("parking")),
        "addr": _text(base.get("addr1")),
        "mapy": _text(base.get("mapy")),
        "mapx": _text(base.get("mapx")),
        "tel": _text(base.get("tel")),
        "contenttypeid_code": str(ct),
        **({"pet_raw": pet_raw} if pet_raw is not None else {}),
    }

def _shape_trip25(settings: Settings, base: Dict, intro: Dict, info_rows: List[Dict], place_index: Dict, cache: Dict, geocode_calls: List[int], geocode_limit: int, area_code: int) -> Dict:
    cid = _text(base.get("contentid") or base.get("contentId"))
    out = {"contentid": cid, "course_contentid": cid, "course_title": _text(base.get("title")), "overview": intro.get("overview") if intro else None, "rand_mapy": None, "rand_mapx": None, "members": []}
    members = []
    for m in (info_rows or []):
        subname, subcontentid, suboverview = _text(m.get("subname")), _text(m.get("subcontentid")), _text(m.get("suboverview"))
        if not suboverview:
            for kk, vv in m.items():
                if "overview" in str(kk).lower() and _text(vv): suboverview = _text(vv); break
        mx, my = _to_float(m.get("mapx")), _to_float(m.get("mapy"))
        if not _valid_xy(mx, my):
            if subcontentid and subcontentid in place_index: mx, my = place_index[subcontentid]
            else:
                q1 = _norm_name(subname); q2 = f"{q1} 서울" if area_code == 1 else q1
                res = _geocode_with_cache(settings, q2, cache, geocode_calls, geocode_limit) or _geocode_with_cache(settings, q1, cache, geocode_calls, geocode_limit)
                if res: mx, my = res
        members.append({"subname": subname, "subcontentid": subcontentid, "suboverview": suboverview, "mapx": str(mx) if mx else None, "mapy": str(my) if my else None})
    out["members"] = members
    xs, ys = [float(mm["mapx"]) for mm in members if mm["mapx"]], [float(mm["mapy"]) for mm in members if mm["mapy"]]
    if xs and ys: out["rand_mapx"], out["rand_mapy"] = str(sum(xs) / len(xs)), str(sum(ys) / len(ys))
    return out