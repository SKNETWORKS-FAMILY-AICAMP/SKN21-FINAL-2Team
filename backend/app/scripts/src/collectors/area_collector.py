from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.api_client import tourapi_get, extract_items, extract_total_count
from src.io_utils import ensure_dir, write_jsonl, safe_filename
from src.schema import normalize_common_record
from src.collectors.detail_collector import fetch_details_with_rate_control
from src.config import SEOUL_AREA_CODE


def collect_area_based_list(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    content_type_id: int,
    area_code: int = SEOUL_AREA_CODE,
    num_rows: int = 1000,
) -> List[Dict[str, Any]]:
    params = {
        "serviceKey": service_key,
        "MobileOS": mobile_os,
        "MobileApp": mobile_app,
        "_type": resp_type,
        "areaCode": area_code,
        "contentTypeId": content_type_id,
        "numOfRows": num_rows,
        "pageNo": 1,
        "arrange": "A",
    }

    first = tourapi_get(base_url, "areaBasedList2", params)
    total = extract_total_count(first)
    pages = max(1, math.ceil(total / num_rows))

    rows = extract_items(first)
    print(f"[area:{content_type_id}] total={total}, pages={pages}, page1={len(rows)}")

    for p in range(2, pages + 1):
        params["pageNo"] = p
        data = tourapi_get(base_url, "areaBasedList2", params)
        items = extract_items(data)
        rows.extend(items)
        if p % 10 == 0 or p == pages:
            print(f"[area:{content_type_id}] page {p}/{pages}, collected={len(rows)}")

    return rows


