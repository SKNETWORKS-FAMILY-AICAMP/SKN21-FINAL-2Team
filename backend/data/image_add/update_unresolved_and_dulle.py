#!/usr/bin/env python3
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

TARGET = Path("backend/data/image_add/12_관광지_image_add.jsonl")
UNRESOLVED = Path("backend/data/image_add/12_관광지_image_add_addr_unresolved_list.jsonl")
SRC_TOUR = Path("backend/data/12_관광지.jsonl")
SRC_LEPORTS = Path("backend/data/28_레포츠.jsonl")
BACKUP = Path("backend/data/image_add/12_관광지_image_add.backup_before_unresolved_and_dulle_update.jsonl")
RESULTS = Path("backend/data/image_add/12_관광지_image_add_unresolved_and_dulle_update_results.jsonl")

KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def load_jsonl(path: Path) -> Tuple[List[str], List[dict]]:
    comments: List[str] = []
    rows: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            comments.append(line)
            continue
        try:
            rows.append(json.loads(s))
        except json.JSONDecodeError:
            continue
    return comments, rows


def load_map(path: Path) -> Dict[str, dict]:
    return {str(row.get("contentid", "")).strip(): row for _, rows in [load_jsonl(path)] for row in rows if str(row.get("contentid", "")).strip()}


