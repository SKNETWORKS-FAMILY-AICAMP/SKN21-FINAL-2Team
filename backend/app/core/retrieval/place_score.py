"""
place_score.py — 점수 계산 전담 모듈

모듈레벨 순수 함수:
  _normalize_match_text, _district_stem, _addr_token_stem,
  _build_compact_text, _to_positive_int, _safe_float, _extract_place_id

PlaceScorer mixin:
  토큰화, 주소 파싱, BM25, 키워드/위치/거리 boost, reranker
  → PlaceRetriever가 상속해서 self.메서드()로 호출
"""


import asyncio
import math
import re
from typing import Any
from sentence_transformers import CrossEncoder

from app.agents.models.output import CategoryType
from app.utils.config import (
    PLACES_COLLECTION,
    PHOTOS_COLLECTION,
    DEVICE,
    BM25_POOL_LIMIT,
    SPARSE_ADDR_EXACT_WEIGHT,
    SPARSE_ADDR_STEM_WEIGHT,
    SPARSE_ADDR_MAX_BOOST,
)
from app.scripts.preprocess_data import build_addr_tokens
from app.utils.place_id import get_place_id_from_point


# ---------------------------------------------------------------------------
# 모듈레벨 순수 헬퍼 (상태 없음)
# ---------------------------------------------------------------------------

def _normalize_match_text(text: str) -> str:
    """
    한글, 영문 소문자, 숫자 외 모든 문자(공백, 특수문자 포함) 제거
    """
    return re.sub(r"[^0-9a-z가-힣]+", "", str(text or "").lower())


def _district_stem(token: str) -> str:
    token = str(token or "").strip()
    if token.endswith(("구", "군", "시", "동", "읍", "면", "리")) and len(token) > 1:
        return token[:-1]
    return token


def _addr_token_stem(token: str) -> str:
    token = str(token or "").strip()
    if token.endswith(("구", "군", "시", "동", "읍", "면", "리", "로", "길")) and len(token) > 1:
        return token[:-1]
    return token


def _build_compact_text(payload: dict[str, Any]) -> str:
    title = str(payload.get("title") or payload.get("name") or "").strip()
    category = str(payload.get("contenttypeid") or payload.get("category") or "").strip()
    addr = str(payload.get("addr") or payload.get("address") or payload.get("road_address") or "").strip()
    return " ".join([part for part in (title, category, addr) if part]).strip()


def _to_positive_int(value: Any) -> int | None:
    if value in (None, "", 0, 0.0):
        return None
    try:
        parsed = int(str(value).strip())
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        parsed = float(value)
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _extract_place_id(point: Any, source_collection: str) -> int | None:
    if source_collection == PHOTOS_COLLECTION:
        cid = get_place_id_from_point(point, prefer_payload=True, fallback_to_point_id=False)
    else:
        cid = get_place_id_from_point(point, prefer_payload=False, fallback_to_point_id=True)
    return _to_positive_int(cid)


# ---------------------------------------------------------------------------
# PlaceScorer — 점수 계산 mixin
# PlaceRetriever가 상속. self.client / self.text_model 등은 PlaceRetriever.__init__에서 설정.
# ---------------------------------------------------------------------------

