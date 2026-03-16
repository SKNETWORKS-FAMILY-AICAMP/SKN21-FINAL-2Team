"""
Visit Seoul API 실패 CID 재시도 스크립트
=========================================
visitseoul_fetcher.py 실행 후 500 오류로 누락된 CID를 재시도합니다.

사용법:
    python backend/app/scripts/visitseoul_retry.py
"""

import requests
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── 설정 ───────────────────────────────────────────────
BASE_URL = "https://api-call.visitseoul.net"
DEFAULT_HEADERS = {
    "Accept": "application/json;charset=UTF-8",
    "Content-Type": "application/json;charset=UTF-8",
}

# 재시도 시 딜레이를 더 길게 (서버 부하 감소)
RETRY_DELAY = 1.0
MAX_RETRIES = 3

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
OUTPUT_DIR = BACKEND_DIR / "data" / "raw"


def make_session(api_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({**DEFAULT_HEADERS, "VISITSEOUL-API-KEY": api_key})
    return s


def get_content_info(session: requests.Session, cid: str) -> dict | None:
    """상세 정보 조회 (최대 MAX_RETRIES회 재시도)"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(
                f"{BASE_URL}/api/v1/contents/info",
                json={"cid": cid},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                detail = data.get("data", data.get("result", data))
                if isinstance(detail, list) and detail:
                    return detail[0]
                return detail
            else:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)  # 점진적 대기
        except requests.exceptions.RequestException:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        finally:
            time.sleep(RETRY_DELAY)
    return None


def get_all_cids(session: requests.Session) -> set:
    """카테고리별 전체 CID 재수집"""
    print("카테고리 목록 조회 중...")
    resp = session.get(f"{BASE_URL}/api/v1/category/list", timeout=30)
    categories = resp.json().get("data", [])
    cat_codes = [c.get("com_ctgry_sn") for c in categories if c.get("com_ctgry_sn")]
    print(f"  → {len(cat_codes)}개 카테고리")

    all_cids = set()
    for cat in cat_codes:
        page = 1
        while True:
            try:
                r = session.post(
                    f"{BASE_URL}/api/v1/contents/list",
                    json={"page_no": page, "page_size": 100, "lang_code": "ko", "com_ctgry_sn": cat},
                    timeout=30,
                )
                data = r.json()
                items = data.get("data", [])
                if not items:
                    break
                for item in items:
                    cid = item.get("cid")
                    if cid:
                        all_cids.add(cid)
                paging = data.get("paging", {})
                total = paging.get("total_count", 0)
                if len(items) < 100 or len(all_cids) >= total:
                    break
                page += 1
            except Exception:
                break
            finally:
                time.sleep(0.3)
    return all_cids


def main():
    api_key = os.environ.get("VISITSEOUL_API_KEY")
    if not api_key:
        print("오류: VISITSEOUL_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    existing_path = OUTPUT_DIR / "contents_detail_all.json"
    if not existing_path.exists():
        print(f"오류: {existing_path} 파일이 없습니다. 먼저 visitseoul_fetcher.py를 실행하세요.")
        sys.exit(1)

    print("=" * 50)
    print("Visit Seoul 실패 CID 재시도")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 이미 수집된 데이터 로드
    with open(existing_path, encoding="utf-8") as f:
        existing = json.load(f)
    success_cids = {d["cid"] for d in existing if "cid" in d}
    print(f"\n기존 수집본: {len(existing)}건 (CID {len(success_cids)}개)")

    session = make_session(api_key)

    # 전체 CID 재수집
    print("\n전체 CID 재수집 중...")
    all_cids = get_all_cids(session)
    print(f"  → 전체 CID: {len(all_cids)}개")

    # 미수집 CID 추출
    failed_cids = sorted(all_cids - success_cids)
    print(f"  → 재시도 대상: {len(failed_cids)}개")

    if not failed_cids:
        print("\n재시도할 CID가 없습니다. 이미 모두 수집됐어요!")
        return

    # 재시도
    print(f"\n재시도 시작 (딜레이: {RETRY_DELAY}s, 최대 {MAX_RETRIES}회)...")
    recovered = []
    still_failed = []

    for i, cid in enumerate(failed_cids, 1):
        if i % 50 == 0 or i == 1:
            print(f"  진행: {i}/{len(failed_cids)} (복구: {len(recovered)}, 실패: {len(still_failed)})")

        detail = get_content_info(session, cid)
        if detail and isinstance(detail, dict):
            recovered.append(detail)
        else:
            still_failed.append(cid)

    print(f"\n재시도 결과:")
    print(f"  복구 성공: {len(recovered)}건")
    print(f"  여전히 실패: {len(still_failed)}건")

    # 기존 데이터에 복구분 병합
    merged = existing + recovered
    with open(existing_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"\n  [저장] contents_detail_all.json ({len(merged)}건)")

    # 여전히 실패한 CID 기록
    if still_failed:
        failed_path = OUTPUT_DIR / "failed_cids.json"
        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(still_failed, f, ensure_ascii=False, indent=2)
        print(f"  [저장] failed_cids.json ({len(still_failed)}건) — 서버 측 문제로 수집 불가")

    print("\n완료!")


if __name__ == "__main__":
    main()
