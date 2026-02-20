import time
from typing import Any, Dict, List, Optional, Tuple

from .__config import Settings
from .__utils import _text
from .__api_client import _base_params, _api_get, _items, _detail_intro, _detail_info_rows, _detail_pet_tour_rows
from .__geocoder import _load_geocode_cache, _save_geocode_cache
from .__parsers import (
    _extract_fees_from_detail_info, _pet_first_and_drop_id, _build_place_index,
    _shape_common, _shape_trip25
)

def collect_category_items(
    settings: Settings, ct: int, area_code: int, resume_done_ids: Optional[set],
    fresh: bool, num_rows: int, throttle: float, verbose: bool,
    test_one: bool, pages_limit: int, test_geocode_limit: int,
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
        if test_one and page_no > pages_limit: break
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
            try: total_count = int(body.get("totalCount") or 0)
            except Exception: total_count = 0

        if not rows: break

        for row in rows:
            fetched += 1
            cid = _text(row.get("contentid") or row.get("contentId"))
            if not cid: continue
            
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
                if fees: item["fees"] = fees
                if pet_tmp is not None: item["pet_raw"] = pet_tmp

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