class PlaceScorer:
    """
    점수 계산 전담 mixin.
    - 토큰화 / 주소 파싱
    - BM25 lexical 채점
    - 키워드 / 위치 텍스트 / Geo 거리 / 주소 sparse boost
    - Reranker (CrossEncoder) 로드 및 추론
    """

    # reranker 상태 — PlaceRetriever.__init__에서 초기화
    _reranker: "CrossEncoder | None"
    _reranker_load_attempted: bool

    # ------------------------------------------------------------------
    # 토큰화
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[가-힣A-Za-z0-9]+", text or "")

    def _extract_query_addr_tokens(self, text: str) -> list[str]:
        if not text:
            return []
        raw_tokens = re.findall(r"[가-힣A-Za-z0-9]+(?:구|군|시|동|읍|면|리|로|길)?|\d+-\d+", text)
        tokens: list[str] = []
        for token in raw_tokens:
            token = str(token).strip().lower()
            if not token:
                continue
            if len(token) == 1 and not token.isdigit():
                continue
            tokens.append(token)
            stem = _addr_token_stem(token)
            if stem != token and stem:
                tokens.append(stem)

        deduped: list[str] = []
        for token in tokens:
            if token not in deduped:
                deduped.append(token)
        return deduped

    def _payload_addr_tokens(self, payload: dict[str, Any]) -> list[str]:
        if not payload:
            return []
        raw = payload.get("addr_tokens")
        if isinstance(raw, list):
            return [str(t).strip().lower() for t in raw if str(t).strip()]
        # 하위 호환: 적재 데이터에 addr_tokens가 없으면 런타임 보강
        return build_addr_tokens(payload)

    # ------------------------------------------------------------------
    # 좌표 / 거리
    # ------------------------------------------------------------------

    def _payload_coordinates(self, payload: dict[str, Any]) -> tuple[float | None, float | None]:
        if not payload:
            return None, None

        geo = payload.get("geo")
        if isinstance(geo, dict):
            geo_lat = _safe_float(geo.get("lat"))
            geo_lng = _safe_float(geo.get("long"))
            if geo_lat is not None and geo_lng is not None:
                if -90.0 <= geo_lat <= 90.0 and -180.0 <= geo_lng <= 180.0:
                    return geo_lat, geo_lng

        lat_keys = ("lat", "mapy", "latitude")
        lng_keys = ("lng", "mapx", "longitude")
        lat = next((_safe_float(payload.get(k)) for k in lat_keys if _safe_float(payload.get(k)) is not None), None)
        lng = next((_safe_float(payload.get(k)) for k in lng_keys if _safe_float(payload.get(k)) is not None), None)

        if lat is None or lng is None:
            return None, None
        if abs(lat) < 1e-9 and abs(lng) < 1e-9:
            return None, None
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return None, None
        return lat, lng

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 좌표 간 거리(km)."""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # ------------------------------------------------------------------
    # Boost 함수
    # ------------------------------------------------------------------

    def _addr_sparse_bonus(
        self,
        query_addr_tokens: list[str],
        payload_addr_tokens: list[str],
        max_boost: float = SPARSE_ADDR_MAX_BOOST,
        exact_weight: float = SPARSE_ADDR_EXACT_WEIGHT,
        stem_weight: float = SPARSE_ADDR_STEM_WEIGHT,
    ) -> float:
        """
        주소 sparse 보너스
        (예: '강남구' -> '강남' 매칭)
        """
        if not query_addr_tokens or not payload_addr_tokens:
            return 0.0
        payload_token_set = set(payload_addr_tokens)
        payload_stem_set = {_addr_token_stem(t) for t in payload_token_set}
        bonus = 0.0
        for token in query_addr_tokens:
            if token in payload_token_set:
                bonus += exact_weight
                continue
            stem = _addr_token_stem(token)
            if stem and stem in payload_stem_set:
                bonus += stem_weight
        return min(max_boost, bonus)

    def _keyword_match_bonus(self, query: str, payload: dict) -> float:
        """
        키워드 매칭 보너스.
        - 상호명 직접 검색(query 토큰 중 title이 완전히 일치)에만 강한 보너스 부여.
        - 문자열 부분 포함(in) 대신 토큰 단위 완전 일치로 비교:
            "홍대김밥" in "홍대김밥집" → True (오매칭)
            "홍대김밥" in {"홍대", "김밥집"} → False (올바른 판단)
        - 주소 기반 행정구역 매칭은 _addr_sparse_bonus가 전담하므로 제거.
        """
        if not query or not payload:
            return 0.0

        title = str(payload.get("title") or payload.get("name") or "")
        if not title:
            return 0.0

        title_norm = _normalize_match_text(title)
        if not title_norm:
            return 0.0

        # query를 토큰 단위로 분리
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return 0.0

        bonus = 0.0

        # Case 1: title 전체가 query 토큰 중 하나로 완전 일치
        # (예: query={"봉피양", "예약"}, title_norm="봉피양" → 완전 일치 → 강한 보너스)
        # 문자열 substring(in)이 아닌 set membership으로 비교:
        # "홍대김밥" not in {"홍대", "김밥집"} → 오매칭 방지
        if len(title_norm) >= 3 and title_norm in query_tokens:
            bonus += 0.18

        # Case 2: title이 여러 토큰으로 구성된 경우 → query 토큰과 overlap 확인
        # title이 4자 이상이어야 의미 있는 상호명으로 판단 (지역명 혼동 방지)
        elif len(title_norm) >= 4:
            title_tokens = {t for t in self._tokenize(title) if len(t) >= 2}
            overlap = len(query_tokens & title_tokens)
            if overlap > 0:
                # 가중치를 낮게 유지: 주소/지역 매칭(_addr_sparse_bonus)과 역할 분리
                bonus += min(0.06, 0.02 * overlap)

        return min(0.15, bonus)

    def _location_text_bonus(self, preferred_location: str | None, payload: dict) -> float:
        """
        사용자 query의 지역 텍스트 보너스.
        - _normalize_match_text + 문자열 in 비교 대신 토큰 set 비교 사용.
        - "강남" in "서울강북구미아동" 같은 오매칭 방지.
        """
        if not preferred_location or not payload:
            return 0.0

        addr = str(payload.get("addr") or payload.get("address") or payload.get("road_address") or "")
        title = str(payload.get("title") or payload.get("name") or "")

        # 주소 + 제목을 토큰 set으로 분리 (공백 제거된 단일 문자열이 아니라 단어 단위로 비교)
        target_tokens = {_normalize_match_text(t) for t in self._tokenize(f"{addr} {title}") if len(t) >= 1}
        target_stems = {_normalize_match_text(_district_stem(t)) for t in self._tokenize(f"{addr} {title}") if len(t) >= 1}
        if not target_tokens:
            return 0.0

        location_tokens = {t for t in self._tokenize(preferred_location) if len(t) >= 2}
        if not location_tokens:
            return 0.0

        hit_count = 0
        for token in location_tokens:
            token_norm = _normalize_match_text(token)
            if token_norm and token_norm in target_tokens:
                hit_count += 1
                continue
            stem_norm = _normalize_match_text(_district_stem(token))
            if stem_norm and stem_norm in target_stems:
                hit_count += 1

        return min(0.10, 0.03 * hit_count)

    def _geo_proximity_bonus(
        self,
        payload: dict,
        anchor_lat: float | None,
        anchor_lng: float | None,
        radius_km: float = 20.0,
        max_boost: float = 0.20,
    ) -> float:
        """
        물리적 거리 기반 보너스
        """
        if anchor_lat in (None, 0, 0.0) or anchor_lng in (None, 0, 0.0):
            return 0.0

        point_lat, point_lng = self._payload_coordinates(payload)
        if point_lat is None or point_lng is None:
            return 0.0

        dist_km = self._haversine(anchor_lat, anchor_lng, point_lat, point_lng)
        if dist_km > radius_km:
            return 0.0

        normalized = max(0.0, 1.0 - (dist_km / radius_km))
        return max_boost * normalized

    # ------------------------------------------------------------------
    # BM25 lexical 검색 (vector pool 재채점)
    # ------------------------------------------------------------------

    def _payload_matches_category(self, payload: dict, categories: list[CategoryType] | None) -> bool:
        if not categories:
            return True
        category_values = [c.value for c in categories]
        payload_values = {
            str(payload.get("contenttypeid") or "").strip(),
            str(payload.get("category") or "").strip(),
        }
        payload_values.discard("")
        return any(value in payload_values for value in category_values)

    def _bm25_like_score(
        self,
        query: str,
        payload: dict,
        doc_freq: dict[str, int] | None = None,
        num_docs: int = 1,
    ) -> float:
        """
        title과 addr에 대한 BM25 유사도 점수.
        doc_freq / num_docs 가 제공되면 IDF 가중치를 적용한다.
        (IDF 없을 시 고빈도 범용 단어가 고유명사와 동일하게 취급되는 문제 해결)
        """
        tokens = self._tokenize(query)
        if not tokens:
            return 0.0
        doc_text = _build_compact_text(payload)
        doc_tokens = self._tokenize(doc_text)
        if not doc_tokens:
            return 0.0

        freq: dict[str, int] = {}
        for tok in doc_tokens:
            freq[tok] = freq.get(tok, 0) + 1

        k1, b, avgdl = 1.2, 0.75, 120.0
        doc_len = len(doc_tokens)
        n = max(num_docs, 1)
        score = 0.0
        for t in tokens:
            tf = freq.get(t, 0)
            if tf <= 0:
                continue
            # Robertson smoothed IDF
            df = (doc_freq or {}).get(t, 0)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
            tf_component = ((k1 + 1) * tf) / (tf + k1 * (1 - b + b * (doc_len / avgdl)))
            score += idf * tf_component
        return float(1 - math.exp(-score))

    async def _search_bm25_lexical(
        self,
        query: str,
        categories: list[CategoryType] | None,
        candidate_points: list,
        candidate_k: int,
        pool_limit: int = BM25_POOL_LIMIT,
    ) -> list[dict]:
        pool = list(candidate_points)[: max(int(pool_limit or 0), 1)]

        # IDF 계산을 위한 DF 사전 구축 (pool 전체 1회 스캔)
        num_docs = 0
        doc_freq: dict[str, int] = {}
        for p in pool:
            payload = p.payload or {}
            doc_tokens = set(self._tokenize(_build_compact_text(payload)))
            num_docs += 1
            for tok in doc_tokens:
                doc_freq[tok] = doc_freq.get(tok, 0) + 1

        scored = []
        for p in pool:
            payload = p.payload or {}
            if not self._payload_matches_category(payload, categories):
                continue
            lexical_score = self._bm25_like_score(
                query, payload, doc_freq=doc_freq, num_docs=num_docs
            )
            if lexical_score <= 0:
                continue
            scored.append({
                "id": _extract_place_id(p, PLACES_COLLECTION),
                "payload": payload,
                "score": lexical_score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:candidate_k]

    # ------------------------------------------------------------------
    # Reranker (CrossEncoder)
    # ------------------------------------------------------------------

    def _ensure_reranker(self) -> None:
        if self._reranker_load_attempted:
            return
        self._reranker_load_attempted = True
        try:
            self._reranker = CrossEncoder(
                "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
                device=DEVICE,
            )
            print("[INFO] Reranker loaded: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
        except Exception as e:
            self._reranker = None
            print(f"[WARN] Reranker unavailable: {e}")

    async def _rerank_candidates(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        self._ensure_reranker()
        # query가 없으면 reranker 실행 불가 → score 순 유지
        if not self._reranker or not candidates or not (query or "").strip():
            for idx, c in enumerate(candidates[:top_k], start=1):
                c["rerank_score"] = None
                c["final_rank"] = idx
            return candidates[:top_k]

        pairs = [(query, _build_compact_text(c.get("payload", {}))) for c in candidates]
        try:
            scores = await asyncio.to_thread(self._reranker.predict, pairs)
            for c, s in zip(candidates, scores):
                # sigmoid 적용: CrossEncoder raw logit(-∞~+∞) → [0.0, 1.0]
                # 음수 오버플로우 방지를 위해 -500 clamp 적용
                logit = max(-500.0, float(s))
                c["rerank_score"] = round(1.0 / (1.0 + math.exp(-logit)), 4)
            candidates.sort(key=lambda x: float(x.get("rerank_score", 0.0)), reverse=True)
            for idx, c in enumerate(candidates[:top_k], start=1):
                c["final_rank"] = idx
            return candidates[:top_k]
        except Exception as e:
            print(f"[WARN] Reranker inference failed: {e}")
            for idx, c in enumerate(candidates[:top_k], start=1):
                c["rerank_score"] = None
                c["final_rank"] = idx
            return candidates[:top_k]
