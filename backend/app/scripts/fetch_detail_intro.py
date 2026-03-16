"""
visitkorea_only detailIntro2 수집 스크립트
==========================================
enriched JSON에서 contentid를 읽어 detailIntro2 원본 통째 저장.

입력: data/add(image,info)/visitkorea_only/visitkorea_only_{카테고리}_enriched.json
출력: data/add(image,info)/visitkorea_only/visitkorea_only_{카테고리}_intro_raw.jsonl

사용법:
  cd backend
  PYTHONPATH=. python -u app/scripts/fetch_detail_intro.py
"""

import json, os, time, sys
import requests
from pathlib import Path


def _load_env():
    """dotenv 없이 .env 파일 직접 파싱"""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()


_load_env()
TOURAPI_KEY = os.getenv("TOURAPI_KEY", "").strip()
BASE = "https://apis.data.go.kr/B551011/KorService2"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "add(image,info)" / "visitkorea_only"

# contenttypeid 매핑 (한글→코드)
CT_MAP = {
    "관광지": "12",
    "음식점": "39",
    "숙박": "32",
}

CATEGORIES = ["관광지", "음식점", "숙박"]
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


def fetch_detail_intro(content_id: str, content_type_id: str) :
    """detailIntro2 호출 → 응답 원본 그대로 반환"""
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
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if items:
            return items[0]
    except Exception as e:
        print(f"  [ERROR] detailIntro2 실패: {e}", flush=True)
    return None


def process_category(cat_name: str):
    ct_code = CT_MAP[cat_name]
    in_file = DATA_DIR / f"visitkorea_only_{cat_name}_enriched.json"
    out_file = DATA_DIR / f"visitkorea_only_{cat_name}_intro_raw.jsonl"

    if not in_file.exists():
        print(f"[SKIP] {in_file} 없음", flush=True)
        return

    with open(in_file, encoding="utf-8") as f:
        items = json.load(f)

    total = len(items)
    print(f"\n{'='*50}", flush=True)
    print(f"{cat_name}: {total}건 detailIntro2 수집 (contentTypeId={ct_code})", flush=True)
    print(f"{'='*50}", flush=True)

    # 이어하기: 이미 저장된 contentid
    done_cids = set()
    if out_file.exists():
        with open(out_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("detail_intro"):
                    done_cids.add(str(d.get("contentid", "")))

    if done_cids:
        print(f"이미 처리 완료: {len(done_cids)}건, 이어서 진행", flush=True)

    success = len(done_cids)
    fail = 0

    with open(out_file, "a" if done_cids else "w", encoding="utf-8") as fout:
        for i, item in enumerate(items):
            cid = str(item.get("contentid", ""))
            title = item.get("title", "").strip()

            if cid in done_cids:
                continue

            print(f"[{i+1}/{total}] {title} (cid={cid})", flush=True)

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
                fields = len(intro)
                print(f"  → 저장 (필드 {fields}개)", flush=True)
                success += 1
            else:
                print(f"  → detailIntro2 결과 없음", flush=True)
                fail += 1

    print(f"\n{cat_name} 완료: 성공 {success}건 / 실패 {fail}건", flush=True)


def main():
    if not TOURAPI_KEY:
        print("[ERROR] TOURAPI_KEY 없음. .env에 설정하세요.", flush=True)
        return

    # 먼저 1건 테스트
    print("=== detailIntro2 테스트 호출 ===", flush=True)
    test = fetch_detail_intro("2611482", "12")
    if test:
        print(f"테스트 성공: {len(test)}개 필드", flush=True)
        print(f"필드 목록: {list(test.keys())}", flush=True)
    else:
        print("[ERROR] 테스트 호출 실패. API 키를 확인하세요.", flush=True)
        return

    for cat_name in CATEGORIES:
        process_category(cat_name)

    print("\n\n=== 전체 완료 ===", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
