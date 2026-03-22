"""
폐업 장소 VectorDB 정리 스케줄러.

Qdrant scroll cursor 방식으로 매주 다른 구간(places 30건 + photos 30건)을 순환 검사하여
전체 장소를 시간에 걸쳐 모두 커버한다.

Kakao Local 키워드 검색 API로 장소 존재 여부를 확인하고
no_match / closed_suspected 상태의 장소를 양 컬렉션에서 동기 삭제한다.

실행:
    python -m app.scripts.scheduler.cleanup_closed_places [--no-dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList

# 프로젝트 루트를 sys.path에 추가
BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from app.utils.config import PLACES_COLLECTION, PHOTOS_COLLECTION
from app.scripts.check_places_with_naver import (
    MatchResult,
    LocalSearchCandidate,
    normalize_key,
    jaccard_similarity,
    distance_meters,
    tokenize_title,
    tokenize_address,
    clean_address,
    normalize_space,
    strip_html,
    to_float,
    only_digits,
    transliterate_title_variants,
    build_query_variants,
)

logger = logging.getLogger(__name__)

KAKAO_KEYWORD_ENDPOINT = "https://dapi.kakao.com/v2/local/search/keyword.json"
DEFAULT_TIMEOUT = 10
DEFAULT_SLEEP_MS = 150

REPORTS_DIR = BACKEND_DIR / "data" / "scheduler_reports"
STATE_FILE = REPORTS_DIR / "scroll_state.json"

# 폐업 판단 임계값 (NaverPlaceChecker와 동일 기준)
OPEN_THRESHOLD = 2.6
REVIEW_THRESHOLD = 1.65
CLOSED_DISTANCE_M = 180


# ---------------------------------------------------------------------------
# Kakao 검색 후보 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class KakaoCandidate:
    query: str
    place_name: str
    address_name: str
    road_address_name: str
    phone: str
    category_name: str
    place_url: str
    x: str  # 경도 (longitude)
    y: str  # 위도 (latitude)

    @property
    def best_address(self) -> str:
        return self.road_address_name or self.address_name

    @property
    def lat(self) -> float | None:
        return to_float(self.y)

    @property
    def lon(self) -> float | None:
        return to_float(self.x)


# ---------------------------------------------------------------------------
# Kakao Local Keyword 검색 클래스
# ---------------------------------------------------------------------------

class KakaoPlaceChecker:
    """
    Kakao Local 키워드 검색 API 기반 장소 폐업 판단 클래스.
    NaverPlaceChecker 패턴을 따른다.
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, sleep_ms: int = DEFAULT_SLEEP_MS) -> None:
        self.timeout = timeout
        self.sleep_ms = sleep_ms
        self.api_key = (os.getenv("KAKAO_REST_API_KEY") or "").strip()

    def ensure_credentials(self) -> None:
        if not self.api_key:
            raise RuntimeError("KAKAO_REST_API_KEY 환경변수가 필요합니다.")

    def keyword_search(
        self, query: str, x: str | None = None, y: str | None = None, radius: int = 500, size: int = 5
    ) -> list[KakaoCandidate]:
        """Kakao 키워드 검색 API 호출."""
        headers = {"Authorization": f"KakaoAK {self.api_key}"}
        params: dict[str, Any] = {"query": query, "size": max(1, min(size, 15))}
        if x:
            params["x"] = x
        if y:
            params["y"] = y
        if x and y:
            params["radius"] = radius

        try:
            response = requests.get(
                KAKAO_KEYWORD_ENDPOINT,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Kakao 키워드 검색 API 호출 실패: {exc}") from exc

        documents = response.json().get("documents") or []
        results: list[KakaoCandidate] = []
        for doc in documents:
            results.append(
                KakaoCandidate(
                    query=query,
                    place_name=normalize_space(doc.get("place_name") or ""),
                    address_name=normalize_space(doc.get("address_name") or ""),
                    road_address_name=normalize_space(doc.get("road_address_name") or ""),
                    phone=normalize_space(doc.get("phone") or ""),
                    category_name=normalize_space(doc.get("category_name") or ""),
                    place_url=normalize_space(doc.get("place_url") or ""),
                    x=str(doc.get("x") or "").strip(),
                    y=str(doc.get("y") or "").strip(),
                )
            )
        return results

    def search_candidates(
        self, item: dict[str, Any]
    ) -> tuple[list[str], list[KakaoCandidate]]:
        """쿼리 변형을 생성하고 중복 제거된 후보 목록을 반환한다."""
        queries = build_query_variants(item)
        deduped: list[KakaoCandidate] = []
        seen: set[tuple[str, str]] = set()

        x = str(item.get("mapx") or "").strip() or None
        y = str(item.get("mapy") or "").strip() or None

        for query in queries:
            try:
                candidates = self.keyword_search(query, x=x, y=y)
            except RuntimeError as exc:
                raise RuntimeError(f"Kakao 검색 실패: {exc}") from exc

            for c in candidates:
                key = (normalize_key(c.place_name), clean_address(c.best_address))
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(c)

            if self.sleep_ms > 0:
                time.sleep(self.sleep_ms / 1000)

        return queries, deduped

    def evaluate_match(
        self, item: dict[str, Any], queries: list[str], candidates: list[KakaoCandidate]
    ) -> MatchResult:
        """후보 목록에 대해 유사도 점수를 계산하고 상태를 결정한다."""
        if not candidates:
            return MatchResult(
                status="no_match",
                score=0.0,
                decision_reason="Kakao 검색 결과 없음",
                candidate=None,
                searched_queries=queries,
            )

        item_title = normalize_space(str(item.get("title", "")))
        item_title_key = normalize_key(item_title)
        item_title_ko_variants = transliterate_title_variants(item_title)
        item_addr = clean_address(str(item.get("addr", "")))
        item_addr_tokens = set(tokenize_address(item_addr))
        input_lat = to_float(item.get("mapy"))
        input_lon = to_float(item.get("mapx"))
        tel_digits = only_digits(item.get("tel") or "")

        best_candidate: KakaoCandidate | None = None
        best_score = -1.0
        best_reason = "후보 점수 계산"
        best_name_similarity = 0.0
        best_address_similarity = 0.0
        best_distance: float | None = None

        for candidate in candidates:
            candidate_title_key = normalize_key(candidate.place_name)
            candidate_addr = clean_address(candidate.best_address)
            candidate_addr_tokens = set(tokenize_address(candidate_addr))

            # 이름 유사도
            name_similarity = 0.0
            if item_title_key and candidate_title_key:
                if item_title_key == candidate_title_key:
                    name_similarity = 1.0
                elif item_title_key in candidate_title_key or candidate_title_key in item_title_key:
                    name_similarity = 0.86
                else:
                    name_similarity = jaccard_similarity(
                        set(tokenize_title(item_title_key)),
                        set(tokenize_title(candidate_title_key)),
                    )

            # 음역 유사도
            translit_similarity = 0.0
            for variant in item_title_ko_variants:
                variant_key = normalize_key(variant)
                if not variant_key:
                    continue
                if variant_key == candidate_title_key:
                    translit_similarity = max(translit_similarity, 0.95)
                elif variant_key in candidate_title_key or candidate_title_key in variant_key:
                    translit_similarity = max(translit_similarity, 0.72)

            # 주소 유사도
            address_similarity = jaccard_similarity(item_addr_tokens, candidate_addr_tokens)
            if item_addr and candidate_addr and item_addr == candidate_addr:
                address_similarity = 1.0

            # 전화번호 유사도
            tel_similarity = 1.0 if tel_digits and tel_digits == only_digits(candidate.phone) else 0.0

            # 거리 점수
            candidate_distance = distance_meters(input_lat, input_lon, candidate.lat, candidate.lon)
            distance_score = 0.0
            if candidate_distance is not None:
                if candidate_distance <= 80:
                    distance_score = 1.0
                elif candidate_distance <= 180:
                    distance_score = 0.72
                elif candidate_distance <= 350:
                    distance_score = 0.35
                else:
                    distance_score = -0.3

            score = (
                max(name_similarity, translit_similarity) * 1.9
                + address_similarity * 1.65
                + tel_similarity * 0.8
                + distance_score * 0.9
            )

            if score > best_score:
                best_candidate = candidate
                best_score = score
                best_name_similarity = max(name_similarity, translit_similarity)
                best_address_similarity = address_similarity
                best_distance = candidate_distance
                best_reason = (
                    f"name={best_name_similarity:.2f}, addr={best_address_similarity:.2f}, "
                    f"dist={candidate_distance if candidate_distance is not None else 'n/a'}"
                )

        if best_candidate is None:
            return MatchResult(
                status="no_match",
                score=0.0,
                decision_reason="후보 선택 실패",
                candidate=None,
                searched_queries=queries,
            )

        # MatchResult.candidate는 LocalSearchCandidate 타입이지만
        # KakaoCandidate를 그대로 저장 (리포트용으로만 사용)
        if best_score >= OPEN_THRESHOLD:
            return MatchResult(
                status="open",
                score=best_score,
                decision_reason=best_reason,
                candidate=best_candidate,  # type: ignore[arg-type]
                searched_queries=queries,
                name_similarity=best_name_similarity,
                address_similarity=best_address_similarity,
                distance_m=best_distance,
            )

        if best_score >= REVIEW_THRESHOLD:
            return MatchResult(
                status="review_needed",
                score=best_score,
                decision_reason=f"부분 일치: {best_reason}",
                candidate=best_candidate,  # type: ignore[arg-type]
                searched_queries=queries,
                name_similarity=best_name_similarity,
                address_similarity=best_address_similarity,
                distance_m=best_distance,
            )

        if best_distance is not None and best_distance <= CLOSED_DISTANCE_M:
            status = "review_needed"
            reason = f"주소는 가깝지만 상호 불일치: {best_reason}"
        else:
            status = "closed_suspected"
            reason = f"강한 일치 후보 없음: {best_reason}"

        return MatchResult(
            status=status,
            score=best_score,
            decision_reason=reason,
            candidate=best_candidate,  # type: ignore[arg-type]
            searched_queries=queries,
            name_similarity=best_name_similarity,
            address_similarity=best_address_similarity,
            distance_m=best_distance,
        )

    def check_item(self, item: dict[str, Any]) -> MatchResult:
        queries, candidates = self.search_candidates(item)
        return self.evaluate_match(item, queries, candidates)


# ---------------------------------------------------------------------------
# Scroll cursor 상태 관리
# ---------------------------------------------------------------------------

def _load_scroll_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"places_offset": None, "photos_offset": None}


