"""
팝업스토어 신규 데이터 크롤링 후 VectorDB 추가 스케줄러.

Popply 사이트를 Selenium으로 크롤링하고, 기존 VectorDB에 없는 팝업만
preprocess_popup.py와 동일한 전처리 파이프라인으로 처리한 후 Qdrant에 upsert한다.

파이프라인:
    1단계: 필드 정규화 + 만료 필터 + 안정 contentid 부여 (_popup_content_id 해시)
    2단계: 텍스트 정제           (preprocess_popup.step2_clean)
    3단계: Geocoding             (preprocess_popup.step3_geocode)
    4단계: llm_text 생성         (preprocess_popup.step4_generate_llm_text)
           Naver 웹문서 검색 + 본문 크롤링 + GPT-4o-mini → 기존 데이터와 동일 품질
    5단계: JSONL 저장 후 Qdrant upsert

중복 판단: _popup_identity_key(title, addr, start_date, end_date) 기반 (안정 해시)
           비용이 큰 geocoding / llm_text 생성 이전에 중복을 제거한다.

실행:
    python -m app.scripts.scheduler.sync_new_popup_data
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# 프로젝트 루트를 sys.path에 추가
BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from app.utils.config import PLACES_COLLECTION
from app.scripts.tour_api.__crawl import (
    _normalize_popup_row,
    _popup_identity_key,
    _is_active_or_upcoming,
    _split_period,
    _text,
)
# preprocess_popup의 step 함수들을 직접 재사용 (동일한 전처리 품질 보장)
from app.scripts.preprocess_popup import (
    step2_clean,
    step3_geocode,
    step4_generate_llm_text,
)

# 기존 콘텐츠 데이터와 동일한 규격:
#   period 필드로 통합 ("yyyy-mm-dd ~ yyyy-mm-dd"), start_date/end_date 미저장
CONTENT_FINAL_FIELDS = [
    "contentid", "title", "contenttypeid", "image",
    "usetime", "restdate", "period",
    "parking", "fee", "addr",
    "mapy", "mapx", "contenttypeid_code", "llm_text",
]

logger = logging.getLogger(__name__)

REPORTS_DIR = BACKEND_DIR / "data" / "scheduler_reports"


# ──────────────────────────────────────────────────────────────────────────────
# VectorDB 기존 팝업 조회
# ──────────────────────────────────────────────────────────────────────────────

def _get_existing_popup_identity_keys(client: QdrantClient) -> set[str]:
    """VectorDB places 컬렉션에서 기존 팝업 identity_key 목록을 반환한다.

    팝업은 _build_15_content()를 통해 contenttypeid="콘텐츠"로 저장되므로
    "콘텐츠" 타입을 스캔한다. 축제도 같은 타입이지만
    _popup_identity_key(title, addr, start_date, end_date) 충돌 확률은 무시 가능하다.
    """
    existing_keys: set[str] = set()
    offset = None

    while True:
        pts, next_offset = client.scroll(
            PLACES_COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="contenttypeid", match=MatchValue(value="콘텐츠"))
            ]),
            offset=offset,
            limit=500,
            with_payload=True,
            with_vectors=False,
        )
        for p in pts:
            payload = p.payload or {}
            title = _text(payload.get("title"))
            if not title:
                continue
            # 기존 콘텐츠 데이터는 period 필드로 저장됨 ("yyyy-mm-dd ~ yyyy-mm-dd")
            # _split_period로 start_date/end_date를 추출하여 identity key 계산
            # period 없으면 start_date/end_date 직접 사용 (신규 수집 데이터 호환)
            period = _text(payload.get("period", ""))
            if period:
                start_date, end_date = _split_period(period)
            else:
                start_date = _text(payload.get("start_date", ""))
                end_date = _text(payload.get("end_date", ""))
            key = _popup_identity_key(
                title,
                _text(payload.get("addr")),
                start_date,
                end_date,
            )
            existing_keys.add(key)
        if next_offset is None:
            break
        offset = next_offset

    return existing_keys


# ──────────────────────────────────────────────────────────────────────────────
# 1단계: 필드 정규화
# ──────────────────────────────────────────────────────────────────────────────

def _step1_normalize(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    필드 정규화 + 만료 팝업 필터.

    _normalize_popup_row()를 재사용하여 기존 파이프라인과 동일한 규격으로 변환한다.
      - contenttypeid  = "콘텐츠"  (기존 데이터와 동일, _build_15_content 경로)
      - contenttypeid_code = "15"
      - contentid      = _popup_content_id() 해시 (9xxxxxxxxx, 스케줄러 재실행에도 안정)
    """
    result = []
    for index, item in enumerate(raw_rows, start=1):
        normalized = _normalize_popup_row(item, index)
        # 만료 팝업 제외 (_build_15_content 내 active_rows 필터와 동일)
        if not _is_active_or_upcoming(_text(normalized.get("end_date"))):
            logger.debug("만료 제외: %s (종료: %s)", normalized.get("title"), normalized.get("end_date"))
            continue
        # introduction 보존: _normalize_popup_row가 제거하지만
        # step4_generate_llm_text의 collect_context()에서 Popply 소개 텍스트로 활용됨.
        # FINAL_FIELDS에 포함되지 않으므로 최종 Qdrant payload에는 저장되지 않는다.
        intro = str(item.get("introduction", "")).strip()
        if intro:
            normalized["introduction"] = intro
        # "Unknown"에서 변환된 빈 문자열 필드 제거 (parking, fee)
        for field in ("parking", "fee"):
            if normalized.get(field) == "":
                del normalized[field]
        result.append(normalized)

    logger.info(
        "1단계 정규화: %d건 → %d건 (만료 %d건 제외)",
        len(raw_rows), len(result), len(raw_rows) - len(result),
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Selenium 크롤링
# ──────────────────────────────────────────────────────────────────────────────

def _crawl_with_selenium(headless: bool = True) -> list[dict[str, Any]]:
    """Popply 사이트를 Selenium으로 크롤링하고 raw 데이터 목록을 반환한다."""
    from app.scripts.popply_crawler import PopplyCrawler  # lazy import

    today = date.today()
    date_from = today.strftime("%Y-%m-%d")
    date_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")  # 1년 후 (하드코딩 방지)

    # crawler가 초기화 전에 예외가 나도 finally에서 안전하게 close 처리
    crawler = None
    try:
        crawler = PopplyCrawler(headless=headless)
        links = crawler.get_popup_links(date_from, date_to)
        logger.info("크롤링된 팝업 링크 수: %d", len(links))
        raw_data: list[dict[str, Any]] = []
        for i, link in enumerate(links, 1):
            data = crawler.parse_detail_page(link)
            if data:
                raw_data.append(data)
            if i % 10 == 0:
                logger.info("  파싱 진행: %d/%d", i, len(links))
        return raw_data
    finally:
        if crawler is not None:
            crawler.close()


# ──────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────────────────────────────────────

def run(headless: bool = True) -> dict[str, Any]:
    """
    팝업스토어 신규 데이터 동기화 실행.

    preprocess_popup.py와 동일한 전처리 파이프라인을 적용하여
    기존 데이터와 동일한 품질(Geocoding + llm_text)로 Qdrant에 upsert한다.

    Args:
        headless: Selenium headless 모드 여부.

    Returns:
        실행 결과 요약 딕셔너리.
    """
    logger.info("팝업스토어 신규 데이터 동기화 시작")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=60)

    # ── Step 0: 기존 팝업 identity_key 조회 ──────────────────────────────────
    existing_keys = _get_existing_popup_identity_keys(client)
    logger.info("기존 팝업 identity_key 수: %d", len(existing_keys))

    # ── Step 1: Selenium 크롤링 ───────────────────────────────────────────────
    raw_data = _crawl_with_selenium(headless=headless)
    logger.info("크롤링 완료: %d건", len(raw_data))

    # ── Step 2: 필드 정규화 + 만료 필터 ──────────────────────────────────────
    normalized = _step1_normalize(raw_data)

    # ── Step 3: identity_key 중복 필터 (비용이 큰 단계 이전에 제거) ───────────
    new_rows: list[dict[str, Any]] = []
    skipped = 0
    for row in normalized:
        key = _popup_identity_key(
            _text(row.get("title")),
            _text(row.get("addr")),
            _text(row.get("start_date")),
            _text(row.get("end_date")),
        )
        if key and key in existing_keys:
            skipped += 1
            continue
        new_rows.append(row)

    logger.info("신규 팝업: %d건 (중복 제외 %d건)", len(new_rows), skipped)

    if not new_rows:
        logger.info("신규 팝업 없음, 처리 생략")
        return {
            "crawled": len(raw_data),
            "normalized": len(normalized),
            "skipped_duplicates": skipped,
            "llm_generated": 0,
            "upserted": 0,
        }

    # ── Step 4: 텍스트 정제 (preprocess_popup.step2_clean) ───────────────────
    cleaned = step2_clean(new_rows)

    # ── Step 5: Geocoding (preprocess_popup.step3_geocode) ───────────────────
    geocoded = asyncio.run(step3_geocode(cleaned))

    # ── Step 6: llm_text 생성 (Naver 검색 + GPT-4o-mini) ─────────────────────
    enriched = step4_generate_llm_text(geocoded)

    # ── Step 7: JSONL 저장 (llm_text 없는 항목 제외) ─────────────────────────
    today_str = date.today().isoformat()
    out_path = REPORTS_DIR / f"popup_new_{today_str}.jsonl"
    upsert_rows: list[dict[str, Any]] = []

    for item in enriched:
        if not item.get("llm_text"):
            logger.warning("llm_text 없어 제외: %s", item.get("title"))
            continue

        # start_date / end_date → period 변환 (기존 콘텐츠 데이터와 동일 규격)
        start_date = _text(item.get("start_date", ""))
        end_date = _text(item.get("end_date", ""))
        if start_date and end_date:
            item["period"] = f"{start_date} ~ {end_date}"
        elif start_date:
            item["period"] = f"{start_date} ~ {start_date}"

        record = {k: item[k] for k in CONTENT_FINAL_FIELDS if k in item}
        upsert_rows.append(record)

    with out_path.open("w", encoding="utf-8") as f:
        for row in upsert_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    logger.info("JSONL 저장: %s (%d건)", out_path, len(upsert_rows))

    # ── Step 8: Qdrant upsert ─────────────────────────────────────────────────
    upserted = 0
    if upsert_rows:
        from app.scripts.qdrant_setup import QdrantClientDB  # ML 모델 의존성 lazy import
        db = QdrantClientDB(setup_collections=False)
        db.add_popup_places(str(out_path))
        upserted = len(upsert_rows)
        logger.info("Qdrant upsert 완료: %d건", upserted)

    stats = {
        "crawled": len(raw_data),
        "normalized": len(normalized),
        "skipped_duplicates": skipped,
        "llm_generated": len(upsert_rows),
        "upserted": upserted,
    }
    logger.info("팝업 동기화 완료: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(headless=True)
