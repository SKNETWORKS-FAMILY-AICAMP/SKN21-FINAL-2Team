from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from .__config import Settings, checkpoint_path, geocode_cache_path, places_jsonl_path, places_test_jsonl_path

FEE_KEYS = {"입장료", "이용요금", "이용요금(입장료)"}
COMMON_LABELS = {12: "관광지", 14: "문화시설", 15: "축제공연행사", 28: "레포츠", 32: "숙박", 39: "음식점"}


def _text(x: Any) -> str:
    return "" if x is None else str(x).strip()


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _valid_xy(x: Optional[float], y: Optional[float]) -> bool:
    return x is not None and y is not None and 120.0 <= x <= 132.0 and 33.0 <= y <= 39.5


def _norm_name(name: str) -> str:
    s = _text(name)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\[.*?\]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_progress(path: Path) -> Dict[str, Any]:
    p = read_json(path, default={})
    if not isinstance(p, dict):
        p = {}
    done_ids = p.get("done_ids", [])
    if not isinstance(done_ids, list):
        done_ids = []
    done_ids = [str(x) for x in done_ids]
    processed = p.get("processed")
    if not isinstance(processed, int):
        processed = len(done_ids)
    return {
        "done_ids": done_ids,
        "processed": int(processed),
        "last_index": int(p.get("last_index") if p.get("last_index") is not None else (len(done_ids) - 1)),
        "total": int(p.get("total") or 0),
        "updated_at": str(p.get("updated_at") or ""),
    }


def save_progress(path: Path, pr: Dict[str, Any]) -> None:
    done_ids = [str(x) for x in (pr.get("done_ids") or [])]
    processed = pr.get("processed") if isinstance(pr.get("processed"), int) else len(done_ids)
    last_index = pr.get("last_index") if isinstance(pr.get("last_index"), int) else len(done_ids) - 1
    write_json(path, {
        "done_ids": done_ids,
        "processed": int(processed),
        "last_index": int(last_index),
        "total": int(pr.get("total") or 0),
        "updated_at": now_iso(),
    })


def _load_done_ids(settings: Settings, ct: int) -> Set[str]:
    return set(load_progress(checkpoint_path(settings, ct)).get("done_ids") or [])


def _append_done_ids(settings: Settings, ct: int, ids: List[str], *, total: int | None = None) -> None:
    path = checkpoint_path(settings, ct)
    progress = load_progress(path)
    done = list(dict.fromkeys(progress.get("done_ids", []) + [str(x) for x in ids]))
    progress["done_ids"] = done
    progress["processed"] = len(done)
    progress["updated_at"] = now_iso()
    progress["last_index"] = max(int(progress.get("last_index") or -1), len(done) - 1)
    if total is not None:
        progress["total"] = int(total)
    save_progress(path, progress)


def _base_params(settings: Settings) -> Dict[str, Any]:
    return {
        "serviceKey": settings.tour_api_key,
        "MobileOS": settings.tour_mobile_os,
        "MobileApp": settings.tour_mobile_app,
        "_type": settings.tour_api_type,
    }


