"""
Step 2: detailIntro2로 장소별 상세 정보 수집
=============================================
enriched JSON에서 contentid를 읽어 detailIntro2 API를 호출하고
카테고리별 _intro_raw.jsonl에 저장한다.

- category_depth로 실제 contentTypeId를 추론 (cat2 → ctid)
- 이미 preprocessed에 있는 항목은 건너뜀 (--skip-preprocessed)
- 이어하기 지원 (성공건만 유지, 실패건 재시도)

입력: data/add(image,info)/visitkorea_only/visitkorea_only_{카테고리}_enriched.json
출력: data/add(image,info)/visitkorea_only/visitkorea_only_{카테고리}_intro_raw.jsonl

사용법:
  cd backend
  PYTHONPATH=. python -u data/scripts/visitkorea/step2_fetch_details.py
  PYTHONPATH=. python -u data/scripts/visitkorea/step2_fetch_details.py --skip-preprocessed
  PYTHONPATH=. python -u data/scripts/visitkorea/step2_fetch_details.py --categories 음식점
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw):
        return False

load_dotenv(override=True)

TOURAPI_KEY = os.getenv("TOURAPI_KEY", "").strip()
BASE = "https://apis.data.go.kr/B551011/KorService2"
DATA_DIR = Path(__file__).resolve().parents[2] / "add(image,info)" / "visitkorea_only"
PREPROCESSED_DIR = Path(__file__).resolve().parents[2] / "preprocessed"

CATEGORIES = ["관광지", "음식점", "숙박"]

# category_depth 두 번째 레벨 → contentTypeId
CAT2_TO_CTID = {
    "문화시설": "14",
    "레포츠소개": "28",
    "육상 레포츠": "28",
    "수상 레포츠": "28",
    "항공 레포츠": "28",
    "복합 레포츠": "28",
    "음식점": "39",
    "숙박시설": "32",
    "쇼핑": "38",
    "축제": "15",
    "공연/행사": "15",
    "가족코스": "25",
    "나홀로코스": "25",
    "힐링코스": "25",
    "도보코스": "25",
    "캠핑코스": "25",
    "맛코스": "25",
    "체험관광지": "12",
    "역사관광지": "12",
    "자연관광지": "12",
    "관광자원": "12",
}

# 파일 카테고리 기본값 (category_depth가 없거나 매핑 안 될 때 fallback)
FILE_DEFAULT_CTID = {
    "관광지": "12",
    "음식점": "39",
    "숙박": "32",
}

THROTTLE = 0.15


def _resolve_ctid(item: dict, file_cat: str) -> str:
    """enriched item의 category_depth에서 실제 contentTypeId를 추론"""
    cd = item.get("category_depth") or ""
    if cd and cd != "None":
        parts = [p.strip() for p in cd.split(" > ")]
        if len(parts) >= 2:
            cat2_name = parts[1]
            if cat2_name in CAT2_TO_CTID:
                return CAT2_TO_CTID[cat2_name]
    return FILE_DEFAULT_CTID.get(file_cat, "12")


def _api_get(url, params, retries=3):
    for attempt in range(retries):
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 429:
            wait = 2 ** (attempt + 1)
            print(f"  [WARN] 429, {wait}초 대기...", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()


def fetch_detail_intro(content_id: str, content_type_id: str) -> dict | None:
    """detailIntro2 호출 → 응답 원본 반환"""
    params = {
        "serviceKey": TOURAPI_KEY,
        "MobileOS": "ETC",
        "MobileApp": "polarisK",
        "_type": "json",
        "contentId": content_id,
        "contentTypeId": content_type_id,
    }
    try:
        data = _api_get(f"{BASE}/detailIntro2", params)
        items_wrapper = data.get("response", {}).get("body", {}).get("items", "")
        if not items_wrapper or isinstance(items_wrapper, str):
            return None
        item_list = items_wrapper.get("item", [])
        if item_list:
            return item_list[0] if isinstance(item_list, list) else item_list
    except Exception as e:
        print(f"  [ERROR] detailIntro2 실패: {e}", flush=True)
    return None


def _load_preprocessed_ids(cat_name: str) -> set[str]:
    """preprocessed 파일에서 이미 처리된 contentid 집합 반환"""
    preprocessed_file = PREPROCESSED_DIR / f"visitkorea_{cat_name}.json"
    if not preprocessed_file.exists():
        return set()
    with open(preprocessed_file, encoding="utf-8") as f:
        data = json.load(f)
    return {str(p["contentid"]) for p in data}


def collect_category(cat_name: str, skip_preprocessed: bool = False):
    in_file = DATA_DIR / f"visitkorea_only_{cat_name}_enriched.json"
    out_file = DATA_DIR / f"visitkorea_only_{cat_name}_intro_raw.jsonl"

    if not in_file.exists():
        print(f"[SKIP] {in_file} 없음", flush=True)
        return

    with open(in_file, encoding="utf-8") as f:
        items = json.load(f)

    total = len(items)

    # preprocessed 제외
    if skip_preprocessed:
        prep_ids = _load_preprocessed_ids(cat_name)
        items = [e for e in items if str(e["contentid"]) not in prep_ids]
        print(f"  Preprocessed 제외: {total}건 → {len(items)}건", flush=True)
        total = len(items)

    print(f"\n{'='*50}", flush=True)
    print(f"{cat_name}: {total}건 detailIntro2 수집 (category_depth 기반 contentTypeId)", flush=True)
    print(f"{'='*50}", flush=True)

    # 이어하기: intro가 있는 건만 성공으로 간주
    done_cids = set()
    keep_lines = []
    if out_file.exists():
        with open(out_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    if d.get("detail_intro"):
                        done_cids.add(str(d.get("contentid", "")))
                        keep_lines.append(line.rstrip("\n"))
                except json.JSONDecodeError:
                    continue

    if done_cids:
        # 성공건만 남기고 파일 재작성
        with open(out_file, "w", encoding="utf-8") as f:
            for line in keep_lines:
                f.write(line + "\n")
        print(f"이미 수집 완료: {len(done_cids)}건 (실패건 재시도)", flush=True)

    success = len(done_cids)
    fail = 0

    with open(out_file, "a" if done_cids else "w", encoding="utf-8") as fout:
        for i, item in enumerate(items):
            cid = str(item.get("contentid", ""))
            title = item.get("title", "").strip()

            if cid in done_cids:
                continue

            ct_code = _resolve_ctid(item, cat_name)
            print(f"[{i+1}/{total}] {title} (cid={cid}, ctid={ct_code})", flush=True)

            intro = fetch_detail_intro(cid, ct_code)
            time.sleep(THROTTLE)

            record = {
                "contentid": cid,
                "title": title,
                "detail_intro": intro,
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            fout.flush()

            if intro:
                print(f"  → 저장 (필드 {len(intro)}개)", flush=True)
                success += 1
            else:
                print(f"  → detailIntro2 결과 없음", flush=True)
                fail += 1

    print(f"\n{cat_name} 완료: 성공 {success}건 / 실패 {fail}건", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="detailIntro2 수집")
    parser.add_argument("--categories", nargs="+", default=CATEGORIES,
                        help="처리할 카테고리 (기본: 관광지 음식점 숙박)")
    parser.add_argument("--skip-preprocessed", action="store_true",
                        help="이미 preprocessed에 있는 항목 건너뜀")
    return parser.parse_args()


def main():
    args = parse_args()

    if not TOURAPI_KEY:
        print("[ERROR] TOURAPI_KEY 없음", flush=True)
        return

    # 테스트 호출
    print("=== detailIntro2 테스트 호출 ===", flush=True)
    test = fetch_detail_intro("2611482", "12")
    if test:
        print(f"테스트 성공: {len(test)}개 필드", flush=True)
    else:
        print("[ERROR] 테스트 호출 실패. API 키 확인 필요", flush=True)
        return

    for cat_name in args.categories:
        collect_category(cat_name, skip_preprocessed=args.skip_preprocessed)

    print("\n\n=== 전체 완료 ===", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
