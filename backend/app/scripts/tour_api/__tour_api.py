from __future__ import annotations



import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False


def _load_env_file_fallback(path: Path) -> None:
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except Exception:
        return

TYPE_LABELS: Dict[int, str] = {
    12: "관광지",
    14: "문화시설",
    15: "축제공연행사",
    25: "여행코스",
    28: "레포츠",
    32: "숙박",
    39: "음식점",
}


@dataclass
class Settings:
    project_root: Path
    data_dir: Path
    checkpoints_dir: Path
    tour_api_key: str
    tour_base_url: str
    tour_mobile_os: str
    tour_mobile_app: str
    tour_api_type: str
    tour_api_area_based_url: str
    tour_api_detail_intro_url: str
    tour_api_detail_info_url: str
    tour_api_detail_pet_tour_url: str
    tour_api_search_keyword_url: str
    kakao_rest_api_key: str
    naver_client_id: str
    naver_client_secret: str


def load_settings() -> Settings:
    this = Path(__file__).resolve()
    project_root = this.parents[4]

    env_candidates = [
        project_root / ".env",
        project_root / "backend" / ".env",
        project_root / "backend" / "app" / "scripts" / "tour_api" / ".env",
        project_root / "backend" / "app" / "scripts" / "src" / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(env_path)
            _load_env_file_fallback(env_path)

    data_dir = project_root / "backend" / "data"
    checkpoints_dir = data_dir / "checkpoints"
    data_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    base = os.getenv("TOURAPI_BASE_URL", "https://apis.data.go.kr/B551011/KorService2").strip().rstrip("/")
    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        checkpoints_dir=checkpoints_dir,
        tour_api_key=os.getenv("TOURAPI_KEY", "").strip(),
        tour_base_url=base,
        tour_mobile_os=os.getenv("TOURAPI_MOBILE_OS", "ETC").strip(),
        tour_mobile_app=os.getenv("TOURAPI_MOBILE_APP", "polarisK").strip(),
        tour_api_type=os.getenv("TOURAPI_TYPE", "json").strip(),
        tour_api_area_based_url=f"{base}/areaBasedList2",
        tour_api_detail_intro_url=f"{base}/detailIntro2",
        tour_api_detail_info_url=f"{base}/detailInfo2",
        tour_api_detail_pet_tour_url=f"{base}/detailPetTour2",
        tour_api_search_keyword_url=f"{base}/searchKeyword2",
        kakao_rest_api_key=os.getenv("KAKAO_REST_API_KEY", "").strip(),
        naver_client_id=os.getenv("NAVER_CLIENT_ID", "").strip(),
        naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", "").strip(),
    )


def places_jsonl_path(settings: Settings, ct: int) -> Path:
    return settings.data_dir / f"{ct}_{TYPE_LABELS.get(ct, str(ct))}.jsonl"


def places_test_jsonl_path(settings: Settings, ct: int) -> Path:
    return settings.data_dir / f"{ct}_{TYPE_LABELS.get(ct, str(ct))}_TEST1.jsonl"


def geocode_cache_path(settings: Settings) -> Path:
    return settings.data_dir / "geocode_cache.json"


def checkpoint_path(settings: Settings, ct: int) -> Path:
    return settings.checkpoints_dir / f"ct_{ct}_progress.json"


import html
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests


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


def _normalize_fee_text(value: str) -> str:
    text = html.unescape(_text(value))
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text in {"0", "0원"}:
        return "무료"
    return text


def _extract_fee_from_detail_info(rows: List[Dict[str, Any]]) -> str:
    fees: List[str] = []
    for row in rows or []:
        key = (row.get("infoname") or "").strip()
        value = (row.get("infotext") or "").strip()
        if key in FEE_KEYS and value:
            cleaned = _normalize_fee_text(value)
            if cleaned and cleaned not in fees:
                fees.append(cleaned)
    return " ".join(fees).strip()


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
        "fee": "",
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
                fee = _extract_fee_from_detail_info(info_rows)
                pet_raw = _pet_first_and_drop_id(_detail_pet_tour_rows(settings, cid, ct, verbose=verbose))
                item = _shape_common(ct, row, intro, pet_raw)
                pet_tmp = item.pop("pet_raw", None)
                if fee:
                    item["fee"] = fee
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


import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


SEOUL_CULTURE_LIST_URL = "https://culture.seoul.go.kr/culture/culture/cultureEvent/jsonList.json"
SEOUL_CULTURE_IMAGE_URL = "https://culture.seoul.go.kr/cmmn/file/getImage.do"
VISITKOREA_IMAGE_CALL_PREFIX = "https://cdn.visitkorea.or.kr/img/call?cmd=VIEW&id="
DEFAULT_OUTPUT_PATH = Path("backend/data/image_add/15_축제공연행사_image_add.jsonl")
TODAY = date.today()


