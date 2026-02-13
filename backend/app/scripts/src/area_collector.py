from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from api_client import tourapi_get, extract_items, extract_total_count
from detail_collector import (
    fetch_detail_common,
    fetch_detail_intro,
    fetch_detail_info,
    fetch_detail_pet_tour,
)
from io_utils import (
    ensure_dir,
    append_jsonl,
    write_jsonl,
    read_jsonl,
    save_json,
    load_json,
    save_firstimage_for_row,
)
from schema import normalize_common_record


def collect_area_based_list(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    content_type_id: int,
    area_code: int,
    num_rows: int,
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
        rows.extend(extract_items(data))
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
        for i, seg in enumerate(segs, 1):
            subid = str(seg.get("subcontentid", "")).strip()
            linked = place_index_by_contentid.get(subid, {}) if subid else {}

            suboverview = seg.get("subdetailoverview") or seg.get("suboverview") or ""
            pov = linked.get("overview", "")

            row = {
                "course_contentid": course_id,
                "course_title": course.get("title", ""),
                "subnum": seg.get("subnum", i),
                "subname": seg.get("subname", ""),
                "subcontentid": subid,
                "suboverview": suboverview,

                "linked_place_found": bool(linked),
                "linked_title": linked.get("title", ""),
                "mapx": linked.get("mapx", ""),
                "mapy": linked.get("mapy", ""),
                "addr1": linked.get("addr1", ""),
                "addr2": linked.get("addr2", ""),
                "place_overview": pov,
                "use_suboverview": bool(
                    suboverview and str(suboverview).strip() != str(pov).strip()
                ),
            }
            out.append(row)

    def _key(r: Dict[str, Any]):
        try:
            sn = int(r.get("subnum", 10**9))
        except Exception:
            sn = 10**9
        return (str(r.get("course_contentid", "")), sn)

    out.sort(key=_key)
    return out


def _checkpoint_path(outdir: Path, ctid: int) -> Path:
    ck = outdir / "checkpoints"
    ensure_dir(ck)
    return ck / f"ct_{ctid}_progress.json"


def _load_done_ids(ck_path: Path) -> set[str]:
    obj = load_json(ck_path, default={"done_ids": []})
    done = obj.get("done_ids", [])
    if not isinstance(done, list):
        return set()
    return {str(x).strip() for x in done if str(x).strip()}


def _save_ck(ck_path: Path, done_ids: set[str], idx: int, total: int) -> None:
    save_json(
        ck_path,
        {
            "done_ids": sorted(done_ids),
            "last_index": idx,
            "total": total,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
    )


def _collect_single_category_resume(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    outdir: Path,
    content_type_id: int,
    label: str,
    area_code: int,
    num_rows: int,
    throttle_s: float,
    resume: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    반환:
      places_rows(해당 카테고리 전체), course_segments(해당 카테고리, 25만 값 존재)
    """
    ensure_dir(outdir)
    places_path = outdir / f"places_contentType{content_type_id}_{label}.jsonl"
    segments_path = outdir / f"course_segments_contentType{content_type_id}_{label}.jsonl"
    ck_path = _checkpoint_path(outdir, content_type_id)

    # 목록 수집
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

    id_to_base: Dict[str, Dict[str, Any]] = {}
    ordered_ids: List[str] = []
    for r in area_rows:
        cid = str(r.get("contentid", "")).strip()
        if not cid:
            continue
        if cid not in id_to_base:
            id_to_base[cid] = r
            ordered_ids.append(cid)

    total = len(ordered_ids)
    done_ids: set[str] = set()

    if resume:
        done_ids |= _load_done_ids(ck_path)
        if places_path.exists():
            for row in read_jsonl(places_path):
                cid = str(row.get("contentid", "")).strip()
                if cid:
                    done_ids.add(cid)
    else:
        write_jsonl(places_path, [], append=False)
        write_jsonl(segments_path, [], append=False)

    print(f"[collect:{content_type_id}] total={total}, done={len(done_ids)}, resume={resume}")

    # contentId 단위 즉시 저장
    detail_infos_map: Dict[str, List[Dict[str, Any]]] = {}

    for idx, cid in enumerate(ordered_ids, 1):
        if cid in done_ids:
            continue

        base = id_to_base[cid]

        try:
            common = fetch_detail_common(base_url, service_key, mobile_os, mobile_app, resp_type, cid)
            if throttle_s > 0:
                time.sleep(throttle_s)

            intro = fetch_detail_intro(base_url, service_key, mobile_os, mobile_app, resp_type, cid, content_type_id)
            if throttle_s > 0:
                time.sleep(throttle_s)

            info = fetch_detail_info(base_url, service_key, mobile_os, mobile_app, resp_type, cid, content_type_id)
            if throttle_s > 0:
                time.sleep(throttle_s)

            pet = fetch_detail_pet_tour(base_url, service_key, mobile_os, mobile_app, resp_type, cid)
            if throttle_s > 0:
                time.sleep(throttle_s)

            row = normalize_common_record(base, common, intro)
            row["contentid"] = cid
            row["contenttypeid_code"] = str(content_type_id)
            row["contenttypeid"] = label  # 요청: 숫자 대신 라벨
            if pet:
                row["pet_raw"] = pet

            append_jsonl(places_path, row)

            if content_type_id == 25:
                detail_infos_map[cid] = info

            done_ids.add(cid)
            _save_ck(ck_path, done_ids, idx, total)

            if len(done_ids) % 20 == 0 or idx == total:
                print(f"[collect:{content_type_id}] progress {len(done_ids)}/{total}")

        except Exception as e:
            # 중간 저장은 이미 append됨. 체크포인트 저장 후 중단.
            _save_ck(ck_path, done_ids, idx, total)
            print(f"[ERROR] stop category={content_type_id}, cid={cid}, err={e}")
            raise

    places_all = read_jsonl(places_path)

    # 여행코스 세그먼트 파일 갱신
    seg_rows: List[Dict[str, Any]] = []
    if content_type_id == 25:
        place_index = {
            str(r.get("contentid", "")).strip(): r
            for r in places_all
            if str(r.get("contentid", "")).strip()
        }
        seg_rows = build_course_segments(places_all, detail_infos_map, place_index)
        write_jsonl(segments_path, seg_rows, append=False)

    print(f"✅ DONE category {content_type_id} ({label}) -> {places_path}")
    return places_all, seg_rows


def collect_multi_categories_into_one_file(
    base_url: str,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    resp_type: str,
    outdir: Path,
    category_map: Dict[int, str],
    area_code: int,
    num_rows: int,
    throttle_s: float,
    resume: bool = True,
) -> Tuple[Path, Path]:
    ensure_dir(outdir)

    all_places: List[Dict[str, Any]] = []
    all_segments: List[Dict[str, Any]] = []

    for ctid, label in category_map.items():
        print(f"\n===== START {ctid} {label} =====")
        places_rows, seg_rows = _collect_single_category_resume(
            base_url=base_url,
            service_key=service_key,
            mobile_os=mobile_os,
            mobile_app=mobile_app,
            resp_type=resp_type,
            outdir=outdir,
            content_type_id=ctid,
            label=label,
            area_code=area_code,
            num_rows=num_rows,
            throttle_s=throttle_s,
            resume=resume,
        )
        all_places.extend(places_rows)
        all_segments.extend(seg_rows)
        print(f"===== END {ctid} {label} =====\n")

    places_out = outdir / "places_contentType12_39_all.jsonl"
    seg_out = outdir / "course_segments_contentType12_39_all.jsonl"

    write_jsonl(places_out, all_places, append=False)
    write_jsonl(seg_out, all_segments, append=False)

    print("✅ DONE ALL")
    print(f" - places(all): {places_out} rows={len(all_places)}")
    print(f" - segments(all): {seg_out} rows={len(all_segments)}")

    return places_out, seg_out
