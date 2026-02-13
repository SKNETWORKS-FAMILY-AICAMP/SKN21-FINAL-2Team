from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

from src.api_client import tourapi_get, extract_items


def fetch_detail_common(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    content_id: str,
) -> Dict[str, Any]:
    params = {
        "serviceKey": service_key,
        "MobileOS": mobile_os,
        "MobileApp": mobile_app,
        "_type": resp_type,
        "contentId": content_id,
        "defaultYN": "Y",
        "firstImageYN": "Y",
        "areacodeYN": "Y",
        "catcodeYN": "Y",
        "addrinfoYN": "Y",
        "mapinfoYN": "Y",
        "overviewYN": "Y",
    }
    data = tourapi_get(base_url, "detailCommon2", params)
    items = extract_items(data)
    return items[0] if items else {}


def fetch_detail_intro(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    content_id: str,
    content_type_id: int,
) -> Dict[str, Any]:
    params = {
        "serviceKey": service_key,
        "MobileOS": mobile_os,
        "MobileApp": mobile_app,
        "_type": resp_type,
        "contentId": content_id,
        "contentTypeId": content_type_id,
    }
    data = tourapi_get(base_url, "detailIntro2", params)
    items = extract_items(data)
    return items[0] if items else {}


def fetch_detail_info(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    content_id: str,
    content_type_id: int,
) -> List[Dict[str, Any]]:
    params = {
        "serviceKey": service_key,
        "MobileOS": mobile_os,
        "MobileApp": mobile_app,
        "_type": resp_type,
        "contentId": content_id,
        "contentTypeId": content_type_id,
    }
    data = tourapi_get(base_url, "detailInfo2", params)
    return extract_items(data)


def fetch_detail_pet_tour(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    content_id: str,
) -> Dict[str, Any]:
    params = {
        "serviceKey": service_key,
        "MobileOS": mobile_os,
        "MobileApp": mobile_app,
        "_type": resp_type,
        "contentId": content_id,
    }
    data = tourapi_get(base_url, "detailPetTour2", params)
    items = extract_items(data)
    return items[0] if items else {}


def fetch_details_with_rate_control(
    content_ids: List[str],
    content_type_id: int,
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    throttle_s: float = 2.0,
    batch_size: int = 50,
    batch_sleep_s: float = 30.0,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
    """
    반환:
      commons[cid], intros[cid], infos[cid], pets[cid]
    """
    commons: Dict[str, Dict[str, Any]] = {}
    intros: Dict[str, Dict[str, Any]] = {}
    infos: Dict[str, List[Dict[str, Any]]] = {}
    pets: Dict[str, Dict[str, Any]] = {}

    total = len(content_ids)
    for i, cid in enumerate(content_ids, 1):
        try:
            commons[cid] = fetch_detail_common(base_url, service_key, mobile_os, mobile_app, resp_type, cid)
        except Exception as e:
            print(f"[WARN] detailCommon2 fail cid={cid}: {e}")
            commons[cid] = {}

        time.sleep(throttle_s)

        try:
            intros[cid] = fetch_detail_intro(base_url, service_key, mobile_os, mobile_app, resp_type, cid, content_type_id)
        except Exception as e:
            print(f"[WARN] detailIntro2 fail cid={cid}: {e}")
            intros[cid] = {}

        time.sleep(throttle_s)

        try:
            infos[cid] = fetch_detail_info(base_url, service_key, mobile_os, mobile_app, resp_type, cid, content_type_id)
        except Exception as e:
            print(f"[WARN] detailInfo2 fail cid={cid}: {e}")
            infos[cid] = []

        time.sleep(throttle_s)

        try:
            pets[cid] = fetch_detail_pet_tour(base_url, service_key, mobile_os, mobile_app, resp_type, cid)
        except Exception as e:
            print(f"[WARN] detailPetTour2 fail cid={cid}: {e}")
            pets[cid] = {}

        time.sleep(throttle_s)

        if i % 10 == 0 or i == total:
            print(f"[detail] {i}/{total}")

        if batch_size > 0 and (i % batch_size == 0) and i < total:
            print(f"[detail] batch pause {batch_sleep_s}s ({i}/{total})")
            time.sleep(batch_sleep_s)

    return commons, intros, infos, pets
