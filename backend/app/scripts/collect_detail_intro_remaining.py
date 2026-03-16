"""
visitkorea_only 음식점: preprocessed에 없는 항목만 detailIntro2 수집
================================================================
1. enriched에서 preprocessed에 있는 contentid 제외 → 대상 목록 생성
2. category_depth로 contenttypeid_code 식별
3. detailIntro2 API 호출
4. 기존 intro_raw.jsonl에 성공건만 유지 + 신규 결과 append

사용법:
  cd backend
  PYTHONPATH=. python -u app/scripts/collect_detail_intro_remaining.py
"""

import json, os, time, sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)
TOURAPI_KEY = os.getenv("TOURAPI_KEY", "").strip()
BASE = "https://apis.data.go.kr/B551011/KorService2"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "add(image,info)" / "visitkorea_only"
PREPROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "preprocessed"

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
FILE_DEFAULT_CTID = "39"  # 음식점 파일이므로

THROTTLE = 0.15


def _resolve_ctid(item: dict) -> str:
    """enriched item의 category_depth에서 실제 contentTypeId를 추론"""
    cd = item.get("category_depth") or ""
    if cd and cd != "None":
        parts = [p.strip() for p in cd.split(" > ")]
        if len(parts) >= 2:
            cat2_name = parts[1]
            if cat2_name in CAT2_TO_CTID:
                return CAT2_TO_CTID[cat2_name]
    return FILE_DEFAULT_CTID


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


def main():
    if not TOURAPI_KEY:
        print("[ERROR] TOURAPI_KEY 없음", flush=True)
        return

    # 1. enriched에서 preprocessed 제외 → 대상 목록
    enriched_file = DATA_DIR / "visitkorea_only_음식점_enriched.json"
    preprocessed_file = PREPROCESSED_DIR / "visitkorea_음식점.json"
    out_file = DATA_DIR / "visitkorea_only_음식점_intro_raw.jsonl"

    with open(enriched_file, encoding="utf-8") as f:
        enriched = json.load(f)
    with open(preprocessed_file, encoding="utf-8") as f:
        preprocessed = json.load(f)

    prep_ids = set(str(p["contentid"]) for p in preprocessed)
    targets = [e for e in enriched if str(e["contentid"]) not in prep_ids]

    print(f"Enriched 전체: {len(enriched)}건", flush=True)
    print(f"Preprocessed (제외): {len(preprocessed)}건", flush=True)
    print(f"호출 대상: {len(targets)}건", flush=True)

    # 2. 기존 intro_raw에서 성공건 로드 (이어하기)
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

    # 기존 파일을 성공건만 남기고 재작성
    with open(out_file, "w", encoding="utf-8") as f:
        for line in keep_lines:
            f.write(line + "\n")

    already_done_in_targets = sum(1 for t in targets if str(t["contentid"]) in done_cids)
    remaining = [t for t in targets if str(t["contentid"]) not in done_cids]

    print(f"기존 intro_raw 성공건 (전체): {len(done_cids)}건", flush=True)
    print(f"대상 중 이미 완료: {already_done_in_targets}건", flush=True)
    print(f"실제 호출 필요: {len(remaining)}건", flush=True)

    # 3. 테스트 호출
    print("\n=== detailIntro2 테스트 호출 ===", flush=True)
    test = fetch_detail_intro("2611482", "12")
    if test:
        print(f"테스트 성공: {len(test)}개 필드", flush=True)
    else:
        print("[ERROR] 테스트 호출 실패. API 키 확인 필요", flush=True)
        return

    # 4. API 호출 및 결과 저장
    success = 0
    fail = 0
    total = len(remaining)

    with open(out_file, "a", encoding="utf-8") as fout:
        for i, item in enumerate(remaining):
            cid = str(item["contentid"])
            title = item.get("title", "")
            ct_code = _resolve_ctid(item)

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

    print(f"\n{'='*50}", flush=True)
    print(f"완료: 성공 {success}건 / 실패 {fail}건", flush=True)
    print(f"intro_raw 총 건수: {len(done_cids) + success + fail}건", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