def _save_scroll_state(places_offset: Any, photos_offset: Any) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"places_offset": places_offset, "photos_offset": photos_offset}, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 삭제 로직 (양 컬렉션 동기)
# ---------------------------------------------------------------------------

def _delete_and_sync(
    client: QdrantClient,
    point_id: Any,
    contentid: str | None,
    source_collection: str,
    dry_run: bool,
) -> dict[str, Any]:
    """
    소스 컬렉션에서 point를 삭제하고 반대 컬렉션에서 contentid 기준으로 동기 삭제한다.
    dry_run=True이면 삭제 없이 로그만 남긴다.
    """
    other_collection = PHOTOS_COLLECTION if source_collection == PLACES_COLLECTION else PLACES_COLLECTION
    deleted_ids: list[Any] = []
    synced_ids: list[Any] = []

    if not dry_run:
        client.delete(source_collection, points_selector=PointIdsList(points=[point_id]))
        deleted_ids.append(point_id)

        if contentid:
            other_pts, _ = client.scroll(
                other_collection,
                scroll_filter=Filter(must=[
                    FieldCondition(key="contentid", match=MatchValue(value=contentid))
                ]),
                with_payload=False,
                with_vectors=False,
            )
            if other_pts:
                other_ids = [p.id for p in other_pts]
                client.delete(other_collection, points_selector=PointIdsList(points=other_ids))
                synced_ids.extend(other_ids)

    return {
        "source_collection": source_collection,
        "point_id": str(point_id),
        "contentid": contentid,
        "deleted_ids": [str(i) for i in deleted_ids],
        "synced_collection": other_collection,
        "synced_ids": [str(i) for i in synced_ids],
        "dry_run": dry_run,
    }