@dataclass
class EventRow:
    contentid: str
    title: str
    contenttypeid: str
    contenttypeid_code: str
    category: str
    image: str
    usetime: str
    restdate: str
    parking: str
    place: str
    addr: str
    mapy: str
    mapx: str
    tel: str
    period: str
    llm_text: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _norm_space(value: str) -> str:
    return re.sub(r"\s+", " ", _text(value)).strip()


def _norm_title(value: str) -> str:
    value = _norm_space(value)
    value = value.lower()
    value = re.sub(r"\s*[\-–~]+\s*", " ", value)
    return value


def _norm_addr(value: str) -> str:
    value = _norm_space(value)
    value = value.replace("서울특별시", "서울")
    return value


def _absolute_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://culture.seoul.go.kr" + url
    return url


def _build_seoul_culture_image_url(atch_file_id: str) -> str:
    if not atch_file_id:
        return ""
    return f"{SEOUL_CULTURE_IMAGE_URL}?atchFileId={atch_file_id}&thumb=Y"


def _try_parse_date(value: str) -> Optional[date]:
    value = _text(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _format_period(start_value: str, end_value: str) -> str:
    start = _try_parse_date(start_value)
    end = _try_parse_date(end_value)
    if start and end:
        return f"{start.isoformat()} ~ {end.isoformat()}"
    if start:
        return f"{start.isoformat()} ~ {start.isoformat()}"
    return ""


def _event_is_active_or_upcoming(start_value: str, end_value: str) -> bool:
    start = _try_parse_date(start_value)
    end = _try_parse_date(end_value)
    if end:
        return end >= TODAY
    if start:
        return start >= TODAY
    return True


def _tour_api_params(settings, extra: Dict[str, Any], tour_api_key: str) -> Dict[str, Any]:
    params = {
        "serviceKey": tour_api_key,
        "MobileOS": settings.tour_mobile_os,
        "MobileApp": settings.tour_mobile_app,
        "_type": settings.tour_api_type,
    }
    params.update(extra)
    return params


def _tour_api_get(url: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _tour_api_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = (payload.get("response") or {}).get("body") or {}
    items = (body.get("items") or {}).get("item")
    if items is None:
        return []
    if isinstance(items, list):
        return items
    return [items]


def _visitkorea_image_url(raw_url: str) -> str:
    raw_url = _absolute_url(raw_url)
    match = re.search(r"id=([0-9a-f\-]{32,36})", raw_url, re.I)
    if match:
        return VISITKOREA_IMAGE_CALL_PREFIX + match.group(1)
    match = re.search(r"/([0-9a-f\-]{32,36})(?:_[^/]+)?\.(?:jpg|jpeg|png|webp)$", raw_url, re.I)
    if match:
        return VISITKOREA_IMAGE_CALL_PREFIX + match.group(1)
    return raw_url


def fetch_seoul_culture_events(search_cate: str = "SHOW", menu_no: str = "200008", max_pages: Optional[int] = None) -> List[EventRow]:
    rows: List[EventRow] = []
    seen_ids: set[str] = set()
    seen_page_signatures: set[Tuple[str, ...]] = set()
    page_index = 1

    while True:
        if max_pages is not None and page_index > max_pages:
            break
        response = requests.post(
            SEOUL_CULTURE_LIST_URL,
            data={"searchCate": search_cate, "menuNo": menu_no, "pageIndex": str(page_index)},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        result_list = payload.get("resultList") or []
        if not result_list:
            break

        page_signature = tuple(_text(item.get("cultcode")) for item in result_list)
        if page_signature in seen_page_signatures:
            break
        seen_page_signatures.add(page_signature)

        added = 0
        for item in result_list:
            contentid = _text(item.get("cultcode"))
            if not contentid or contentid in seen_ids:
                continue
            start_value = _text(item.get("strtdate"))
            end_value = _text(item.get("endDate"))
            if not _event_is_active_or_upcoming(start_value, end_value):
                continue
            seen_ids.add(contentid)
            added += 1

            image = _absolute_url(_text(item.get("mainImg")))
            if not image:
                image = _build_seoul_culture_image_url(_text(item.get("atchFileId")))

            rows.append(
                EventRow(
                    contentid=contentid,
                    title=_text(item.get("title")),
                    contenttypeid="축제공연행사",
                    contenttypeid_code="15",
                    category=_text(item.get("subjcodeGroupNm") or item.get("subjcodeNm")),
                    image=image,
                    usetime="",
                    restdate="",
                    parking="",
                    place=_text(item.get("facName")),
                    addr=_text(item.get("addr")),
                    mapy=_text(item.get("xCoord")),
                    mapx=_text(item.get("yCoord")),
                    tel="",
                    period=_format_period(start_value, end_value),
                    llm_text="",
                )
            )

        if added == 0:
            break
        page_index += 1

    return rows


def fetch_tour_api_events(tour_api_key: str, area_code: int = 1) -> List[EventRow]:
    settings = load_settings()
    rows: List[EventRow] = []
    page_no = 1

    while True:
        params = _tour_api_params(
            settings,
            {
                "contentTypeId": 15,
                "areaCode": area_code,
                "pageNo": page_no,
                "numOfRows": 200,
                "arrange": "A",
            },
            tour_api_key,
        )
        payload = _tour_api_get(settings.tour_api_area_based_url, params)
        items = _tour_api_items(payload)
        if not items:
            break

        for item in items:
            contentid = _text(item.get("contentid") or item.get("contentId"))
            if not contentid:
                continue

            intro_params = _tour_api_params(
                settings,
                {"contentId": contentid, "contentTypeId": 15},
                tour_api_key,
            )
            intro_payload = _tour_api_get(settings.tour_api_detail_intro_url, intro_params)
            intro_list = _tour_api_items(intro_payload)
            intro = intro_list[0] if intro_list else {}

            start_value = _text(intro.get("eventstartdate"))
            end_value = _text(intro.get("eventenddate"))
            if not _event_is_active_or_upcoming(start_value, end_value):
                continue

            rows.append(
                EventRow(
                    contentid=contentid,
                    title=_text(item.get("title")),
                    contenttypeid="축제공연행사",
                    contenttypeid_code="15",
                    category="축제",
                    image=_visitkorea_image_url(_text(item.get("firstimage"))),
                    usetime=_text(intro.get("playtime")),
                    restdate="",
                    parking="",
                    place=_text(intro.get("eventplace")),
                    addr=_text(item.get("addr1")),
                    mapy=_text(item.get("mapy")),
                    mapx=_text(item.get("mapx")),
                    tel=_text(item.get("tel") or intro.get("sponsor1tel")),
                    period=_format_period(start_value, end_value),
                    llm_text="",
                )
            )

        page_no += 1

    return rows


def dedupe_event_rows(rows: Iterable[EventRow]) -> List[EventRow]:
    best_by_key: Dict[Tuple[str, str, str], EventRow] = {}

    def score(row: EventRow) -> Tuple[int, int, int, int]:
        return (
            1 if "culture.seoul.go.kr" in row.image else 0,
            1 if row.place else 0,
            1 if row.addr else 0,
            1 if row.period else 0,
        )

    for row in rows:
        key = (_norm_title(row.title), _norm_space(row.period), _norm_addr(row.addr))
        current = best_by_key.get(key)
        if current is None or score(row) > score(current):
            best_by_key[key] = row

    merged = list(best_by_key.values())
    merged.sort(key=lambda r: (r.period or "9999-99-99", r.title, r.addr))
    return merged


def write_event_rows(path: Path, rows: Iterable[EventRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            raw = row.to_dict()
            ordered = {
                "contentid": _text(raw.get("contentid")),
                "title": _text(raw.get("title")),
                "contenttypeid": _text(raw.get("contenttypeid")),
                "contenttypeid_code": _text(raw.get("contenttypeid_code")),
                "category": _text(raw.get("category")),
                "image": _text(raw.get("image")),
                "usetime": _text(raw.get("usetime")),
                "restdate": _text(raw.get("restdate")),
                "parking": _text(raw.get("parking")),
                "fee": _text(raw.get("fee")),
                "place": _text(raw.get("place")),
                "addr": _text(raw.get("addr")),
                "mapy": _text(raw.get("mapy")),
                "mapx": _text(raw.get("mapx")),
                "tel": _text(raw.get("tel")),
                "period": _text(raw.get("period")),
                "llm_text": _text(raw.get("llm_text")),
            }
            handle.write(json.dumps(ordered, ensure_ascii=False) + "\n")


def build_festival_image_add(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    tour_api_key: str = "",
    include_tour_api: bool = True,
    max_seoul_pages: Optional[int] = None,
) -> Dict[str, Any]:
    seoul_rows = fetch_seoul_culture_events(max_pages=max_seoul_pages)
    tour_rows: List[EventRow] = []
    effective_key = tour_api_key or os.getenv("TOURAPI_KEY", "").strip()
    if include_tour_api and effective_key:
        tour_rows = fetch_tour_api_events(effective_key)

    merged_rows = dedupe_event_rows([*seoul_rows, *tour_rows])
    write_event_rows(output_path, merged_rows)

    return {
        "output_path": str(output_path),
        "seoul_culture_count": len(seoul_rows),
        "tour_api_count": len(tour_rows),
        "merged_count": len(merged_rows),
        "tour_api_included": bool(tour_rows),
    }


from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
