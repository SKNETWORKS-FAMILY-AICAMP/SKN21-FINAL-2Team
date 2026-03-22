"""
매주 월요일 08:00 KST 실행되는 배치 작업 엔트리포인트.

실행:
    python -m app.scripts.scheduler.weekly_scheduler_job [--no-dry-run]

AWS SSM Run Command 예시:
    CONTAINER=$(docker ps -qf "label=com.docker.compose.service=backend")
    docker exec -T "$CONTAINER" python -m app.scripts.scheduler.weekly_scheduler_job
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scripts.scheduler.cleanup_closed_places import run as cleanup_run
from app.scripts.scheduler.cleanup_expired_contents import run as cleanup_contents_run
from app.scripts.scheduler.sync_new_popup_data import run as sync_run


def main(dry_run: bool = True) -> int:
    """주간 스케줄러 메인 함수.

    Args:
        dry_run (bool, optional): 실제 삭제 수행 여부. True이면 삭제하지 않음.

    Returns:
        int: 성공 시 0, 실패 시 1
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 주간 스케줄러 시작 (dry_run=%s) ===", dry_run)

    errors: list[Exception] = []

    # 1. 폐업 장소 정리 (places 30건 + photos 30건 Kakao API 검증)
    logger.info("--- [1/3] 폐업 장소 정리 ---")
    try:
        report = cleanup_run(dry_run=dry_run)
        stats = report.get("stats", {})
        logger.info(
            "폐업 정리 완료: total=%d, deleted=%d, closed_suspected=%d, no_match=%d, review_needed=%d",
            stats.get("total", 0),
            stats.get("deleted", 0),
            stats.get("closed_suspected", 0),
            stats.get("no_match", 0),
            stats.get("review_needed", 0),
        )
    except Exception as exc:
        logger.error("폐업 정리 실패: %s", exc, exc_info=True)
        errors.append(exc)

    # 2. 만료된 콘텐츠(축제/팝업) 정리 (period 종료일 기준, 20건 순환)
    logger.info("--- [2/3] 만료 콘텐츠 정리 ---")
    try:
        report = cleanup_contents_run(dry_run=dry_run)
        stats = report.get("stats", {})
        logger.info(
            "만료 콘텐츠 정리 완료: total=%d, expired=%d, deleted=%d, active=%d, no_period=%d, parse_failed=%d",
            stats.get("total", 0),
            stats.get("expired", 0),
            stats.get("deleted", 0),
            stats.get("active", 0),
            stats.get("no_period", 0),
            stats.get("parse_failed", 0),
        )
    except Exception as exc:
        logger.error("만료 콘텐츠 정리 실패: %s", exc, exc_info=True)
        errors.append(exc)

    # 3. 팝업스토어 신규 데이터 동기화
    logger.info("--- [3/3] 팝업스토어 신규 데이터 동기화 ---")
    try:
        stats = sync_run(headless=True)
        logger.info(
            "팝업 동기화 완료: crawled=%d, normalized=%d, skipped=%d, upserted=%d",
            stats.get("crawled", 0),
            stats.get("normalized", 0),
            stats.get("skipped_duplicates", 0),
            stats.get("upserted", 0),
        )
    except Exception as exc:
        logger.error("팝업 동기화 실패: %s", exc, exc_info=True)
        errors.append(exc)

    if errors:
        logger.error("=== 주간 스케줄러 완료 (오류 %d건) ===", len(errors))
        return 1

    logger.info("=== 주간 스케줄러 완료 (3/3 성공) ===")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="주간 스케줄러 배치 작업")
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=True,
        help="실제 삭제 수행 (기본값: dry-run 모드)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(main(dry_run=args.dry_run))