def _api_get(url: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _items(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = (resp.get("response") or {}).get("body") or {}
    items = (body.get("items") or {}).get("item")
    if items is None:
        return []
    if isinstance(items, list):
        return items
    return [items]


def _detail_intro(settings: Settings, content_id: str, ct: int) -> Dict[str, Any]:
    params = _base_params(settings)
    params.update({"contentId": content_id, "contentTypeId": ct})
    try:
        rows = _items(_api_get(settings.tour_api_detail_intro_url, params))
        return rows[0] if rows else {}
    except Exception:
        return {}


def _detail_info_rows(settings: Settings, content_id: str, ct: int, *, verbose: bool = False) -> List[Dict[str, Any]]:
    params = _base_params(settings)
    params.update({"contentId": str(content_id), "contentTypeId": str(ct), "pageNo": 1, "numOfRows": 100})
    try:
        return _items(_api_get(settings.tour_api_detail_info_url, params))
    except Exception as exc:
        if verbose:
            print(f"[detailInfo2 EXCEPTION] ct={ct} {exc}")
        return []


def _detail_pet_tour_rows(settings: Settings, content_id: str, ct: int, *, verbose: bool = False) -> List[Dict[str, Any]]:
    params = _base_params(settings)
    params.update({"contentId": str(content_id), "pageNo": 1, "numOfRows": 100})
    try:
        resp = _api_get(settings.tour_api_detail_pet_tour_url, params)
        response = resp.get("response") if isinstance(resp, dict) else None
        body = response.get("body") if isinstance(response, dict) else None
        items = body.get("items") if isinstance(body, dict) else None
        items = items.get("item") if isinstance(items, dict) else items
        if items is None:
            return []
        if isinstance(items, list):
            return items
        if isinstance(items, dict):
            return [items]
        return []
    except Exception as exc:
        if verbose:
            print(f"[detailPetTour2 EXCEPTION] ct={ct} {exc}")
        return []


def _load_geocode_cache(settings: Settings) -> Dict[str, Any]:
    return read_json(geocode_cache_path(settings), default={}) or {}


def _save_geocode_cache(settings: Settings, cache: Dict[str, Any]) -> None:
    write_json(geocode_cache_path(settings), cache)


def _kakao_geocode(settings: Settings, query: str) -> Optional[Tuple[float, float]]:
    if not settings.kakao_rest_api_key:
        return None
    q = _text(query)
    if not q:
        return None
    headers = {"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"}
    try:
        resp = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            params={"query": q, "size": 1},
            headers=headers,
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        docs = resp.json().get("documents") or []
        if not docs:
            return None
        x, y = _to_float(docs[0].get("x")), _to_float(docs[0].get("y"))
        return (x, y) if _valid_xy(x, y) else None
    except Exception:
        return None


def _naver_geocode(settings: Settings, query: str) -> Optional[Tuple[float, float]]:
    if not (settings.naver_client_id and settings.naver_client_secret):
        return None
    q = _text(query)
    if not q:
        return None
    headers = {
        "X-NCP-APIGW-API-KEY-ID": settings.naver_client_id,
        "X-NCP-APIGW-API-KEY": settings.naver_client_secret,
    }
    try:
        resp = requests.get(
            "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode",
            params={"query": q},
            headers=headers,
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        addrs = resp.json().get("addresses") or []
        if not addrs:
            return None
        x, y = float(addrs[0].get("x")), float(addrs[0].get("y"))
        return (x, y) if _valid_xy(x, y) else None
    except Exception:
        return None


def _geocode_with_cache(settings: Settings, query: str, cache: Dict[str, Any], geocode_calls: List[int], geocode_limit: int) -> Optional[Tuple[float, float]]:
    key = _text(query)
    if not key:
        return None
    if key in cache:
        cached = cache.get(key)
        if isinstance(cached, dict):
            x, y = _to_float(cached.get("x")), _to_float(cached.get("y"))
            return (x, y) if _valid_xy(x, y) else None
        return None
    if geocode_calls[0] >= geocode_limit:
        return None
    res = _kakao_geocode(settings, key) or _naver_geocode(settings, key)
    geocode_calls[0] += 1
    cache[key] = {"x": res[0], "y": res[1]} if res else {"x": None, "y": None}
    return res


def _extract_fees_from_detail_info(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    fees = []
    for row in rows or []:
        key = (row.get("infoname") or "").strip()
        value = (row.get("infotext") or "").strip()
        if key in FEE_KEYS and value:
            fees.append({"name": key, "text": value})
    return fees


def _pet_first_and_drop_id(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None
    if not isinstance(rows[0], dict):
        return None
    data = dict(rows[0])
    data.pop("contentid", None)
    data.pop("contentId", None)
    return data


def _build_place_index(settings: Settings) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for ct in [12, 14, 15, 28, 32, 39]:
        for row in read_jsonl(places_jsonl_path(settings, ct)):
            cid = _text(row.get("contentid"))
            x, y = _to_float(row.get("mapx")), _to_float(row.get("mapy"))
            if cid and _valid_xy(x, y):
                out[cid] = (x, y)
    return out


def _shape_common(ct: int, base: Dict[str, Any], intro: Dict[str, Any], pet_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    item = {
        "contentid": _text(base.get("contentid") or base.get("contentId")),
        "title": _text(base.get("title")),
        "contenttypeid": COMMON_LABELS.get(ct, str(ct)),
        "image": _text(base.get("firstimage")),
        "usetime": _text(intro.get("usetime") or intro.get("usetimeTourinfo") or base.get("usetime")),
        "restdate": _text(intro.get("restdate") or base.get("restdate")),
        "parking": _text(intro.get("parking") or base.get("parking")),
        "addr": _text(base.get("addr1")),
        "mapy": _text(base.get("mapy")),
        "mapx": _text(base.get("mapx")),
        "tel": _text(base.get("tel")),
        "contenttypeid_code": str(ct),
    }
    if pet_raw is not None:
        item["pet_raw"] = pet_raw
    return item


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
    out = {
        "contentid": cid,
        "course_contentid": cid,
        "course_title": _text(base.get("title")),
        "overview": intro.get("overview") if intro else None,
        "rand_mapy": None,
        "rand_mapx": None,
        "members": [],
    }
    members = []
    for row in info_rows or []:
        subname = _text(row.get("subname"))
        subcontentid = _text(row.get("subcontentid"))
        suboverview = _text(row.get("suboverview"))
        if not suboverview:
            for key, value in row.items():
                if "overview" in str(key).lower() and _text(value):
                    suboverview = _text(value)
                    break
        mx, my = _to_float(row.get("mapx")), _to_float(row.get("mapy"))
        if not _valid_xy(mx, my):
            if subcontentid and subcontentid in place_index:
                mx, my = place_index[subcontentid]
            else:
                q1 = _norm_name(subname)
                q2 = f"{q1} 서울" if area_code == 1 else q1
                res = _geocode_with_cache(settings, q2, cache, geocode_calls, geocode_limit) or _geocode_with_cache(settings, q1, cache, geocode_calls, geocode_limit)
                if res:
                    mx, my = res
        members.append({
            "subname": subname,
            "subcontentid": subcontentid,
            "suboverview": suboverview,
            "mapx": str(mx) if mx else None,
            "mapy": str(my) if my else None,
        })
    out["members"] = members
    xs = [float(m["mapx"]) for m in members if m["mapx"]]
    ys = [float(m["mapy"]) for m in members if m["mapy"]]
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
    params_base.update({"contentTypeId": ct, "areaCode": area_code, "numOfRows": num_rows, "pageNo": 1, "arrange": "A"})

    fetched = wrote = skipped = errors = 0
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

            if ct in (12, 14, 15, 28, 32, 39):
                intro = _detail_intro(settings, cid, ct)
                info_rows = _detail_info_rows(settings, cid, ct, verbose=verbose)
                fees = _extract_fees_from_detail_info(info_rows)
                pet_raw = _pet_first_and_drop_id(_detail_pet_tour_rows(settings, cid, ct, verbose=verbose))
                item = _shape_common(ct, row, intro, pet_raw)
                pet_tmp = item.pop("pet_raw", None)
                if fees:
                    item["fees"] = fees
                if pet_tmp is not None:
                    item["pet_raw"] = pet_tmp
            elif ct == 25:
                intro = _detail_intro(settings, cid, ct)
                info_rows = _detail_info_rows(settings, cid, ct, verbose=verbose)
                item = _shape_trip25(settings, row, intro, info_rows, place_index, cache, geocode_calls, test_geocode_limit if test_one else 10**9, area_code)
            else:
                continue

            out_rows.append(item)
            wrote += 1
            if test_one and wrote >= 1:
                _save_geocode_cache(settings, cache)
                return out_rows, {"fetched": fetched, "wrote": wrote, "skipped": skipped, "errors": errors, "geocode_calls": geocode_calls[0], "total": total_count or 0}

        page_no += 1
        time.sleep(throttle)

    _save_geocode_cache(settings, cache)
    return out_rows, {"fetched": fetched, "wrote": wrote, "skipped": skipped, "errors": errors, "geocode_calls": geocode_calls[0], "total": total_count or 0}


def run_pipeline(
    settings: Settings,
    content_types: List[int],
    area_code: int,
    resume: bool,
    fresh: bool,
    num_rows: int,
    throttle: float,
    verbose: bool,
    test_one: bool,
    test_pages: int,
    test_geocode_limit: int,
) -> Dict[int, Dict[str, int]]:
    summary: Dict[int, Dict[str, int]] = {}
    for ct in content_types:
        resume_done_ids: Optional[set] = _load_done_ids(settings, ct) if resume else None
        rows, meta = collect_category_items(
            settings=settings,
            ct=ct,
            area_code=area_code,
            resume_done_ids=resume_done_ids,
            fresh=fresh,
            num_rows=num_rows,
            throttle=throttle,
            verbose=verbose,
            test_one=test_one,
            pages_limit=test_pages,
            test_geocode_limit=test_geocode_limit,
        )
        out_path = places_test_jsonl_path(settings, ct) if test_one else places_jsonl_path(settings, ct)
        if test_one:
            write_jsonl(out_path, rows)
            if verbose:
                print(f"[WRITE] ct={ct} -> {out_path} rows={len(rows)}")
        else:
            prev = read_jsonl(out_path)
            prev_map = {str(r.get("contentid")): r for r in prev if r.get("contentid")}
            new_ids: List[str] = []
            for row in rows:
                cid = str(row.get("contentid") or "")
                if not cid:
                    continue
                prev_map[cid] = row
                new_ids.append(cid)
            merged = list(prev_map.values())
            write_jsonl(out_path, merged)
            _append_done_ids(settings, ct, new_ids, total=int(meta.get("total") or 0))
            if verbose:
                print(f"[WRITE] ct={ct} -> {out_path} rows={len(merged)}")
        summary[ct] = {
            "fetched": int(meta.get("fetched") or 0),
            "wrote": int(meta.get("wrote") or 0),
            "skipped": int(meta.get("skipped") or 0),
            "errors": int(meta.get("errors") or 0),
            "geocode_calls": int(meta.get("geocode_calls") or 0),
        }
    return summary
