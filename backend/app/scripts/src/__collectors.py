from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from .__config import Settings, places_jsonl_path, geocode_cache_path
from .__storage import read_json, write_json, read_jsonl


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
    if items is None:
        return []
    if isinstance(items, list):
        return items
    return [items]


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


def _load_geocode_cache(settings: Settings) -> Dict[str, Any]:
    return read_json(geocode_cache_path(settings), default={}) or {}


def _save_geocode_cache(settings: Settings, cache: Dict[str, Any]) -> None:
    write_json(geocode_cache_path(settings), cache)

def _kakao_geocode(settings: Settings, query: str) -> Optional[Tuple[float, float]]:
    # Kakao REST 키가 없으면 사용 안 함
    if not getattr(settings, "kakao_rest_api_key", ""):
        return None

    q = _text(query)
    if not q:
        return None

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"}

    try:
        r = requests.get(url, params={"query": q, "size": 1}, headers=headers, timeout=20)
        if r.status_code != 200:
            return None
        js = r.json()
        docs = js.get("documents") or []
        if not docs:
            return None

        x = _to_float(docs[0].get("x"))
        y = _to_float(docs[0].get("y"))
        if _valid_xy(x, y):
            return (x, y)
        return None
    except Exception:
        return None


def _naver_geocode(settings: Settings, query: str) -> Optional[Tuple[float, float]]:
    if not (settings.naver_client_id and settings.naver_client_secret):
        return None
    q = _text(query)
    if not q:
        return None
    url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": settings.naver_client_id,
        "X-NCP-APIGW-API-KEY": settings.naver_client_secret,
    }
    r = requests.get(url, params={"query": q}, headers=headers, timeout=20)
    if r.status_code != 200:
        return None
    js = r.json()
    addrs = js.get("addresses") or []
    if not addrs:
        return None
    try:
        x = float(addrs[0].get("x"))
        y = float(addrs[0].get("y"))
        if _valid_xy(x, y):
            return (x, y)
        return None
    except Exception:
        return None


def _geocode_with_cache(
    settings: Settings,
    query: str,
    cache: Dict[str, Any],
    geocode_calls: List[int],
    geocode_limit: int,
) -> Optional[Tuple[float, float]]:
    key = _text(query)
    if not key:
        return None
    if key in cache:
        v = cache.get(key)
        if isinstance(v, dict):
            x = _to_float(v.get("x"))
            y = _to_float(v.get("y"))
            if _valid_xy(x, y):
                return (x, y)
        return None

    if geocode_calls[0] >= geocode_limit:
        return None

    res = _kakao_geocode(settings, key) or _naver_geocode(settings, key)
    geocode_calls[0] += 1

    if res is None:
        cache[key] = {"x": None, "y": None}
        return None

    cache[key] = {"x": res[0], "y": res[1]}
    return res


def _detail_intro(settings: Settings, content_id: str, ct: int) -> Dict[str, Any]:
    params = _base_params(settings)
    params.update({"contentId": content_id, "contentTypeId": ct})
    try:
        resp = _api_get(settings.tour_api_detail_intro_url, params)
        rows = _items(resp)
        return rows[0] if rows else {}
    except Exception:
        return {}


