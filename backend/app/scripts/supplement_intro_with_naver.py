"""
detailIntro2 실패(null) 항목을 네이버 지역검색 API로 보완하는 스크립트.
네이버 검색 결과에서 카테고리, 전화번호 등을 가져와 detail_intro 형식으로 변환 후 저장.

사용법:
  cd backend
  PYTHONPATH=. python -u app/scripts/supplement_intro_with_naver.py
"""

import json, os, sys, time
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 내 NaverPlaceChecker 재사용
from app.scripts.check_places_with_naver import (
    NaverPlaceChecker,
    load_env_candidates,
    strip_html,
    normalize_space,
)

load_dotenv(override=True)
load_env_candidates()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "add(image,info)" / "visitkorea_only"
PREPROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "preprocessed"


def load_null_intro_items() -> list[dict]:
    """intro_raw에서 detail_intro가 null인 항목의 contentid 목록 추출"""
    intro_file = DATA_DIR / "visitkorea_only_음식점_intro_raw.jsonl"
    null_items = []
    with open(intro_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if item.get("detail_intro") is None:
                    null_items.append(item)
            except json.JSONDecodeError:
                continue
    return null_items


def load_enriched_map() -> dict[str, dict]:
    """enriched에서 contentid → item 매핑"""
    enriched_file = DATA_DIR / "visitkorea_only_음식점_enriched.json"
    with open(enriched_file, encoding="utf-8") as f:
        enriched = json.load(f)
    return {str(e["contentid"]): e for e in enriched}


def naver_to_detail_intro(candidate, content_id: str) -> dict:
    """네이버 검색 결과를 detailIntro2 형식으로 변환"""
    intro = {
        "contentid": content_id,
        "contenttypeid": "39",
        "seat": "",
        "kidsfacility": "",
        "firstmenu": "",
        "treatmenu": "",
        "smoking": "",
        "packing": "",
        "infocenterfood": candidate.telephone or "",
        "scalefood": "",
        "parkingfood": "",
        "opendatefood": "",
        "opentimefood": "",
        "restdatefood": "",
        "discountinfofood": "",
        "chkcreditcardfood": "",
        "reservationfood": "",
        "lcnsno": "",
        "_source": "naver_local_search",
        "_naver_title": candidate.title,
        "_naver_category": candidate.category,
        "_naver_address": candidate.best_address,
    }

    # 카테고리에서 음식 종류 추출 (예: "음식점>한식>갈비" → firstmenu 힌트)
    if candidate.category:
        cat_parts = [p.strip() for p in candidate.category.split(">")]
        if len(cat_parts) >= 3:
            intro["firstmenu"] = cat_parts[-1]
        elif len(cat_parts) >= 2:
            intro["firstmenu"] = cat_parts[-1]

    return intro


def main():
    checker = NaverPlaceChecker(timeout=10, sleep_ms=150)
    checker.ensure_credentials()

    null_items = load_null_intro_items()
    enriched_map = load_enriched_map()

    print(f"detail_intro null 항목: {len(null_items)}건", flush=True)

    # 기존 intro_raw를 읽어서 null이 아닌 항목은 유지
    intro_file = DATA_DIR / "visitkorea_only_음식점_intro_raw.jsonl"
    keep_lines = []
    null_cids = set()
    with open(intro_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if item.get("detail_intro") is not None:
                    keep_lines.append(line.rstrip("\n"))
                else:
                    null_cids.add(str(item["contentid"]))
            except json.JSONDecodeError:
                continue

    print(f"기존 성공건 유지: {len(keep_lines)}건", flush=True)
    print(f"네이버 검색 대상: {len(null_cids)}건", flush=True)

    # 네이버 검색으로 보완
    success = 0
    fail = 0
    new_lines = []

    for i, null_item in enumerate(null_items):
        cid = str(null_item["contentid"])
        title = null_item.get("title", "")

        # enriched에서 주소 등 추가 정보 가져오기
        enriched = enriched_map.get(cid, {})
        search_item = {
            "title": title,
            "addr": enriched.get("addr", ""),
            "tel": enriched.get("tel", ""),
            "mapx": enriched.get("mapx", ""),
            "mapy": enriched.get("mapy", ""),
        }

        print(f"[{i+1}/{len(null_items)}] {title} (cid={cid})", flush=True)

        try:
            result = checker.check_item(search_item)
        except Exception as e:
            print(f"  [ERROR] 네이버 검색 실패: {e}", flush=True)
            fail += 1
            record = {"contentid": cid, "title": title, "detail_intro": None}
            new_lines.append(json.dumps(record, ensure_ascii=False))
            continue

        if result.candidate and result.status in ("open", "review_needed"):
            intro = naver_to_detail_intro(result.candidate, cid)
            record = {"contentid": cid, "title": title, "detail_intro": intro}
            print(f"  → 네이버 매칭 성공 ({result.status}, score={result.score:.2f}): {result.candidate.title}", flush=True)
            print(f"    카테고리: {result.candidate.category}, 전화: {result.candidate.telephone}", flush=True)
            success += 1
        else:
            record = {"contentid": cid, "title": title, "detail_intro": None}
            print(f"  → 매칭 실패 ({result.status}, score={result.score:.2f})", flush=True)
            fail += 1

        new_lines.append(json.dumps(record, ensure_ascii=False))

    # 파일 재작성: 기존 성공건 + 새 결과
    with open(intro_file, "w", encoding="utf-8") as f:
        for line in keep_lines:
            f.write(line + "\n")
        for line in new_lines:
            f.write(line + "\n")

    print(f"\n{'='*50}", flush=True)
    print(f"완료: 네이버 매칭 성공 {success}건 / 실패 {fail}건", flush=True)
    print(f"intro_raw 총 건수: {len(keep_lines) + len(new_lines)}건", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