def get_kakao_key() -> str:
    key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if key:
        return key
    env_file = Path("backend/.env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("KAKAO_REST_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def clean_addr_for_geocode(addr: str) -> List[str]:
    base = normalize(addr)
    variants = [base]

    # Drop route-section notes in parentheses.
    variants.append(re.sub(r"\s*\([^)]*~[^)]*\)", "", base).strip())
    # Keep only the address portion before a route description after a right paren.
    variants.append(re.sub(r"(\([^)]*\)).*$", r"\1", base).strip())
    # Remove all parenthetical text.
    variants.append(re.sub(r"\s*\([^)]*\)", "", base).strip())
    # Remove trailing station/segment description after two or more spaces.
    variants.append(re.split(r"\s{2,}|\t+", base)[0].strip())

    seen = []
    for item in variants:
        item = normalize(item)
        if item and item not in seen:
            seen.append(item)
    return seen


def geocode_addr(session: requests.Session, headers: dict, addr: str) -> Tuple[str, str]:
    for query in clean_addr_for_geocode(addr):
        try:
            resp = session.get(
                KAKAO_ADDRESS_URL,
                headers=headers,
                params={"query": query, "analyze_type": "similar", "size": 5},
                timeout=10,
            )
            if not resp.ok:
                time.sleep(0.02)
                continue
            docs = resp.json().get("documents") or []
            if docs:
                x = str(docs[0].get("x", "")).strip()
                y = str(docs[0].get("y", "")).strip()
                if x and y:
                    return x, y
        except Exception:
            pass
        time.sleep(0.02)
    return "", ""


def first_22_unresolved_rows() -> List[dict]:
    rows: List[dict] = []
    for line in UNRESOLVED.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("{"):
            rows.append(json.loads(s))
        if len(rows) == 22:
            break
    return rows


def route_specs() -> List[dict]:
    return [
        {
            "contentid": "1964911",
            "title": "[서울둘레길 1코스] 수락산코스",
            "ch_title": "서울둘레길1코스(수락산)",
            "addr": "서울특별시 도봉구 도봉로 948 (도봉동)",
            "source_file": "28",
        },
        {
            "contentid": "1964912",
            "title": "[서울둘레길 2코스] 덕릉고개코스",
            "ch_title": "서울둘레길2코스(덕릉고개)",
            "addr": "서울특별시 노원구 상계동 산152-1",
            "source_file": "28",
        },
        {
            "contentid": "3526326",
            "title": "[서울둘레길 3코스] 불암산코스",
            "ch_title": "서울둘레길3코스(불암산)",
            "addr": "서울 노원구 중계동 산112",
            "source_file": "12",
        },
        {
            "contentid": "1964918",
            "title": "[서울둘레길 4코스] 망우·용마산코스",
            "ch_title": "서울둘레길4코스(망우용마산)",
            "addr": "서울특별시 노원구 화랑로 지하510 (공릉동)",
            "source_file": "28",
        },
        {
            "contentid": "1964922",
            "title": "[서울둘레길 5코스] 아차산코스",
            "ch_title": "서울둘레길5코스(아차산)",
            "addr": "서울특별시 중랑구 면목동",
            "source_file": "28",
        },
        {
            "contentid": "1964914",
            "title": "[서울둘레길 6코스] 고덕산코스",
            "ch_title": "서울둘레길6코스(고덕산)",
            "addr": "서울특별시 광진구 아차산로 지하571 (광장동)",
            "source_file": "28",
        },
        {
            "contentid": "1964932",
            "title": "[서울둘레길 7코스] 일자산코스",
            "ch_title": "서울둘레길7코스(일자산)",
            "addr": "서울특별시 강동구 상일동",
            "source_file": "28",
        },
        {
            "contentid": "1964937",
            "title": "[서울둘레길 8코스] 장지·탄천코스",
            "ch_title": "서울둘레길8코스(장지탄천)",
            "addr": "서울특별시 송파구 방이동",
            "source_file": "28",
        },
        {
            "contentid": "3526328",
            "title": "[서울둘레길 9코스] 대모·구룡산코스",
            "ch_title": "서울둘레길9코스(대모구룡산)",
            "addr": "서울 강남구 광평로 지하 270",
            "source_file": "12",
        },
        {
            "contentid": "3526332",
            "title": "[서울둘레길 10코스] 우면산코스",
            "ch_title": "서울둘레길10코스(우면산)",
            "addr": "서울 서초구 서초동 산150-123",
            "source_file": "12",
        },
        {
            "contentid": "3526339",
            "title": "[서울둘레길 11코스] 관악산코스",
            "ch_title": "서울둘레길11코스(관악산)",
            "addr": "서울 동작구 동작대로 지하 3",
            "source_file": "12",
        },
        {
            "contentid": "3526341",
            "title": "[서울둘레길 12코스] 호암산코스",
            "ch_title": "서울둘레길12코스(호암산)",
            "addr": "서울특별시 금천구 호암로 250",
            "source_file": "12",
        },
        {
            "contentid": "15e3bcd7-bd04-4782-97d3-83823feff222",
            "title": "[서울둘레길 13코스] 안양천 상류코스",
            "ch_title": "서울둘레길13코스(안양천상류)",
            "addr": "경기도 안양시 만안구 경수대로 1431 (석수동)",
            "source_file": "synthetic",
        },
        {
            "contentid": "3526342",
            "title": "[서울둘레길 14코스] 안양천 하류코스",
            "ch_title": "서울둘레길14코스(안양천하류)",
            "addr": "서울 영등포구 양평동 504-1",
            "source_file": "12",
        },
        {
            "contentid": "3526353",
            "title": "[서울둘레길 15코스] 노을·하늘공원코스",
            "ch_title": "서울둘레길15코스(노을하늘공원)",
            "addr": "서울 마포구 상암동 482-49",
            "source_file": "12",
        },
        {
            "contentid": "3526354",
            "title": "[서울둘레길 16코스] 봉산·앵봉산코스",
            "ch_title": "서울둘레길16코스(봉산앵봉산)",
            "addr": "서울 은평구 갈현로15길 27-1 은평의 마을",
            "source_file": "12",
        },
        {
            "contentid": "3526376",
            "title": "[서울둘레길 17코스] 북한산 은평코스",
            "ch_title": "서울둘레길17코스(북한산은평)",
            "addr": "서울 은평구 진관2로 지하 15-25",
            "source_file": "12",
        },
        {
            "contentid": "3526384",
            "title": "[서울둘레길 18코스] 북한산 종로코스",
            "ch_title": "서울둘레길18코스(북한산종로)",
            "addr": "서울 종로구 평창동 575",
            "source_file": "12",
        },
        {
            "contentid": "3526391",
            "title": "[서울둘레길 19코스] 북한산 성북코스",
            "ch_title": "서울둘레길19코스(북한산성북)",
            "addr": "서울 성북구 정릉동 803-13",
            "source_file": "12",
        },
        {
            "contentid": "3526413",
            "title": "[서울둘레길 20코스] 북한산 강북코스",
            "ch_title": "서울둘레길20코스(북한산강북)",
            "addr": "서울 강북구 화계사길 117",
            "source_file": "12",
        },
        {
            "contentid": "3526434",
            "title": "[서울둘레길 21코스] 북한산 도봉코스",
            "ch_title": "서울둘레길21코스(북한산도봉)",
            "addr": "서울 강북구 삼양로 지하 676",
            "source_file": "12",
        },
    ]


def make_record(schema_row: Optional[dict], spec: dict) -> dict:
    record = {
        "contentid": spec["contentid"],
        "title": spec["ch_title"],
        "contenttypeid": "관광지",
        "image": "",
        "usetime": "",
        "restdate": "",
        "parking": "",
        "addr": spec["addr"],
        "mapy": "",
        "mapx": "",
        "tel": "",
        "contenttypeid_code": "12",
        "llm_text": "",
    }
    if schema_row:
        for key in record.keys():
            if key in schema_row and key != "title":
                record[key] = schema_row.get(key, record[key])
    if spec["source_file"] == "28":
        record["contenttypeid"] = "레포츠"
        record["contenttypeid_code"] = "28"
    record["title"] = spec["ch_title"]
    record["addr"] = spec["addr"]
    record["llm_text"] = ""
    return record


def main() -> None:
    if not BACKUP.exists():
        shutil.copy2(TARGET, BACKUP)

    key = get_kakao_key()
    if not key:
        raise SystemExit("KAKAO_REST_API_KEY not found")

    headers = {"Authorization": f"KakaoAK {key}"}
    session = requests.Session()

    comments, target_rows = load_jsonl(TARGET)
    target_by_id = {str(row.get("contentid", "")).strip(): row for row in target_rows}

    src_tour = load_map(SRC_TOUR)
    src_leports = load_map(SRC_LEPORTS)

    results: List[dict] = []

    # 1-2. Apply first 22 unresolved addresses and refresh coordinates.
    for row in first_22_unresolved_rows():
        cid = str(row.get("contentid", "")).strip()
        title = str(row.get("title", "")).strip()
        addr = str(row.get("addr", "")).strip()
        x, y = geocode_addr(session, headers, addr)
        target = target_by_id.get(cid)
        if target and str(target.get("title", "")).strip() == title:
            target["addr"] = addr
            if x and y:
                target["mapx"] = x
                target["mapy"] = y
            results.append(
                {
                    "phase": "first_22_addr_apply",
                    "contentid": cid,
                    "title": title,
                    "addr": addr,
                    "mapx": x,
                    "mapy": y,
                    "status": "updated" if x and y else "addr_updated_coord_missing",
                }
            )
        else:
            results.append(
                {
                    "phase": "first_22_addr_apply",
                    "contentid": cid,
                    "title": title,
                    "addr": addr,
                    "mapx": x,
                    "mapy": y,
                    "status": "target_not_found_or_title_mismatch",
                }
            )

    # 3-6. Apply dulle-gil rows.
    existing_ids = {str(row.get("contentid", "")).strip() for row in target_rows}
    appended_rows: List[dict] = []

    for spec in route_specs():
        cid = spec["contentid"]
        if spec["source_file"] == "28":
            source_row = src_leports.get(cid)
        elif spec["source_file"] == "12":
            source_row = src_tour.get(cid) or target_by_id.get(cid)
        else:
            source_row = None

        record = make_record(source_row, spec)
        x, y = geocode_addr(session, headers, record["addr"])
        if x and y:
            record["mapx"] = x
            record["mapy"] = y

        if cid in target_by_id:
            target_by_id[cid].update(record)
            status = "updated_existing"
        else:
            appended_rows.append(record)
            status = "appended_new"

        results.append(
            {
                "phase": "dulle_apply",
                "contentid": cid,
                "title": record["title"],
                "addr": record["addr"],
                "mapx": record["mapx"],
                "mapy": record["mapy"],
                "status": status,
            }
        )

    if appended_rows:
        target_rows.extend(appended_rows)

    lines = comments + [json.dumps(row, ensure_ascii=False) for row in target_rows]
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    RESULTS.write_text(
        ("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n") if results else "",
        encoding="utf-8",
    )

    print("target", TARGET)
    print("results", RESULTS)
    print("total_rows_after", len(target_rows))
    print("new_rows", len(appended_rows))
    print("first_22_processed", 22)
    print("dulle_processed", len(route_specs()))


if __name__ == "__main__":
    main()