def _detail_info_rows(
    settings: Settings,
    content_id: str,
    ct: int,
    *,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    params = _base_params(settings)

    # ✅ detailInfo2는 페이지 파라미터가 없는 경우 items가 비는 케이스가 많음
    params.update(
        {
            "contentId": str(content_id),
            "contentTypeId": str(ct),
            "pageNo": 1,
            "numOfRows": 100,  # 여행코스 subcourse 수가 많을 수 있으니 넉넉히
        }
    )

    try:
        resp = _api_get(settings.tour_api_detail_info_url, params)
        rows = _items(resp)  # dict/list 모두 처리하는 함수(너 코드에 이미 있음)

        if not rows and verbose:
            header = (resp.get("response") or {}).get("header") or {}
            body = (resp.get("response") or {}).get("body") or {}
            print(
                f"[detailInfo2 EMPTY] ct={ct} contentId={content_id} "
                f"resultCode={header.get('resultCode')} resultMsg={header.get('resultMsg')} "
                f"totalCount={body.get('totalCount')} keys(items)={list((body.get('items') or {}).keys())}"
            )

        return rows

    except Exception as e:
        if verbose:
            print(f"[detailInfo2 EXCEPTION] ct={ct} contentId={content_id} {type(e).__name__}: {e}")
        return []


def _pet_first_and_drop_id(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None
    d = dict(rows[0]) if isinstance(rows[0], dict) else None
    if not d:
        return None
    d.pop("contentid", None)
    d.pop("contentId", None)
    return d


def _build_place_index(settings: Settings) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for ct in [12, 14, 15, 28, 32, 39]:
        p = places_jsonl_path(settings, ct)
        for row in read_jsonl(p):
            cid = _text(row.get("contentid"))
            if not cid:
                continue
            x = _to_float(row.get("mapx"))
            y = _to_float(row.get("mapy"))
            if _valid_xy(x, y):
                out[cid] = (x, y)
    return out


def _shape_ct12(base: Dict[str, Any], intro: Dict[str, Any], pet_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": "관광지",
        "firstimage": _text(base.get("firstimage")),
        "usetime": _text(intro.get("usetime") or intro.get("usetimeTourinfo") or base.get("usetime")),
        "restdate": _text(intro.get("restdate") or base.get("restdate")),
        "parking": _text(intro.get("parking") or base.get("parking")),
        "addr1": _text(base.get("addr1")),
        "addr2": _text(base.get("addr2")),
        "mapx": _text(base.get("mapx")),
        "mapy": _text(base.get("mapy")),
        "areacode": _text(base.get("areacode")),
        "cat1": _text(base.get("cat1")),
        "cat2": _text(base.get("cat2")),
        "cat3": _text(base.get("cat3")),
        "lclsSystm1": _text(base.get("lclsSystm1")),
        "lclsSystm2": _text(base.get("lclsSystm2")),
        "lclsSystm3": _text(base.get("lclsSystm3")),
        "lDongRegnCd": _text(base.get("lDongRegnCd")),
        "lDongSignguCd": _text(base.get("lDongSignguCd")),
        "contenttypeid_code": "12",
        **({"pet_raw": pet_raw} if pet_raw is not None else {}),
    }


def _shape_ct14(base: Dict[str, Any], intro: Dict[str, Any], pet_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": "문화시설",
        "firstimage": _text(base.get("firstimage")),
        "usetime": _text(intro.get("usetime") or base.get("usetime")),
        "addr1": _text(base.get("addr1")),
        "mapx": _text(base.get("mapx")),
        "mapy": _text(base.get("mapy")),
        "areacode": _text(base.get("areacode")),
        "cat1": _text(base.get("cat1")),
        "cat2": _text(base.get("cat2")),
        "cat3": _text(base.get("cat3")),
        "lclsSystm1": _text(base.get("lclsSystm1")),
        "lclsSystm2": _text(base.get("lclsSystm2")),
        "lclsSystm3": _text(base.get("lclsSystm3")),
        "lDongRegnCd": _text(base.get("lDongRegnCd")),
        "lDongSignguCd": _text(base.get("lDongSignguCd")),
        "contenttypeid_code": "14",
        **({"pet_raw": pet_raw} if pet_raw is not None else {}),
    }


def _shape_ct15(base: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": "축제공연행사",
        "firstimage": _text(base.get("firstimage")),
        "addr1": _text(base.get("addr1")),
        "addr2": _text(base.get("addr2")),
        "mapx": _text(base.get("mapx")),
        "mapy": _text(base.get("mapy")),
        "tel": _text(base.get("tel")),
        "areacode": _text(base.get("areacode")),
        "cat1": _text(base.get("cat1")),
        "cat2": _text(base.get("cat2")),
        "cat3": _text(base.get("cat3")),
        "lclsSystm1": _text(base.get("lclsSystm1")),
        "lclsSystm2": _text(base.get("lclsSystm2")),
        "lclsSystm3": _text(base.get("lclsSystm3")),
        "lDongRegnCd": _text(base.get("lDongRegnCd")),
        "lDongSignguCd": _text(base.get("lDongSignguCd")),
        "contenttypeid_code": "15",
    }


def _shape_ct28(base: Dict[str, Any], pet_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": "레포츠",
        "firstimage": _text(base.get("firstimage")),
        "addr1": _text(base.get("addr1")),
        "mapx": _text(base.get("mapx")),
        "mapy": _text(base.get("mapy")),
        "areacode": _text(base.get("areacode")),
        "cat1": _text(base.get("cat1")),
        "cat2": _text(base.get("cat2")),
        "cat3": _text(base.get("cat3")),
        "lclsSystm1": _text(base.get("lclsSystm1")),
        "lclsSystm2": _text(base.get("lclsSystm2")),
        "lclsSystm3": _text(base.get("lclsSystm3")),
        "lDongRegnCd": _text(base.get("lDongRegnCd")),
        "lDongSignguCd": _text(base.get("lDongSignguCd")),
        "contenttypeid_code": "28",
        **({"pet_raw": pet_raw} if pet_raw is not None else {}),
    }


def _shape_ct32(base: Dict[str, Any], pet_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": "숙박",
        "firstimage": _text(base.get("firstimage")),
        "addr1": _text(base.get("addr1")),
        "mapx": _text(base.get("mapx")),
        "mapy": _text(base.get("mapy")),
        "tel": _text(base.get("tel")),
        "areacode": _text(base.get("areacode")),
        "cat1": _text(base.get("cat1")),
        "cat2": _text(base.get("cat2")),
        "cat3": _text(base.get("cat3")),
        "lclsSystm1": _text(base.get("lclsSystm1")),
        "lclsSystm2": _text(base.get("lclsSystm2")),
        "lclsSystm3": _text(base.get("lclsSystm3")),
        "lDongRegnCd": _text(base.get("lDongRegnCd")),
        "lDongSignguCd": _text(base.get("lDongSignguCd")),
        "contenttypeid_code": "32",
        **({"pet_raw": pet_raw} if pet_raw is not None else {}),
    }


def _shape_ct39(base: Dict[str, Any], pet_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": "음식점",
        "addr1": _text(base.get("addr1")),
        "mapx": _text(base.get("mapx")),
        "mapy": _text(base.get("mapy")),
        "areacode": _text(base.get("areacode")),
        "cat1": _text(base.get("cat1")),
        "cat2": _text(base.get("cat2")),
        "cat3": _text(base.get("cat3")),
        "lclsSystm1": _text(base.get("lclsSystm1")),
        "lclsSystm2": _text(base.get("lclsSystm2")),
        "lclsSystm3": _text(base.get("lclsSystm3")),
        "lDongRegnCd": _text(base.get("lDongRegnCd")),
        "lDongSignguCd": _text(base.get("lDongSignguCd")),
        "contenttypeid_code": "39",
        **({"pet_raw": pet_raw} if pet_raw is not None else {}),
    }


def _shape_trip25(
    settings: Settings,
    base: Dict[str, Any],
    intro: Dict[str, Any],
    info_rows: List[Dict[str, Any]],
    place_index: Dict[str, Tuple[float, float]],
    cache: Dict[str, Any],
    geocode_calls: List[int],
    geocode_limit: int,
    area_code: int,
) -> Dict[str, Any]:
    cid = _text(base.get("contentid") or base.get("contentId"))
    title = _text(base.get("title"))
    out: Dict[str, Any] = {
        "contentid": cid,
        "course_contentid": cid,
        "course_title": title,
        "overview": intro.get("overview") if intro else None,
        "rand_mapx": None,
        "rand_mapy": None,
        "members": [],
    }

    members: List[Dict[str, Any]] = []

    for m in (info_rows or []):
        subname = _text(m.get("subname"))
        subcontentid = _text(m.get("subcontentid"))
        suboverview = _text(m.get("suboverview"))
        
        if not suboverview:
            for kk, vv in m.items():
                if "overview" in str(kk).lower() and _text(vv):
                    suboverview = _text(vv)
                    break

    
        mx = _to_float(m.get("mapx"))
        my = _to_float(m.get("mapy"))

        if not _valid_xy(mx, my):
            if subcontentid and subcontentid in place_index:
                mx, my = place_index[subcontentid]
            else:
                q1 = _norm_name(subname)
                q2 = f"{q1} 서울" if area_code == 1 else q1
                res = (
                    _geocode_with_cache(settings, q2, cache, geocode_calls, geocode_limit)
                    or _geocode_with_cache(settings, q1, cache, geocode_calls, geocode_limit)
                )
                if res is not None:
                    mx, my = res

        members.append(
            {
                "subname": subname,
                "subcontentid": subcontentid,
                "suboverview": suboverview,
                "mapx": None if mx is None else str(mx),
                "mapy": None if my is None else str(my),
            }
        )

    out["members"] = members

    xs: List[float] = []
    ys: List[float] = []
    for mm in members:
        mx = _to_float(mm.get("mapx"))
        my = _to_float(mm.get("mapy"))
        if _valid_xy(mx, my):
            xs.append(mx)
            ys.append(my)
    if xs and ys:
        out["rand_mapx"] = str(sum(xs) / len(xs))
        out["rand_mapy"] = str(sum(ys) / len(ys))

    return out


def collect_category_items(
    settings: Settings,
    ct: int,
    area_code: int,
    resume_done_ids: Optional[set],
    fresh: bool,
    num_rows: int,
    throttle: float,
    verbose: bool,
    test_one: bool,
    pages_limit: int,
    test_geocode_limit: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:

    params_base = _base_params(settings)
    params_base.update(
        {
            "contentTypeId": ct,
            "areaCode": area_code,
            "numOfRows": num_rows,
            "pageNo": 1,
            "arrange": "A",
        }
    )

    fetched = 0
    wrote = 0
    skipped = 0
    errors = 0

    total_count: Optional[int] = None

    geocode_calls = [0]
    cache = _load_geocode_cache(settings)
    place_index = _build_place_index(settings) if ct == 25 else {}

    out_rows: List[Dict[str, Any]] = []
    page_no = 1

    while True:

        if test_one and page_no > pages_limit:
            break

        params = dict(params_base)
        params["pageNo"] = page_no

        try:
            resp = _api_get(settings.tour_api_area_based_url, params)
            rows = _items(resp)
        except Exception:
            errors += 1
            break

        body = (resp.get("response") or {}).get("body") or {}

        if total_count is None:
            try:
                total_count = int(body.get("totalCount") or 0)
            except Exception:
                total_count = 0

        if not rows:
            break

        for row in rows:
            fetched += 1

            cid = _text(row.get("contentid") or row.get("contentId"))
            if not cid:
                continue

            if resume_done_ids is not None and cid in resume_done_ids and not fresh:
                skipped += 1
                continue

            if ct == 12:
                intro = _detail_intro(settings, cid, ct)
                pet_raw = _pet_first_and_drop_id(_detail_info_rows(settings, cid, ct))
                item = _shape_ct12(row, intro, pet_raw)

            elif ct == 14:
                intro = _detail_intro(settings, cid, ct)
                pet_raw = _pet_first_and_drop_id(_detail_info_rows(settings, cid, ct))
                item = _shape_ct14(row, intro, pet_raw)

            elif ct == 15:
                item = _shape_ct15(row)

            elif ct == 28:
                pet_raw = _pet_first_and_drop_id(_detail_info_rows(settings, cid, ct))
                item = _shape_ct28(row, pet_raw)

            elif ct == 32:
                pet_raw = _pet_first_and_drop_id(_detail_info_rows(settings, cid, ct))
                item = _shape_ct32(row, pet_raw)

            elif ct == 39:
                pet_raw = _pet_first_and_drop_id(_detail_info_rows(settings, cid, ct))
                item = _shape_ct39(row, pet_raw)

            elif ct == 25:
                intro = _detail_intro(settings, cid, ct)
                info_rows = _detail_info_rows(settings, cid, ct, verbose=verbose)
                item = _shape_trip25(
                    settings=settings,
                    base=row,
                    intro=intro,
                    info_rows=info_rows,
                    place_index=place_index,
                    cache=cache,
                    geocode_calls=geocode_calls,
                    geocode_limit=test_geocode_limit if test_one else 10**9,
                    area_code=area_code,
                )

            else:
                continue

            out_rows.append(item)
            wrote += 1

            if test_one and wrote >= 1:
                _save_geocode_cache(settings, cache)
                return out_rows, {
                    "fetched": fetched,
                    "wrote": wrote,
                    "skipped": skipped,
                    "errors": errors,
                    "geocode_calls": geocode_calls[0],
                    "total": total_count or 0,
                }

        page_no += 1
        time.sleep(throttle)

    _save_geocode_cache(settings, cache)

    return out_rows, {
        "fetched": fetched,
        "wrote": wrote,
        "skipped": skipped,
        "errors": errors,
        "geocode_calls": geocode_calls[0],
        "total": total_count or 0,
    }

