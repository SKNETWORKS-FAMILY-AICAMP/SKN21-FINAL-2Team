"""
Visit Seoul API 데이터 수집 스크립트
====================================
비짓서울 API 센터에서 제공하는 모든 관광지 데이터를 수집합니다.

사용법:
    1) .env 파일에 API 키 저장 후 실행:
       VISITSEOUL_API_KEY=your_api_key_here
       python backend/app/scripts/visitseoul_fetcher.py

    2) 환경변수로 직접 지정:
       export VISITSEOUL_API_KEY=your_api_key_here
       python backend/app/scripts/visitseoul_fetcher.py

    3) 커맨드라인 인자:
       python backend/app/scripts/visitseoul_fetcher.py --api-key YOUR_API_KEY
"""

import requests
import json
import time
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# .env 파일 지원 (python-dotenv 설치 시)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv 없으면 os.environ에서 직접 읽음


# ─── 설정 ───────────────────────────────────────────────
BASE_URL = "https://api-call.visitseoul.net"
DEFAULT_HEADERS = {
    "Accept": "application/json;charset=UTF-8",
    "Content-Type": "application/json;charset=UTF-8",
}

# API 호출 간격 (초) — 서버 부하 방지
REQUEST_DELAY = 0.3

# 출력 디렉토리 (backend/data/)
SCRIPT_DIR = Path(__file__).resolve().parent        # backend/app/scripts/
BACKEND_DIR = SCRIPT_DIR.parent.parent              # backend/
OUTPUT_DIR = BACKEND_DIR / "data"


