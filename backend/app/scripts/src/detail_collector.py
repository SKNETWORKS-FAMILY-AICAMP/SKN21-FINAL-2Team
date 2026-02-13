from __future__ import annotations

from typing import Any, Dict, List

from api_client import tourapi_get, extract_items


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
