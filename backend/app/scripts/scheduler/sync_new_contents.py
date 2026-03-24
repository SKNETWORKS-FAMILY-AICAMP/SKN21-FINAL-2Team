"""
콘텐츠(팝업스토어 + 문화행사) 신규 데이터 동기화 스케줄러.

collect → preprocess → enrich → qdrant upsert 파이프라인으로
Qdrant에 없는 신규 콘텐츠만 추가한다.

실행:
    python -m app.scripts.scheduler.sync_new_contents
    python -m app.scripts.scheduler.sync_new_contents --source popply
    python -m app.scripts.scheduler.sync_new_contents --source seoul_culture
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from app.utils.config import PLACES_COLLECTION

log = logging.getLogger(__name__)

DATA_DIR = BACKEND_DIR / "data"
REPORTS_DIR = DATA_DIR / "scheduler_reports"


# ── 소스별 설정 ──────────────────────────────────────────────


@dataclass
class ContentSource:
    name: str
    collect: Callable[..., None]
    preprocess: Callable[[], None]
    enrich_target: str                       # generate_content_llm_text에 넘길 이름
    preprocessed_file: str                   # preprocessed/ 아래 파일명
    enrich_file: str                         # enrich/ 아래 파일명
    collect_kwargs: dict[str, Any] = field(default_factory=dict)


def _build_sources(existing_ids: set[str], headless: bool) -> dict[str, ContentSource]:
    from app.scripts.collect.popply import collect as popply_collect
    from app.scripts.collect.seoul_culture import collect as culture_collect
    from app.scripts.preprocess.popply import preprocess as popply_preprocess
    from app.scripts.preprocess.seoul_culture import preprocess as culture_preprocess

    return {
        "popply": ContentSource(
            name="팝업스토어",
            collect=popply_collect,
            preprocess=popply_preprocess,
            enrich_target="popply_팝업스토어",
            preprocessed_file="popply_팝업스토어.json",
            enrich_file="popply_팝업스토어_enrich.json",
            collect_kwargs={"headless": headless, "exclude_ids": existing_ids},
        ),
        "seoul_culture": ContentSource(
            name="문화행사",
            collect=culture_collect,
            preprocess=culture_preprocess,
            enrich_target="seoul_culture_문화행사",
            preprocessed_file="seoul_culture_문화행사.json",
            enrich_file="seoul_culture_문화행사_enrich.json",
        ),
    }


# ── 공통 로직 ────────────────────────────────────────────────


def _get_existing_contentids(client: QdrantClient) -> set[str]:
    existing: set[str] = set()
    offset = None
    while True:
        pts, next_offset = client.scroll(
            PLACES_COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="contenttypeid", match=MatchValue(value="콘텐츠"))
            ]),
            offset=offset, limit=500,
            with_payload=["contentid"], with_vectors=False,
        )
        for p in pts:
            cid = str((p.payload or {}).get("contentid", "")).strip()
            if cid:
                existing.add(cid)
        if next_offset is None:
            break
        offset = next_offset
    return existing


def _sync_one(src: ContentSource, existing_ids: set[str], dry_run: bool = False) -> dict[str, Any]:
    """단일 소스에 대해 collect → preprocess → enrich → upsert 파이프라인 실행."""
    log.info("── %s 동기화 시작 (dry_run=%s) ──", src.name, dry_run)

    # 1. 수집
    src.collect(**src.collect_kwargs)

    # 2. 전처리
    src.preprocess()

    # 3. 신규만 필터
    pre_path = DATA_DIR / "preprocessed" / src.preprocessed_file
    new_count = _filter_new(pre_path, existing_ids)
    if new_count == 0:
        log.info("신규 %s 없음, 스킵", src.name)
        return {"source": src.name, "new": 0, "upserted": 0, "dry_run": dry_run}
    log.info("신규 %s: %d건", src.name, new_count)

    # 4. llm_text + tags 생성
    from app.scripts.enrich.generate_content_llm_text import process as enrich
    enrich(src.enrich_target)

    # 5. Qdrant upsert (dry_run이면 스킵)
    upserted = 0
    enrich_path = DATA_DIR / "enrich" / src.enrich_file
    if dry_run:
        if enrich_path.exists():
            with open(enrich_path, encoding="utf-8") as f:
                upserted = len(json.load(f))
        log.info("[dry_run] upsert 스킵: %d건 대상", upserted)
    else:
        upserted = _upsert(enrich_path)

    return {"source": src.name, "new": new_count, "upserted": upserted, "dry_run": dry_run}


def _filter_new(path: Path, existing_ids: set[str]) -> int:
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    new = [d for d in data if str(d.get("contentid", "")) not in existing_ids]
    if not new:
        return 0
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)
    return len(new)


def _upsert(path: Path) -> int:
    if not path.exists():
        return 0
    from app.scripts.qdrant_upsert import QdrantUploader
    uploader = QdrantUploader(recreate=False)
    uploader.upsert_file(str(path))
    with open(path, encoding="utf-8") as f:
        return len(json.load(f))


# ── 진입점 ───────────────────────────────────────────────────


def run(headless: bool = True, sources: list[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    log.info("=== 콘텐츠 신규 동기화 시작 (dry_run=%s) ===", dry_run)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        timeout=60,
    )

    existing_ids = _get_existing_contentids(client)
    log.info("기존 콘텐츠: %d건", len(existing_ids))

    all_sources = _build_sources(existing_ids, headless)
    targets = sources or list(all_sources)
    results = [_sync_one(all_sources[s], existing_ids, dry_run=dry_run) for s in targets if s in all_sources]

    # 리포트
    stats = {"date": date.today().isoformat(), "dry_run": dry_run, "existing": len(existing_ids), "results": results}
    report = REPORTS_DIR / f"contents_sync_{date.today().isoformat()}.json"
    report.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("=== 콘텐츠 신규 동기화 완료 ===")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["popply", "seoul_culture"])
    p.add_argument("--no-dry-run", dest="dry_run", action="store_false", default=True,
                   help="실제 upsert 수행 (기본: dry-run 모드)")
    args = p.parse_args()
    run(headless=True, sources=[args.source] if args.source else None, dry_run=args.dry_run)