class VisitSeoulAPI:
    """비짓서울 API 클라이언트"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            **DEFAULT_HEADERS,
            "VISITSEOUL-API-KEY": api_key,
        })
        self.stats = {"api_calls": 0, "errors": 0, "items_fetched": 0}

    def _request(self, method: str, endpoint: str, payload: dict = None) -> dict | None:
        """API 요청 공통 메서드"""
        url = f"{BASE_URL}{endpoint}"
        self.stats["api_calls"] += 1

        try:
            if method.upper() == "GET":
                resp = self.session.get(url, timeout=30)
            else:
                resp = self.session.post(url, json=payload or {}, timeout=30)

            resp.raise_for_status()
            data = resp.json()
            return data

        except requests.exceptions.HTTPError as e:
            print(f"  [HTTP 오류] {e.response.status_code} - {endpoint}")
            self.stats["errors"] += 1
            return None
        except requests.exceptions.RequestException as e:
            print(f"  [요청 오류] {e}")
            self.stats["errors"] += 1
            return None
        except json.JSONDecodeError:
            print(f"  [JSON 파싱 오류] {endpoint}")
            self.stats["errors"] += 1
            return None
        finally:
            time.sleep(REQUEST_DELAY)

    # ─── 1. 언어 코드 조회 ───────────────────────────────
    def get_language_codes(self) -> list:
        """사용 가능한 언어 코드 목록 조회"""
        print("\n[1/4] 언어 코드 조회 중...")
        data = self._request("GET", "/api/v1/code/lang")
        if data:
            codes = data.get("data", data.get("result", data))
            if isinstance(codes, list):
                print(f"  → {len(codes)}개 언어 코드 확인")
                return codes
            elif isinstance(codes, dict) and "list" in codes:
                codes = codes["list"]
                print(f"  → {len(codes)}개 언어 코드 확인")
                return codes
        print("  → 언어 코드 조회 실패, 기본값 사용")
        return [
            {"code_id": "ko", "code_nm": "한국어"},
            {"code_id": "en", "code_nm": "English"},
            {"code_id": "ja", "code_nm": "日本語"},
            {"code_id": "zh-CN", "code_nm": "中文(简体)"},
            {"code_id": "zh-TW", "code_nm": "中文(繁體)"},
            {"code_id": "ru", "code_nm": "Русский"},
            {"code_id": "ms", "code_nm": "Bahasa Melayu"},
        ]

    # ─── 2. 카테고리 조회 ────────────────────────────────
    def get_categories(self) -> list:
        """카테고리 코드 목록 조회"""
        print("\n[2/4] 카테고리 코드 조회 중...")

        endpoints = [
            "/api/v1/code/category",
            "/api/v1/code/ctgry",
            "/api/v1/category/list",
        ]

        for ep in endpoints:
            data = self._request("GET", ep)
            if data:
                cats = data.get("data", data.get("result", data))
                if isinstance(cats, list) and len(cats) > 0:
                    print(f"  → {len(cats)}개 카테고리 확인 (endpoint: {ep})")
                    return cats
                elif isinstance(cats, dict) and "list" in cats:
                    cats = cats["list"]
                    print(f"  → {len(cats)}개 카테고리 확인 (endpoint: {ep})")
                    return cats

        for ep in endpoints:
            data = self._request("POST", ep, {})
            if data:
                cats = data.get("data", data.get("result", data))
                if isinstance(cats, list) and len(cats) > 0:
                    print(f"  → {len(cats)}개 카테고리 확인 (POST {ep})")
                    return cats

        print("  → 카테고리 엔드포인트 자동 탐색 실패")
        print("  → 카테고리 없이 전체 목록 조회를 시도합니다.")
        return []

    # ─── 3. 콘텐츠 목록 조회 (페이징) ────────────────────
    def get_contents_list(self, lang_code: str = "ko", category: str = None, page: int = 1, page_size: int = 100) -> dict | None:
        """콘텐츠 목록 조회 (1페이지)"""
        payload = {
            "page": page,
            "page_size": page_size,
            "page_no": page,
            "pageNo": page,
            "pageSize": page_size,
        }

        if lang_code:
            payload["lang_code"] = lang_code
            payload["lang_code_id"] = lang_code

        if category:
            payload["com_ctgry_sn"] = category
            payload["category"] = category

        return self._request("POST", "/api/v1/contents/list", payload)

    def get_all_contents_list(self, lang_code: str = "ko", category: str = None) -> list:
        """콘텐츠 목록 전체 조회 (자동 페이징)"""
        all_items = []
        page = 1
        page_size = 100

        while True:
            data = self.get_contents_list(lang_code, category, page, page_size)
            if not data:
                break

            items = self._extract_list(data)
            if not items:
                break

            all_items.extend(items)
            print(f"    페이지 {page}: {len(items)}건 (누적 {len(all_items)}건)")

            total = self._extract_total(data)
            if total and len(all_items) >= total:
                break
            if len(items) < page_size:
                break

            page += 1
            if page > 500:
                print("    [경고] 500페이지 초과, 중단합니다.")
                break

        return all_items

    # ─── 4. 콘텐츠 상세 정보 조회 ────────────────────────
    def get_content_info(self, cid: str) -> dict | None:
        """단일 콘텐츠 상세 정보 조회"""
        payload = {"cid": cid}
        data = self._request("POST", "/api/v1/contents/info", payload)
        if data:
            # 상세 데이터 추출 (응답 구조에 따라)
            detail = data.get("data", data.get("result", data))
            if isinstance(detail, list) and len(detail) > 0:
                return detail[0]
            return detail
        return None

    # ─── 유틸리티 ────────────────────────────────────────
    @staticmethod
    def _extract_list(data: dict) -> list:
        """응답에서 리스트 추출 (다양한 JSON 구조 대응)"""
        if isinstance(data, list):
            return data
        for key in ["data", "result", "list", "contents", "items"]:
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for sub_key in ["list", "items", "contents"]:
                    sub_val = val.get(sub_key)
                    if isinstance(sub_val, list):
                        return sub_val
        return []

    @staticmethod
    def _extract_total(data: dict) -> int | None:
        """응답에서 총 건수 추출"""
        for key in ["total", "totalCount", "total_count", "totalCnt", "total_cnt"]:
            if key in data:
                try:
                    return int(data[key])
                except (ValueError, TypeError):
                    pass
            for parent in ["data", "result", "meta", "page", "paging"]:
                if isinstance(data.get(parent), dict) and key in data[parent]:
                    try:
                        return int(data[parent][key])
                    except (ValueError, TypeError):
                        pass
        return None


def fetch_all_data(api_key: str, output_dir: Path, lang_codes_filter: list = None):
    """메인 수집 로직 — 목록 + 상세를 병합하여 최종 데이터 생성"""
    client = VisitSeoulAPI(api_key)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ─── Step 1: 언어 코드 조회 ──────────────────────────
    lang_codes = client.get_language_codes()
    save_json(output_dir / "language_codes.json", lang_codes)

    # ─── Step 2: 카테고리 조회 ───────────────────────────
    categories = client.get_categories()
    save_json(output_dir / "categories.json", categories)

    # 사용할 언어 결정
    if lang_codes_filter:
        use_langs = lang_codes_filter
    else:
        use_langs = []
        for lc in lang_codes:
            if isinstance(lc, dict):
                code = lc.get("code_id") or lc.get("lang_code") or lc.get("code") or lc.get("id")
                if code:
                    use_langs.append(code)
            elif isinstance(lc, str):
                use_langs.append(lc)
        if not use_langs:
            use_langs = ["ko"]

    print(f"\n사용할 언어: {use_langs}")

    # 카테고리 코드 추출
    cat_codes = []
    for cat in categories:
        if isinstance(cat, dict):
            code = cat.get("com_ctgry_sn") or cat.get("category_id") or cat.get("code") or cat.get("id")
            if code:
                cat_codes.append(code)
        elif isinstance(cat, str):
            cat_codes.append(cat)

    # ─── Step 3: 콘텐츠 목록 전체 수집 ──────────────────
    print("\n[3/4] 콘텐츠 목록 수집 중...")

    all_contents = {}  # {lang_code: [items]}
    all_cids = set()

    for lang in use_langs:
        print(f"\n  === 언어: {lang} ===")

        if cat_codes:
            lang_items = []
            for cat in cat_codes:
                print(f"  카테고리: {cat}")
                items = client.get_all_contents_list(lang_code=lang, category=cat)
                lang_items.extend(items)
        else:
            lang_items = client.get_all_contents_list(lang_code=lang)

        all_contents[lang] = lang_items
        print(f"  → {lang} 총 {len(lang_items)}건 수집")

        for item in lang_items:
            if isinstance(item, dict):
                cid = item.get("cid") or item.get("content_id") or item.get("id")
                if cid:
                    all_cids.add(cid)

        save_json(output_dir / f"contents_list_{lang}.json", lang_items)

    print(f"\n  총 고유 CID: {len(all_cids)}개")

    # ─── Step 4: 상세 정보 수집 + 목록에 병합 ────────────
    print(f"\n[4/4] 콘텐츠 상세 정보 수집 + 병합 중... ({len(all_cids)}건)")

    # CID → 상세정보 매핑 딕셔너리
    detail_map = {}
    cid_list = sorted(all_cids)

    for i, cid in enumerate(cid_list, 1):
        if i % 50 == 0 or i == 1:
            print(f"  진행: {i}/{len(cid_list)}")

        detail = client.get_content_info(cid)
        if detail and isinstance(detail, dict):
            detail_map[cid] = detail
            client.stats["items_fetched"] += 1

        # 100건마다 중간 저장
        if i % 100 == 0:
            save_json(
                output_dir / f"contents_detail_partial_{i}.json",
                list(detail_map.values())[-100:]
            )

    # 상세 정보만 별도 저장
    save_json(output_dir / "contents_detail_all.json", list(detail_map.values()))
    print(f"  → 상세 정보 {len(detail_map)}건 수집 완료")

    # ─── 병합: 목록 항목 + 상세 정보 → 최종 통합 데이터 ──
    print("\n[병합] 목록 + 상세 정보 통합 중...")

    for lang, items in all_contents.items():
        merged = []
        for item in items:
            if not isinstance(item, dict):
                merged.append(item)
                continue

            cid = item.get("cid") or item.get("content_id") or item.get("id")
            if cid and cid in detail_map:
                # 목록 데이터를 기본으로, 상세 데이터를 덮어쓰기 병합
                merged_item = {**item, **detail_map[cid]}
                # 원본 목록의 키도 보존 (상세에 없는 필드)
                for k, v in item.items():
                    if k not in merged_item or merged_item[k] is None:
                        merged_item[k] = v
                merged.append(merged_item)
            else:
                merged.append(item)

        save_json(output_dir / f"contents_merged_{lang}.json", merged)
        print(f"  → {lang}: {len(merged)}건 병합 완료")

    # ─── 통계 출력 ───────────────────────────────────────
    print("\n" + "=" * 50)
    print("수집 완료!")
    print(f"  API 호출 횟수: {client.stats['api_calls']}")
    print(f"  오류 횟수: {client.stats['errors']}")
    print(f"  수집 항목 수: {client.stats['items_fetched']}")
    print(f"  저장 위치: {output_dir.resolve()}")
    print("=" * 50)
    print("\n저장된 파일:")
    print("  - language_codes.json       : 언어 코드")
    print("  - categories.json           : 카테고리 코드")
    print("  - contents_list_{lang}.json : 목록 원본 (언어별)")
    print("  - contents_detail_all.json  : 상세 정보 전체")
    print("  - contents_merged_{lang}.json : ★ 목록+상세 병합 최종본")
    print("  - fetch_summary.json        : 수집 요약")

    summary = {
        "timestamp": timestamp,
        "stats": client.stats,
        "languages_used": use_langs,
        "categories_found": len(cat_codes),
        "unique_cids": len(all_cids),
        "details_fetched": len(detail_map),
        "contents_per_lang": {lang: len(items) for lang, items in all_contents.items()},
    }
    save_json(output_dir / "fetch_summary.json", summary)

    return summary


def save_json(filepath: Path, data):
    """JSON 파일 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [저장] {filepath.name}")