def build_course_segments(
    course_rows: List[Dict[str, Any]],
    detail_infos_by_course: Dict[str, List[Dict[str, Any]]],
    place_index_by_contentid: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for course in course_rows:
        course_id = str(course.get("contentid", "")).strip()
        if not course_id:
            continue

        segs = detail_infos_by_course.get(course_id, [])
        for idx, seg in enumerate(segs, 1):
            subcontentid = str(seg.get("subcontentid", "")).strip()
            linked_place = place_index_by_contentid.get(subcontentid, {}) if subcontentid else {}

            suboverview = seg.get("subdetailoverview") or seg.get("suboverview") or ""
            place_overview = linked_place.get("overview", "")

            record = {
                "course_contentid": course_id,
                "course_title": course.get("title", ""),
                "subnum": seg.get("subnum", idx),
                "subname": seg.get("subname", ""),
                "subcontentid": subcontentid,
                "suboverview": suboverview,

                "linked_place_found": True if linked_place else False,
                "linked_title": linked_place.get("title", ""),
                "mapx": linked_place.get("mapx", ""),
                "mapy": linked_place.get("mapy", ""),
                "addr1": linked_place.get("addr1", ""),
                "addr2": linked_place.get("addr2", ""),
                "place_overview": place_overview,

                "use_suboverview": bool(suboverview and suboverview.strip() and suboverview.strip() != str(place_overview).strip()),
            }
            out.append(record)

    def _subnum_key(x: Dict[str, Any]):
        v = x.get("subnum", "")
        try:
            return int(v)
        except Exception:
            return 10**9

    out.sort(key=lambda r: (str(r.get("course_contentid", "")), _subnum_key(r)))
    return out


def collect_category_dataset(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    outdir: Path,
    content_type_id: int,
    label: str,
    area_code: int = SEOUL_AREA_CODE,
    num_rows: int = 1000,
    throttle_s: float = 2.0,
    batch_size: int = 50,
    batch_sleep_s: float = 30.0,
) -> Tuple[Path, Path]:
    ensure_dir(outdir)
    safe_label = safe_filename(label)

    places_path = outdir / f"places_contentType{content_type_id}_{safe_label}.jsonl"
    segments_path = outdir / f"course_segments_contentType{content_type_id}_{safe_label}.jsonl"

    area_rows = collect_area_based_list(
        base_url=base_url,
        service_key=service_key,
        mobile_os=mobile_os,
        mobile_app=mobile_app,
        resp_type=resp_type,
        content_type_id=content_type_id,
        area_code=area_code,
        num_rows=num_rows,
    )

    content_ids = [str(r.get("contentid", "")).strip() for r in area_rows if str(r.get("contentid", "")).strip()]
    unique_ids = list(dict.fromkeys(content_ids))
    print(f"[collect:{content_type_id}] area_rows={len(area_rows)}, unique_ids={len(unique_ids)}")

    commons, intros, infos, pets = fetch_details_with_rate_control(
        content_ids=unique_ids,
        content_type_id=content_type_id,
        base_url=base_url,
        service_key=service_key,
        mobile_os=mobile_os,
        mobile_app=mobile_app,
        resp_type=resp_type,
        throttle_s=throttle_s,
        batch_size=batch_size,
        batch_sleep_s=batch_sleep_s,
    )

    places: List[Dict[str, Any]] = []
    for base in area_rows:
        cid = str(base.get("contentid", "")).strip()
        if not cid:
            continue
        common = commons.get(cid, {})
        intro = intros.get(cid, {})
        pet = pets.get(cid, {})

        row = normalize_common_record(base, common, intro)
        if pet:
            row["pet_raw"] = pet
        row["contentid"] = cid
        row["contenttypeid"] = str(content_type_id)
        places.append(row)

    write_jsonl(places_path, places, append=False)

    if int(content_type_id) == 25:
        place_index = {str(r.get("contentid", "")).strip(): r for r in places if str(r.get("contentid", "")).strip()}
        segments = build_course_segments(places, infos, place_index)
        write_jsonl(segments_path, segments, append=False)
    else:
        write_jsonl(segments_path, [], append=False)

    print(f"✅ DONE category {content_type_id} ({label})")
    print(f" - places: {places_path}")
    print(f" - segments: {segments_path}")

    return places_path, segments_path


def collect_multi_categories_into_one_file(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    outdir: Path,
    category_map: Dict[int, str],  # {14:"문화시설", ...}
    area_code: int = SEOUL_AREA_CODE,
    num_rows: int = 1000,
    throttle_s: float = 2.0,
    batch_size: int = 50,
    batch_sleep_s: float = 30.0,
) -> Tuple[Path, Path]:
    """
    여러 contentType을 순회해서
    - places: 하나의 통합 파일로 저장
    - course_segments(25): 하나의 통합 파일로 저장
    """
    ensure_dir(outdir)

    all_places: List[Dict[str, Any]] = []
    all_segments: List[Dict[str, Any]] = []

    # 전체 장소 인덱스(세그먼트 연결용): 나중에 course segment subcontentid 매칭 강화에 활용
    global_place_index: Dict[str, Dict[str, Any]] = {}

    for ctid, label in category_map.items():
        print(f"\n===== START contentType {ctid} ({label}) =====")

        area_rows = collect_area_based_list(
            base_url=base_url,
            service_key=service_key,
            mobile_os=mobile_os,
            mobile_app=mobile_app,
            resp_type=resp_type,
            content_type_id=ctid,
            area_code=area_code,
            num_rows=num_rows,
        )

        ids = [str(r.get("contentid", "")).strip() for r in area_rows if str(r.get("contentid", "")).strip()]
        unique_ids = list(dict.fromkeys(ids))
        print(f"[collect:{ctid}] area_rows={len(area_rows)}, unique_ids={len(unique_ids)}")

        commons, intros, infos, pets = fetch_details_with_rate_control(
            content_ids=unique_ids,
            content_type_id=ctid,
            base_url=base_url,
            service_key=service_key,
            mobile_os=mobile_os,
            mobile_app=mobile_app,
            resp_type=resp_type,
            throttle_s=throttle_s,
            batch_size=batch_size,          # 50
            batch_sleep_s=batch_sleep_s,    # 30초
        )

        cat_places: List[Dict[str, Any]] = []
        for base in area_rows:
            cid = str(base.get("contentid", "")).strip()
            if not cid:
                continue

            row = normalize_common_record(
                base=base,
                common=commons.get(cid, {}),
                intro=intros.get(cid, {}),
            )
            if pets.get(cid):
                row["pet_raw"] = pets[cid]

            row["contentid"] = cid
            row["contenttypeid"] = str(ctid)
            row["contenttype_label"] = label
            cat_places.append(row)

        all_places.extend(cat_places)

        # 글로벌 인덱스 갱신
        for r in cat_places:
            rcid = str(r.get("contentid", "")).strip()
            if rcid:
                global_place_index[rcid] = r

        # 여행코스(25) 세그먼트 처리
        if int(ctid) == 25:
            cat_place_index = {str(r.get("contentid", "")).strip(): r for r in cat_places if str(r.get("contentid", "")).strip()}
            segments = build_course_segments(cat_places, infos, cat_place_index)
            all_segments.extend(segments)

        print(f"===== END contentType {ctid} ({label}) =====\n")

    # 25 세그먼트의 linked_place 보강(전체 카테고리 인덱스로 2차 매칭)
    if all_segments:
        for seg in all_segments:
            if not seg.get("linked_place_found"):
                subid = str(seg.get("subcontentid", "")).strip()
                if subid and subid in global_place_index:
                    p = global_place_index[subid]
                    seg["linked_place_found"] = True
                    seg["linked_title"] = p.get("title", "")
                    seg["mapx"] = p.get("mapx", "")
                    seg["mapy"] = p.get("mapy", "")
                    seg["addr1"] = p.get("addr1", "")
                    seg["addr2"] = p.get("addr2", "")
                    seg["place_overview"] = p.get("overview", "")

    places_out = outdir / "places_contentType14_39_all.jsonl"
    seg_out = outdir / "course_segments_contentType14_39_all.jsonl"

    write_jsonl(places_out, all_places, append=False)
    write_jsonl(seg_out, all_segments, append=False)

    print("✅ DONE multi categories -> one file")
    print(f" - places(all): {places_out} rows={len(all_places)}")
    print(f" - segments(all): {seg_out} rows={len(all_segments)}")

    return places_out, seg_out
