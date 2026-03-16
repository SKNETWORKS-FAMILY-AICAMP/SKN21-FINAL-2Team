"""
visitkorea_only 데이터에 대해 detailCommon2 원본을 통째로 저장하는 스크립트.
변환은 별도 스크립트(transform_visitkorea_only.py)에서 수행.

사용법:
  PYTHONPATH=. python -u app/scripts/enrich_visitkorea_only.py
"""

import json, os, time, sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)
TOURAPI_KEY = os.getenv("TOURAPI_KEY", "").strip()
BASE = "https://apis.data.go.kr/B551011/KorService2"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "add(image,info)" / "visitkorea_only"

CATEGORIES = {
    "관광지": "12",
    "음식점": "39",
    "숙박": "32",
}

THROTTLE = 0.15


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


def fetch_detail_common(content_id: str, content_type_id: str) -> dict | None:
    """detailCommon2 호출 → 응답 원본 그대로 반환"""
    params = {
        "serviceKey": TOURAPI_KEY,
        "MobileOS": "ETC",
        "MobileApp": "polarisK",
        "_type": "json",
        "contentId": content_id,
    }
    try:
        data = _api_get(f"{BASE}/detailCommon2", params)
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if items:
            return items[0]
    except Exception as e:
        print(f"  [ERROR] detailCommon2 실패: {e}", flush=True)
    return None


def enrich_category(cat_name: str, ct_code: str):
    in_file = DATA_DIR / f"visitkorea_only_{cat_name}_matched.jsonl"
    out_file = DATA_DIR / f"visitkorea_only_{cat_name}_detail_raw.jsonl"

    if not in_file.exists():
        print(f"[SKIP] {in_file} 없음", flush=True)
        return

    with open(in_file, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]

    total = len(items)
    print(f"\n{'='*50}", flush=True)
    print(f"{cat_name}: {total}건 처리 시작 (contentTypeId={ct_code})", flush=True)
    print(f"{'='*50}", flush=True)

    # 이미 처리된 것 로드 (이어하기용 - detail_common이 있는 것만)
    done_titles = set()
    if out_file.exists():
        with open(out_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("detail_common"):
                    done_titles.add(d.get("title", "").strip())

    if done_titles:
        print(f"이미 처리 완료: {len(done_titles)}건, 이어서 진행", flush=True)

    success = len(done_titles)
    fail = 0

    with open(out_file, "a" if done_titles else "w", encoding="utf-8") as fout:
        for i, item in enumerate(items):
            title = item["title"].strip()

            if title in done_titles:
                continue

            cid = str(item["contentid"])
            print(f"[{i+1}/{total}] {title} (cid={cid})", flush=True)

            detail = fetch_detail_common(cid, ct_code)
            time.sleep(THROTTLE)

            # 원본 item + detailCommon2 응답 통째로 저장
            record = {
                **item,
                "detail_common": detail,  # None이면 null로 저장
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            fout.flush()

            if detail:
                overview_len = len(detail.get("overview", "") or "")
                print(f"  → 저장 (overview {overview_len}자, 필드 {len(detail)}개)", flush=True)
                success += 1
            else:
                print(f"  → detailCommon2 결과 없음 (원본만 저장)", flush=True)
                fail += 1

    print(f"\n{cat_name} 완료: API 성공 {success}건 / 실패 {fail}건", flush=True)


def main():
    if not TOURAPI_KEY:
        print("[ERROR] TOURAPI_KEY 없음", flush=True)
        return

    for cat_name, ct_code in CATEGORIES.items():
        enrich_category(cat_name, ct_code)

    print("\n\n=== 전체 완료 ===", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
