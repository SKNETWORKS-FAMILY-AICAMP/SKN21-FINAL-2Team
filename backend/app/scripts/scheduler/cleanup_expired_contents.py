"""
만료된 콘텐츠(축제/팝업) VectorDB 정리 스케줄러.

places 컬렉션에서 contenttypeid="콘텐츠" 타입 데이터를 scroll cursor 방식으로
매주 20건씩 순환 검사한다.

period 필드("yyyy-mm-dd ~ yyyy-mm-dd")의 종료일(뒤 날짜)이 오늘 이전이면
places + photos 양 컬렉션에서 동기 삭제한다. (Kakao API 불필요 — 날짜 기반 판단)

실행:
    python -m app.scripts.scheduler.cleanup_expired_contents [--no-dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList

# 프로젝트 루트를 sys.path에 추가
BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from app.utils.config import PLACES_COLLECTION, PHOTOS_COLLECTION

logger = logging.getLogger(__name__)

REPORTS_DIR = BACKEND_DIR / "data" / "scheduler_reports"
STATE_FILE = REPORTS_DIR / "scroll_state_contents.json"

SCROLL_BATCH = 20  # 매주 검사할 콘텐츠 건수


# ---------------------------------------------------------------------------
# period 파싱
# ---------------------------------------------------------------------------

_PERIOD_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})"
)


def _parse_end_date(period: str) -> date | None:
    """
    "yyyy-mm-dd ~ yyyy-mm-dd" 형식에서 종료일(뒤 날짜)을 파싱한다.
    파싱 실패 시 None 반환.
    """
    if not period:
        return None
    m = _PERIOD_RE.search(period)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(2))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Scroll cursor 상태 관리 (cleanup_closed_places와 별도 파일 사용)
# ---------------------------------------------------------------------------

def _load_scroll_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"contents_offset": None}


def _save_scroll_state(contents_offset: Any) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"contents_offset": contents_offset}, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 삭제 로직 (양 컬렉션 동기)
# ---------------------------------------------------------------------------

def _delete_and_sync(
    client: QdrantClient,
    point_id: Any,
    contentid: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    """
    places 컬렉션에서 point를 삭제하고 photos 컬렉션에서 contentid 기준으로 동기 삭제한다.
    dry_run=True이면 삭제 없이 로그만 남긴다.
    """
    deleted_place_ids: list[str] = []
    synced_photo_ids: list[str] = []

    if not dry_run:
        client.delete(PLACES_COLLECTION, points_selector=PointIdsList(points=[point_id]))
        deleted_place_ids.append(str(point_id))

        if contentid:
            photo_pts, _ = client.scroll(
                PHOTOS_COLLECTION,
                scroll_filter=Filter(must=[
                    FieldCondition(key="contentid", match=MatchValue(value=contentid))
                ]),
                with_payload=False,
                with_vectors=False,
            )
            if photo_pts:
                photo_ids = [p.id for p in photo_pts]
                client.delete(PHOTOS_COLLECTION, points_selector=PointIdsList(points=photo_ids))
                synced_photo_ids.extend(str(i) for i in photo_ids)

    return {
        "point_id": str(point_id),
        "contentid": contentid,
        "deleted_place_ids": deleted_place_ids,
        "synced_photo_ids": synced_photo_ids,
        "dry_run": dry_run,
    }


# ---------------------------------------------------------------------------
# 메인 실행 함수
# ---------------------------------------------------------------------------

def run(dry_run: bool = True) -> dict[str, Any]:
    """
    만료된 콘텐츠 정리 실행.

    places 컬렉션에서 contenttypeid="콘텐츠" 타입 20건을 scroll cursor로 순환 조회하고
    period 필드의 종료일이 오늘 이전이면 places + photos에서 동기 삭제한다.

    Args:
        dry_run: True이면 삭제 없이 리포트만 생성 (초기 운영 시 사용).

    Returns:
        실행 결과 요약 딕셔너리.
    """
    logger.info("만료 콘텐츠 정리 시작 (dry_run=%s)", dry_run)

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=60)

    today = date.today()

    # scroll cursor 로드
    state = _load_scroll_state()
    contents_offset = state.get("contents_offset")

    # contenttypeid="콘텐츠" 에서 20건 scroll
    pts, next_offset = client.scroll(
        PLACES_COLLECTION,
        scroll_filter=Filter(must=[
            FieldCondition(key="contenttypeid", match=MatchValue(value="콘텐츠"))
        ]),
        offset=contents_offset,
        limit=SCROLL_BATCH,
        with_payload=True,
        with_vectors=False,
    )

    # cursor 저장 (None이면 다음 실행 시 처음부터 순환)
    _save_scroll_state(next_offset)
    logger.info(
        "Scroll: 콘텐츠 %d건 조회 (next_offset=%s)",
        len(pts), next_offset,
    )

    results: list[dict[str, Any]] = []
    stats = {
        "total": 0,
        "active": 0,
        "expired": 0,
        "no_period": 0,    # period 필드 자체가 없는 경우
        "parse_failed": 0, # period 필드는 있으나 날짜 파싱 실패
        "deleted": 0,
    }

    for point in pts:
        payload = point.payload or {}
        title = str(payload.get("title", "")).strip()
        period = str(payload.get("period", "")).strip()
        contentid = str(payload.get("contentid", "")).strip() or None

        stats["total"] += 1

        # period 필드 없는 경우
        if not period:
            logger.debug("period 없음, 건너뜀: %s (id=%s)", title, point.id)
            stats["no_period"] += 1
            results.append({
                "point_id": str(point.id),
                "title": title,
                "contentid": contentid,
                "period": period,
                "status": "no_period",
            })
            continue

        end_date = _parse_end_date(period)

        # 파싱 실패
        if end_date is None:
            logger.warning("period 파싱 실패, 건너뜀: %s | period=%s", title, period)
            stats["parse_failed"] += 1
            results.append({
                "point_id": str(point.id),
                "title": title,
                "contentid": contentid,
                "period": period,
                "status": "parse_failed",
            })
            continue

        # 종료일 미경과 → 활성
        if end_date >= today:
            logger.debug("활성 콘텐츠: %s (종료: %s)", title, end_date)
            stats["active"] += 1
            results.append({
                "point_id": str(point.id),
                "title": title,
                "contentid": contentid,
                "period": period,
                "end_date": end_date.isoformat(),
                "status": "active",
            })
            continue

        # 종료일 경과 → 삭제 대상
        logger.info(
            "[만료] %s (종료: %s, id=%s) → %s",
            title, end_date, point.id,
            "dry_run" if dry_run else "삭제",
        )
        stats["expired"] += 1

        delete_info = _delete_and_sync(client, point.id, contentid, dry_run)
        if not dry_run:
            stats["deleted"] += 1

        results.append({
            "point_id": str(point.id),
            "title": title,
            "contentid": contentid,
            "period": period,
            "end_date": end_date.isoformat(),
            "status": "expired",
            "delete_info": delete_info,
        })

    # 리포트 저장
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"cleanup_contents_{date.today().isoformat()}.json"
    report = {
        "date": today.isoformat(),
        "dry_run": dry_run,
        "stats": stats,
        "results": results,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("리포트 저장: %s | 통계: %s", report_path, stats)

    return report


# ---------------------------------------------------------------------------
# CLI 엔트리포인트
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="만료된 콘텐츠 VectorDB 정리")
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=True,
        help="실제 삭제 수행 (기본값: dry-run 모드)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    run(dry_run=args.dry_run)
