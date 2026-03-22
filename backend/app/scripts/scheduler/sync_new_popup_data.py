"""
팝업스토어 신규 데이터 크롤링 후 VectorDB 추가 스케줄러.

Popply 사이트를 Selenium으로 크롤링하고, 기존 VectorDB에 없는 팝업만
경량 정규화 경로로 처리한 후 Qdrant에 upsert한다.

중복 판단: _popup_identity_key(title, addr, start_date, end_date) 기반 (안정 해시)
경량 파이프라인: __crawl.py의 _build_popup_image_add_rows 재사용
                (Naver 웹검색 + OpenAI llm_text 생성 없음)

실행:
    python -m app.scripts.scheduler.sync_new_popup_data
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import date
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
    DEFAULT_POPUP_LLM_CACHE_PATH,
    _build_popup_image_add_rows,
    _popup_identity_key,
    _text,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = BACKEND_DIR / "data" / "scheduler_reports"


def _get_existing_popup_identity_keys(client: QdrantClient) -> set[str]:
    """VectorDB places 컬렉션에서 기존 팝업 identity_key 목록을 반환한다."""
    existing_keys: set[str] = set()
    offset = None

    while True:
        pts, next_offset = client.scroll(
            PLACES_COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="contenttypeid", match=MatchValue(value="팝업스토어"))
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
            key = _popup_identity_key(
                title,
                _text(payload.get("addr")),
                _text(payload.get("start_date")),
                _text(payload.get("end_date")),
            )
            existing_keys.add(key)
        if next_offset is None:
            break
        offset = next_offset

    return existing_keys


def _crawl_with_selenium(headless: bool = True) -> list[dict[str, Any]]:
    """Popply 사이트를 Selenium으로 크롤링하고 raw 데이터 목록을 반환한다."""
    from app.scripts.popply_crawler import PopplyCrawler  # Selenium 의존성을 lazy import

    today = date.today().strftime("%Y-%m-%d")
    crawler = PopplyCrawler(headless=headless)
    try:
        links = crawler.get_popup_links(today, "2026-12-31")
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
        crawler.close()


def run(headless: bool = True) -> dict[str, Any]:
    """
    팝업스토어 신규 데이터 동기화 실행.

    Args:
        headless: Selenium headless 모드 여부.

    Returns:
        실행 결과 요약 딕셔너리.
    """
    logger.info("팝업스토어 신규 데이터 동기화 시작")

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=60)

    # 1. 기존 팝업 identity_key 조회
    existing_keys = _get_existing_popup_identity_keys(client)
    logger.info("기존 팝업 identity_key 수: %d", len(existing_keys))

    # 2. Selenium 크롤링
    raw_data = _crawl_with_selenium(headless=headless)
    logger.info("크롤링 완료: %d건", len(raw_data))

    # 3. 경량 정규화 + 만료 필터 + stable contentid 부여
    #    llm_text는 기존 캐시(DEFAULT_POPUP_LLM_CACHE_PATH) 참조, 없으면 introduction 텍스트
    llm_cache_path = Path(DEFAULT_POPUP_LLM_CACHE_PATH)
    normalized_rows = _build_popup_image_add_rows(raw_data, llm_cache_path)
    logger.info("정규화 후 활성 팝업 수: %d건", len(normalized_rows))

    # 4. identity_key 중복 필터
    new_rows = []
    skipped = 0
    for row in normalized_rows:
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

    # 5. 임시 JSONL 저장 후 upsert
    upserted = 0
    if new_rows:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = REPORTS_DIR / f"popup_new_{date.today().isoformat()}.jsonl"
        with tmp_path.open("w", encoding="utf-8") as f:
            for row in new_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        logger.info("임시 JSONL 저장: %s", tmp_path)

        from app.scripts.qdrant_setup import QdrantClientDB  # ML 모델 의존성 lazy import
        db = QdrantClientDB(setup_collections=False)
        db.add_popup_places(str(tmp_path))
        upserted = len(new_rows)
        logger.info("Qdrant upsert 완료: %d건", upserted)
    else:
        logger.info("신규 팝업 없음, upsert 생략")

    stats = {
        "crawled": len(raw_data),
        "normalized": len(normalized_rows),
        "skipped_duplicates": skipped,
        "upserted": upserted,
    }
    logger.info("팝업 동기화 완료: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(headless=True)