# ---------------------------------------------------------------------------
# 메인 실행 함수
# ---------------------------------------------------------------------------

def run(dry_run: bool = True) -> dict[str, Any]:
    """
    폐업 장소 정리 실행.

    Args:
        dry_run: True이면 삭제 없이 리포트만 생성 (초기 운영 시 사용).

    Returns:
        실행 결과 요약 딕셔너리.
    """
    logger.info("폐업 장소 정리 시작 (dry_run=%s)", dry_run)

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=60)

    checker = KakaoPlaceChecker()
    checker.ensure_credentials()

    # scroll cursor 로드
    state = _load_scroll_state()
    places_offset = state.get("places_offset")
    photos_offset = state.get("photos_offset")

    # 각 컬렉션에서 30건씩 scroll (총 60건 검사)
    places_pts, next_places_offset = client.scroll(
        PLACES_COLLECTION,
        offset=places_offset,
        limit=30,
        with_payload=True,
        with_vectors=False,
    )
    photos_pts, next_photos_offset = client.scroll(
        PHOTOS_COLLECTION,
        offset=photos_offset,
        limit=30,
        with_payload=True,
        with_vectors=False,
    )

    # cursor 저장 (None이면 다음 실행 시 처음부터)
    _save_scroll_state(next_places_offset, next_photos_offset)
    logger.info(
        "Scroll: places %d건 (next_offset=%s), photos %d건 (next_offset=%s)",
        len(places_pts), next_places_offset, len(photos_pts), next_photos_offset,
    )

    results: list[dict[str, Any]] = []
    stats = {"total": 0, "open": 0, "review_needed": 0, "closed_suspected": 0, "no_match": 0, "deleted": 0, "error": 0}

    sample_points = [(p, PLACES_COLLECTION) for p in places_pts] + [(p, PHOTOS_COLLECTION) for p in photos_pts]

    for point, source_collection in sample_points:
        payload = point.payload or {}

        # 표시명: 팝업/축제는 title(행사명), 일반 장소는 name/title 순
        name = (payload.get("title") or payload.get("name") or payload.get("place") or "").strip()
        # 지도 검색어: place(장소명) 우선, 없으면 name/title 폴백
        map_search_name = (payload.get("place") or name).strip()

        item = {
            "title": map_search_name,  # Kakao 키워드 검색에 사용되는 쿼리
            "addr": payload.get("addr", ""),
            "mapx": payload.get("mapx", ""),
            "mapy": payload.get("mapy", ""),
            "tel": payload.get("tel", ""),
        }
        contentid = str(payload.get("contentid", "")) or None

        if not name:
            logger.debug("title 없는 point 건너뜀: %s", point.id)
            continue

        stats["total"] += 1
        try:
            match_result = checker.check_item(item)
        except Exception as exc:
            logger.error("Kakao 검색 실패 (point_id=%s, title=%s): %s", point.id, name, exc)
            stats["error"] += 1
            results.append({
                "point_id": str(point.id),
                "source_collection": source_collection,
                "title": name,
                "map_search_name": map_search_name,
                "addr": item["addr"],
                "contentid": contentid,
                "status": "error",
                "error": str(exc),
            })
            continue

        stats[match_result.status] = stats.get(match_result.status, 0) + 1
        logger.info(
            "[%s] %s → %s (score=%.2f, reason=%s)",
            source_collection, name, match_result.status,
            match_result.score, match_result.decision_reason,
        )

        entry: dict[str, Any] = {
            "point_id": str(point.id),
            "source_collection": source_collection,
            "title": name,
            "map_search_name": map_search_name,  # 실제 Kakao 검색에 사용된 쿼리
            "addr": item["addr"],
            "contentid": contentid,
            "status": match_result.status,
            "score": round(match_result.score, 4),
            "decision_reason": match_result.decision_reason,
            "searched_queries": match_result.searched_queries,
        }

        # 삭제 대상: no_match 또는 closed_suspected
        if match_result.status in ("no_match", "closed_suspected"):
            delete_info = _delete_and_sync(client, point.id, contentid, source_collection, dry_run)
            entry["delete_info"] = delete_info
            if not dry_run:
                stats["deleted"] += 1

        results.append(entry)

    # 리포트 저장
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"cleanup_{date.today().isoformat()}.json"
    report = {
        "date": date.today().isoformat(),
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
    parser = argparse.ArgumentParser(description="폐업 장소 VectorDB 정리")
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