def main():
    parser = argparse.ArgumentParser(
        description="비짓서울 API 관광지 데이터 전체 수집기"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("VISITSEOUL_API_KEY"),
        help="비짓서울 API 키 (미지정 시 환경변수 VISITSEOUL_API_KEY 사용)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="출력 디렉토리 (기본: backend/data/)",
    )
    parser.add_argument(
        "--langs",
        nargs="*",
        default=None,
        help="수집할 언어 코드 (예: ko en ja). 미지정시 전체 언어",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="API 호출 간격(초) (기본: 0.3)",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("오류: API 키를 찾을 수 없습니다.")
        print()
        print("다음 중 하나의 방법으로 API 키를 설정하세요:")
        print("  1) .env 파일에 VISITSEOUL_API_KEY=your_key 저장")
        print("  2) export VISITSEOUL_API_KEY=your_key")
        print("  3) python visitseoul_fetcher.py --api-key your_key")
        sys.exit(1)

    global REQUEST_DELAY
    REQUEST_DELAY = args.delay

    print("=" * 50)
    print("비짓서울 API 관광지 데이터 수집기")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API 키: {args.api_key[:8]}...{args.api_key[-4:]}")
    print("=" * 50)

    output_dir = Path(args.output_dir)
    fetch_all_data(args.api_key, output_dir, args.langs)


if __name__ == "__main__":
    main()
