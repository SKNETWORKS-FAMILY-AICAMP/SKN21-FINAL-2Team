import os
import numpy as np
import asyncio
import math
import re
from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, MatchAny
)
from sentence_transformers import SentenceTransformer, CrossEncoder

from app.utils.config import (
    PLACES_COLLECTION, PHOTOS_COLLECTION, DEVICE,
    TEXT_MODEL, VISION_MODEL, TEXT_VECTOR_SIZE, VISION_VECTOR_SIZE,
    BM25_POOL_LIMIT, BM25_ENABLE_THRESHOLD, BM25_ENABLE_SCORE_THRESHOLD,
    get_retrieval_params,
)
from app.schemas.chat import ChatMessageCreate
from app.scripts.preprocess_data import download_image
from app.utils.geocoder import GeoCoder
from app.services.vision import describe_image
from app.utils.place_id import get_place_id_from_point


def _normalize_match_text(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", str(text or "").lower())


def _district_stem(token: str) -> str:
    token = str(token or "").strip()
    if token.endswith(("구", "군", "시", "동", "읍", "면", "리")) and len(token) > 1:
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


class PlaceRetriever:
    _instance = None
    CATEGORY_NORMALIZATION_MAP = {
        "관광지": "관광지",
        "명소": "관광지",
        "볼거리": "관광지",
        "문화시설": "문화시설",
        "박물관": "문화시설",
        "미술관": "문화시설",
        "전시": "문화시설",
        "축제공연행사": "축제공연행사",
        "축제": "축제공연행사",
        "공연": "축제공연행사",
        "레포츠": "레포츠",
        "액티비티": "레포츠",
        "체험": "레포츠",
        "숙박": "숙박",
        "숙소": "숙박",
        "호텔": "숙박",
        "음식점": "음식점",
        "맛집": "음식점",
        "식당": "음식점",
        "레스토랑": "음식점",
        "카페": "음식점",
        "팝업스토어": "팝업스토어",
        "팝업": "팝업스토어",
    }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            print("[INFO] Initializing PlaceRetriever (Singleton)...")
            cls._instance = cls()
        return cls._instance

    def normalize_category(self, category: str | None) -> str | None:
        if not category:
            return None
        normalized = self.CATEGORY_NORMALIZATION_MAP.get(self._category_to_str(category))
        return normalized

    def _get_category_candidates(self, category: Any) -> list[str]:
        if not category:
            return []
            
        # 리스트인 경우 각 항목에 대해 후보군 추출
        if isinstance(category, list):
            all_candidates = []
            for item in category:
                item_candidates = self._get_category_candidates_single(item)
                for c in item_candidates:
                    if c not in all_candidates:
                        all_candidates.append(c)
            return all_candidates
            
        return self._get_category_candidates_single(category)

    def _get_category_candidates_single(self, category: Any) -> list[str]:
        raw = self._category_to_str(category)
        if not raw:
            return []

        normalized = self.normalize_category(raw)
        candidates: list[str] = []
        for value in (normalized, raw):
            if value and value not in candidates:
                candidates.append(value)
        return candidates

    @staticmethod
    def _category_to_str(category: Any) -> str:
        if category is None:
            return ""
        # Pydantic Enum 또는 일반 Enum 처리
        if hasattr(category, "value"):
            return str(category.value).strip()
        return str(category).strip()

    def __init__(self):
        host = os.getenv('QDRANT_HOST', "localhost")
        port = os.getenv('QDRANT_PORT', 6333)
        print(f"[INFO] Connecting to Qdrant at {host}:{port}")
        self.client = QdrantClient(host=host, port=port)
        
        print(f"[INFO] Loading models: Text={TEXT_MODEL}, Vision={VISION_MODEL}")
        self.text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)
        self.vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)
        self._reranker = None
        self._reranker_load_attempted = False
        
        print(f"[INFO] PlaceRetriever ready on {DEVICE}")

    def _build_category_filter(self, category: Any = None, has_image: bool = False) -> Filter | None:
        """카테고리 필터 생성 (contenttypeid 필드에 한글 명칭으로 저장됨)"""
        must_conditions = []
        must_not_conditions = []
        category_values = self._get_category_candidates(category)

        if category_values:
            if len(category_values) >= 2:
                print(f"[INFO] category candidates built: {category_values}")
            # MatchAny: contenttypeid가 후보값 중 하나와 일치하면 통과 (OR 조건)
            must_conditions.append(
                FieldCondition(key="contenttypeid", match=MatchAny(any=category_values))
            )

        if has_image:
            from qdrant_client.models import IsEmptyCondition, PayloadField
            must_not_conditions.append(IsEmptyCondition(is_empty=PayloadField(key="image")))

        if not must_conditions and not must_not_conditions:
            return None

        built = Filter(
            must=must_conditions if must_conditions else None,
            must_not=must_not_conditions if must_not_conditions else None
        )
        print(f"[INFO] category_filter built: category={category} values={category_values}")
        return built

    def search_text(self, query: str, limit: int = 5, category: Any = None, has_image: bool = False):
        """
        Text-based search for places (Semantic).
        Uses 'text_vec' (BGE-M3) in PLACES_COLLECTION.
        """
        print(f"[INFO] search_text (Semantic) start query='{query[:80]}' limit={limit} category={category} has_image={has_image}")
        query_vec = self.text_model.encode(query).astype(np.float32)
        
        query_filter = self._build_category_filter(category, has_image)

        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        print(f"[INFO] search_text hits={len(response.points)}")
        return response.points

    def search_text_to_image(self, query: str, limit: int = 5, category: Any = None):
        """
        Text-to-Image cross-modal search.
        Uses CLIP Text Encoder to find images in 'img_vec_agg'.
        """
        print(f"[INFO] search_text_to_image (Cross-modal) start query='{query[:80]}'")
        # Using CLIP to encode text for image matching
        query_vec = self.vision_model.encode(query).astype(np.float32)
        
        query_filter = self._build_category_filter(category)

        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            using="img_vec_agg",
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        return response.points

    async def search_image(self, image_url: str, limit: int = 5, group_size: int = 3, category: Any = None):
        """
        Image-based search (Visual Similarity).
        Uses CLIP Vision Encoder on PHOTOS_COLLECTION.
        """
        print(f"[INFO] search_image (Visual) start image_url='{str(image_url)[:120]}'")
        
        img = await asyncio.to_thread(download_image, image_url)
        if img is None:
            return []

        query_vec = await asyncio.to_thread(self.vision_model.encode, img)
        query_vec = np.asarray(query_vec, dtype=np.float32)
        query_filter = self._build_category_filter(category)

        response = await asyncio.to_thread(
            self.client.query_points_groups,
            collection_name=PHOTOS_COLLECTION,
            query=query_vec.tolist(),
            group_by="contentid",
            group_size=group_size,
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        return response.groups

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[가-힣A-Za-z0-9]+", text or "")

    def _bm25_like_score(self, query: str, payload: dict) -> float:
        tokens = self._tokenize(query)
        if not tokens:
            return 0.0
        doc_text = _build_compact_text(payload)
        doc_tokens = self._tokenize(doc_text)
        if not doc_tokens:
            return 0.0

        freq = {}
        for tok in doc_tokens:
            freq[tok] = freq.get(tok, 0) + 1

        k1 = 1.2
        b = 0.75
        avgdl = 120.0
        doc_len = len(doc_tokens)
        score = 0.0
        for t in tokens:
            tf = freq.get(t, 0)
            if tf <= 0:
                continue
            denom = tf + k1 * (1 - b + b * (doc_len / avgdl))
            score += ((k1 + 1) * tf) / denom
        return float(1 - math.exp(-score))

    def _payload_matches_category(self, payload: dict, normalized_category: Any) -> bool:
        category_values = self._get_category_candidates(normalized_category)
        if not category_values:
            return True
        payload_values = {
            str(payload.get("contenttypeid") or "").strip(),
            str(payload.get("category") or "").strip(),
        }
        payload_values.discard("")
        return any(value in payload_values for value in category_values)

    def _keyword_match_bonus(self, query: str, payload: dict) -> float:
        if not query or not payload:
            return 0.0

        title = str(payload.get("title") or payload.get("name") or "")
        addr = str(payload.get("addr") or payload.get("address") or payload.get("road_address") or "")
        if not title and not addr:
            return 0.0

        query_norm = _normalize_match_text(query)
        title_norm = _normalize_match_text(title)
        bonus = 0.0

        if title_norm:
            if len(title_norm) >= 3 and title_norm in query_norm:
                bonus += 0.18
            else:
                # 제목 토큰이 2개 이상 질의에 겹치면 소폭 부스트
                query_tokens = set(self._tokenize(query))
                title_tokens = {t for t in self._tokenize(title) if len(t) >= 2}
                overlap = len(query_tokens & title_tokens)
                if overlap > 0:
                    bonus += min(0.12, 0.04 * overlap)

        # 질의 내 지역 토큰(예: 성북동, 강남구)이 주소에 있으면 소폭 부스트
        district_tokens = set(re.findall(r"[가-힣A-Za-z0-9]+(?:구|군|시|동|읍|면|리)", query))
        if district_tokens and addr:
            addr_norm = _normalize_match_text(addr)
            normalized_districts = {_normalize_match_text(tok) for tok in district_tokens}
            stemmed_districts = {_normalize_match_text(_district_stem(tok)) for tok in district_tokens}
            if any(tok and tok in addr_norm for tok in normalized_districts):
                bonus += 0.06
            elif any(stem and stem in addr_norm for stem in stemmed_districts):
                bonus += 0.06

        return min(0.25, bonus)

    def _payload_coordinates(self, payload: dict[str, Any]) -> tuple[float | None, float | None]:
        if not payload:
            return None, None

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

    def _location_text_bonus(self, preferred_location: str | None, payload: dict) -> float:
        if not preferred_location or not payload:
            return 0.0

        addr = str(payload.get("addr") or payload.get("address") or payload.get("road_address") or "")
        title = str(payload.get("title") or payload.get("name") or "")
        target_norm = _normalize_match_text(f"{addr} {title}")
        if not target_norm:
            return 0.0

        location_tokens = {t for t in self._tokenize(preferred_location) if len(t) >= 2}
        if not location_tokens:
            return 0.0

        hit_count = 0
        for token in location_tokens:
            token_norm = _normalize_match_text(token)
            if token_norm and token_norm in target_norm:
                hit_count += 1
                continue
            stem_norm = _normalize_match_text(_district_stem(token))
            if stem_norm and stem_norm in target_norm:
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

    async def _search_bm25_lexical(
        self,
        query: str,
        category: Any,
        candidate_points: list,
        candidate_k: int,
        pool_limit: int = BM25_POOL_LIMIT,
    ) -> list[dict]:
        normalized_category = self.normalize_category(category)

        scored = []
        for p in list(candidate_points)[: max(int(pool_limit or 0), 1)]:
            payload = p.payload or {}
            if not self._payload_matches_category(payload, normalized_category):
                continue
            lexical_score = self._bm25_like_score(query, payload)
            if lexical_score <= 0:
                continue
            scored.append(
                {
                    "id": _extract_place_id(p, PLACES_COLLECTION),
                    "payload": payload,
                    "score": lexical_score,
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:candidate_k]

    def _ensure_reranker(self):
        if self._reranker_load_attempted:
            return
        self._reranker_load_attempted = True
        try:

            self._reranker = CrossEncoder("BAAI/bge-reranker-base", device=DEVICE)
            print("[INFO] Reranker loaded: BAAI/bge-reranker-base")
        except Exception as e:
            self._reranker = None
            print(f"[WARN] Reranker unavailable: {e}")

    async def _rerank_candidates(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        self._ensure_reranker()
        if not self._reranker or not candidates:
            for idx, c in enumerate(candidates[:top_k], start=1):
                c["rerank_score"] = None
                c["final_rank"] = idx
            return candidates[:top_k]

        pairs = []
        for c in candidates:
            payload = c.get("payload", {})
            pairs.append((query, _build_compact_text(payload)))

        try:
            scores = await asyncio.to_thread(self._reranker.predict, pairs)
            for c, s in zip(candidates, scores):
                c["rerank_score"] = float(s)
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

    async def search_hybrid(
        self,
        query: str,
        image_url: str = None,
        limit: int = 5,
        category: Any = None,
        emotional_text: str = None,
        user_latitude: float | None = None,
        user_longitude: float | None = None,
        preferred_location: str | None = None,
        candidate_k: int | None = None,
        enable_bm25: bool = True,
        enable_rerank: bool = True,
        rerank_top_k: int | None = None,
        search_scope: str = "auto",
    ):
        """
        Refined Hybrid search combining Text (BGE-M3) and Image (CLIP-L) with Place-ID Fusion.
        1. Text Input -> BGE-M3 (Text DB) + CLIP Text (Image DB)
        2. Image Input -> CLIP Vision (Image DB) + Emotional Extraction (Text DB)
        """
        scope = (search_scope or "auto").strip().lower()
        if scope not in {"auto", "place_only", "photo_only"}:
            scope = "auto"
        print(
            f"[INFO] search_hybrid start query='{query[:80]}' has_image={'yes' if image_url else 'no'} "
            f"scope={scope}"
        )
        
        defaults = get_retrieval_params()
        query_filter = self._build_category_filter(category)
        candidate_k = max(int(candidate_k or defaults["candidate_k"]), int(limit or 0), 1)
        rerank_top_k = min(
            max(int(rerank_top_k or defaults["top_k"]), int(limit or 0), 1),
            min(defaults["rerank_max_k"], candidate_k),
        )
        candidates_limit = max(candidate_k * 5, 30)
        score_map = {}  # place_id -> {score, payload, matches}
        place_vector_points = []
        rrf_k = 60

        def collect_hits(hits, weight, match_type, source_collection):
            for rank, h in enumerate(hits, start=1):
                pid = _extract_place_id(h, source_collection)
                if pid is None:
                    continue

                if pid not in score_map:
                    score_map[pid] = {"score": 0.0, "payload": h.payload or {}, "matches": set()}
                elif source_collection == PLACES_COLLECTION and h.payload:
                    # photos 채널 payload보다 places payload를 우선 사용
                    score_map[pid]["payload"] = h.payload

                # 채널 간 점수 분포 차이를 줄이기 위해 RRF로 rank 기반 결합
                score_map[pid]["score"] += weight * (1.0 / (rrf_k + rank))
                score_map[pid]["matches"].add(match_type)

        # --- A. Text Search Channel ---
        if query and query.strip() and scope in {"auto", "place_only"}:
            # 1. Scenario: Semantic Text Search (BGE-M3)
            text_emb = await asyncio.to_thread(self.text_model.encode, query)
            text_emb = np.asarray(text_emb, dtype=np.float32)
            t_t_resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PLACES_COLLECTION,
                query=text_emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=query_filter,
            )
            place_vector_points.extend(t_t_resp.points)
            print(f"[INFO] text_semantic hits={len(t_t_resp.points)} (filter={'yes' if query_filter else 'no'})")
            collect_hits(t_t_resp.points, 1.0, "text_semantic", PLACES_COLLECTION)

        if query and query.strip() and scope in {"auto", "photo_only"}:
            # 2. Scenario: Cross-modal Text-to-Image (CLIP Text)
            clip_text_emb = await asyncio.to_thread(self.vision_model.encode, query)
            clip_text_emb = np.asarray(clip_text_emb, dtype=np.float32)
            t_i_resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PHOTOS_COLLECTION,
                query=clip_text_emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=query_filter,
            )
            collect_hits(t_i_resp.points, 0.5, "text_to_image", PHOTOS_COLLECTION)

        # --- B. Image Search Channel ---
        if image_url and scope in {"auto", "photo_only"}:
            img = await asyncio.to_thread(download_image, image_url)
            if img:
                # 3. Scenario: Visual Similarity (CLIP Vision)
                img_emb = await asyncio.to_thread(self.vision_model.encode, img)
                img_emb = np.asarray(img_emb, dtype=np.float32)
                i_i_resp = await asyncio.to_thread(
                    self.client.query_points,
                    collection_name=PHOTOS_COLLECTION,
                    query=img_emb.tolist(),
                    limit=candidates_limit,
                    with_payload=True,
                    query_filter=query_filter,
                )
                collect_hits(i_i_resp.points, 1.0, "image_visual", PHOTOS_COLLECTION)

        if image_url and scope == "auto":
            # 4. Scenario: Emotional Enrichment (GPT-4o-mini -> BGE-M3)
            if not emotional_text:
                emotional_text = await describe_image(image_url)

            if emotional_text:
                emo_emb = await asyncio.to_thread(self.text_model.encode, emotional_text)
                emo_emb = np.asarray(emo_emb, dtype=np.float32)
                i_e_resp = await asyncio.to_thread(
                    self.client.query_points,
                    collection_name=PLACES_COLLECTION,
                    query=emo_emb.tolist(),
                    limit=candidates_limit,
                    with_payload=True,
                    query_filter=query_filter,
                )
                place_vector_points.extend(i_e_resp.points)
                collect_hits(i_e_resp.points, 0.8, "image_emotional", PLACES_COLLECTION)

        if enable_bm25 and query and query.strip() and scope in {"auto", "place_only"}:
            try:
                unique_points = {}
                for point in place_vector_points:
                    pid = point.id
                    if pid is None:
                        continue
                    unique_points[pid] = point

                point_pool = list(unique_points.values())
                top_vector_score = 0.0
                if point_pool:
                    try:
                        top_vector_score = max(float(getattr(p, "score", 0.0) or 0.0) for p in point_pool)
                    except Exception:
                        top_vector_score = 0.0

                bm25_needed = (
                    len(point_pool) < BM25_ENABLE_THRESHOLD
                    or top_vector_score < BM25_ENABLE_SCORE_THRESHOLD
                )

                if bm25_needed and point_pool:
                    lexical_hits = await self._search_bm25_lexical(
                        query=query,
                        category=category,
                        candidate_points=point_pool,
                        candidate_k=candidates_limit,
                        pool_limit=BM25_POOL_LIMIT,
                    )
                    for rank, item in enumerate(lexical_hits, start=1):
                        pid = _to_positive_int(item.get("id"))
                        if pid is None:
                            continue
                        payload = item.get("payload") or {}
                        if pid not in score_map:
                            score_map[pid] = {"score": 0.0, "payload": payload, "matches": set()}
                        elif payload and not score_map[pid].get("payload"):
                            score_map[pid]["payload"] = payload
                        score_map[pid]["score"] += 0.7 * (1.0 / (rrf_k + rank))
                        score_map[pid]["matches"].add("bm25_lexical")
                else:
                    print(
                        f"[INFO] bm25 skipped vector_pool={len(point_pool)} "
                        f"top_vector_score={top_vector_score:.4f}"
                    )
            except Exception as e:
                print(f"[WARN] bm25 lexical channel failed: {e}")

        # --- C. Fusion & Boosting ---
        results = []
        fused = []
        for pid, data in score_map.items():
            payload = data.get("payload") or {}
            keyword_boost = self._keyword_match_bonus(query=query or "", payload=payload)
            location_text_boost = self._location_text_bonus(preferred_location=preferred_location, payload=payload)
            geo_proximity_boost = self._geo_proximity_bonus(
                payload=payload,
                anchor_lat=user_latitude,
                anchor_lng=user_longitude,
            )
            boost = keyword_boost + location_text_boost + geo_proximity_boost
            fused.append(
                (
                    pid,
                    data,
                    float(data.get("score", 0.0)) + boost,
                    {
                        "keyword": keyword_boost,
                        "location_text": location_text_boost,
                        "geo_proximity": geo_proximity_boost,
                        "total": boost,
                    },
                )
            )

        fused.sort(key=lambda x: x[2], reverse=True)
        for idx, (pid, data, final_score, boost_detail) in enumerate(fused, start=1):
            results.append({
                "id": pid,
                "score": final_score,
                "first_stage_score": data["score"],
                "first_stage_rank": idx,
                "payload": data["payload"],
                "match_types": sorted(list(data["matches"])),
                "keyword_match_boost": boost_detail["keyword"],
                "location_text_boost": boost_detail["location_text"],
                "geo_proximity_boost": boost_detail["geo_proximity"],
                "score_boost_total": boost_detail["total"],
            })

        print(f"[INFO] fusion & boosting returning {len(results)} candidates")

        first_stage_results = results[:candidate_k]
        if enable_rerank:
            reranked = await self._rerank_candidates(query=query, candidates=first_stage_results, top_k=min(rerank_top_k, candidate_k))
        else:
            reranked = first_stage_results[: min(rerank_top_k, candidate_k)]
            for idx, c in enumerate(reranked, start=1):
                c["rerank_score"] = None
                c["final_rank"] = idx

        # 기존 인터페이스 호환: limit 기준으로 반환
        final = reranked[: max(int(limit or 0), 1)]
        print(f"[INFO] search_hybrid returning {len(final)} candidates (score_map={len(score_map)} reranked={len(reranked)})")
        return final
        
    def search_nearby(self, lat: float, lng: float, limit: int = 5, radius_km: float = 10.0):
        """
        Search for places near a specific coordinate.
        Since we don't have a Geo Index yet, we will fetch all (or many) and filter/sort in Python.
        For 177 items, this is efficient enough.
        """
        print(f"[INFO] search_nearby start lat={lat} lng={lng} limit={limit} radius_km={radius_km}")
        # Fetch all places (scroll) - optimize this if data grows!
        # For now, we scroll to get all points to calculate distance
        all_points = []
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=PLACES_COLLECTION,
                limit=100,
                with_payload=True,
                offset=offset,
                with_vectors=False
            )
            all_points.extend(points)
            if offset is None:
                break
        print(f"[DEBUG] search_nearby total_points_scrolled={len(all_points)}")
        
        # Calculate distance and filter
        results = []
        for p in all_points:
            try:
                p_lat = float(p.payload.get("lat", 0))
                p_lng = float(p.payload.get("lng", 0))
            except (ValueError, TypeError):
                p_lat, p_lng = 0.0, 0.0
            
            if p_lat == 0 and p_lng == 0:
                continue
                
            dist = self._haversine(lat, lng, p_lat, p_lng)
            # radius 반경 내에 있는 장소만 추가
            if dist <= radius_km:
                results.append({
                    "id": p.id,
                    "payload": p.payload,
                    "score": 1.0 / (dist + 0.1), # Score inversely proportional to distance
                    "distance_km": dist
                })
        
        # 거리가 가까운 순서대로 정렬
        results.sort(key=lambda x: x["distance_km"])
        trimmed = results[:limit]
        print(f"[INFO] search_nearby matched={len(results)} returned={len(trimmed)}")
        return trimmed

    def _haversine(self, lat1, lon1, lat2, lon2):
        """
        두 지점 간의 거리를 계산합니다.
        """
        import math
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) * math.sin(dlon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = R * c
        return d


async def retrieval_place(message_in: ChatMessageCreate):
    # Retrieval (Search Places)
    context_str = None
    search_results = []
    nearby_places = []
    try:        
        print(
            f"[INFO] retrieval_place start message_len={len(message_in.message or '')} "
            f"has_image={'yes' if message_in.image_path else 'no'}"
        )
        # Instantiate retriever (In production, use dependency injection or singleton)
        # Note: This loads the model every time if not cached. 
        # For better performance, move instantiation outside or use lru_cache
        retriever = PlaceRetriever.get_instance() 

        user_lat = message_in.latitude
        user_long = message_in.longitude
        address = ''
        if user_lat and user_long:
            # Instantiate geocoder on demand
            geocoder_client = GeoCoder()
            geocode_data = geocoder_client.reverse_geocoder(user_lat, user_long)
            if geocode_data:
                road_address = (geocode_data.get("road_address") or "").strip()
                jibun_address = (geocode_data.get("jibun_address") or "").strip()
                address = " ".join(part for part in [road_address, jibun_address] if part).strip()
                print(f"[DEBUG] retrieval_place reverse_geocoded address='{address}'")
            else:
                print("[WARN] retrieval_place reverse geocoder returned no address")
        
        query = message_in.message
        if len(address) > 0:
            query += f'\n## location : ({user_lat}, {user_long}), address : {address}'
        # Main Search (Hybrid)
        search_results = await retriever.search_hybrid(
            query=query,
            image_url=message_in.image_path,
            limit=5,
            user_latitude=user_lat,
            user_longitude=user_long,
        )
        print(f"[INFO] retrieval_place search_results_count={len(search_results) if search_results else 0}")
        
        formatted_results = []
        search_ids = []
        photo_url_map = {}
        if search_results:
            photo_url_map = await _fetch_photo_urls_by_contentids(
                retriever=retriever,
                content_ids=[res.get("id") for res in search_results],
                per_place=3,
            )

        if search_results:            
            formatted_results.append(f"### 🔎 Search Results (Hybrid Fusion)")
            for i, res in enumerate(search_results):
                payload = res.get('payload', {})
                rid = res.get('id')
                score = res.get('score')
                matches = res.get('match_types', [])
                
                search_ids.append(rid)

                title = payload.get('title', 'Unknown')
                category = payload.get('category', 'Unknown')
                desc = payload.get('description', '')
                addr = payload.get('address', '')
                emo_desc = payload.get('emotional_description', '')
                photo_urls = photo_url_map.get(str(rid), [])

                print(f"[DEBUG] retrieval_place result[{i}] id={rid} title='{title}' matches={matches}")
                match_str = ", ".join(matches)
                formatted_results.append(
                    f"{i+1}. **{title}** ({category})\n"
                    f"   - Match Reasons: {match_str}\n"
                    f"   - Address: {addr}\n"
                    f"   - Emotional Context: {emo_desc if emo_desc else 'N/A'}\n"
                    f"   - Description: {desc[:200]}...\n"
                    f"   - Photos: {', '.join(photo_urls[:3]) if photo_urls else 'No photos found'}"
                )
        else:
            print("[WARN] retrieval_place no search results")

        # Nearby Search (if best match found and has coordinates)
        if user_lat and user_long:
            lat = user_lat
            lng = user_long
            print(f"[DEBUG] retrieval_place best_place coords lat={lat} lng={lng}")
            
            if lat != 0 and lng != 0:
                nearby_places = retriever.search_nearby(lat, lng, limit=3, radius_km=5.0)
                if nearby_places:
                    formatted_results.append("\n### 📍 Nearby Recommendations (near 첨부한 위치)")
                    for i, res in enumerate(nearby_places):
                        # Filter out the place itself if needed, but Qdrant might return it. Use ID check.
                        if res['id'] in search_ids:
                            print(f"[DEBUG] retrieval_place skip nearby self id={res['id']}")
                            continue
                            
                        payload = res.get('payload', {})
                        title = payload.get('title', 'Unknown')
                        dist = res.get('distance_km', 0)
                        print(f"[DEBUG] retrieval_place nearby[{i}] id={res['id']} title='{title}' dist={dist:.3f}km")
                        formatted_results.append(f"- **{title}** ({dist:.1f}km away) - {payload.get('category')}")
                else:
                    print("[INFO] retrieval_place nearby search returned 0")
            else:
                print("[INFO] retrieval_place skip nearby (missing coordinates)")

        if formatted_results:
            context_str = "\n".join(formatted_results)
            print(f"[INFO] Context Reference:\n{context_str}")
        else:
            print("[INFO] retrieval_place no formatted context generated")
            
    except Exception as e:
        print(f"[ERROR] Retrieval failed: {e}")
        context_str = None

    print(f"[INFO] retrieval_place done context_exists={'yes' if context_str else 'no'}")
    
    # Collect all results for the agent
    all_results = []
    if search_results:
        all_results.extend(search_results)
    if 'nearby_places' in locals() and nearby_places:
        all_results.extend(nearby_places)
        
    return context_str, all_results


async def _fetch_photo_urls_by_contentids(
    retriever: PlaceRetriever,
    content_ids: list,
    per_place: int = 3,
    scroll_limit: int = 200,
) -> dict[str, list[str]]:
    wanted_ids = {str(cid) for cid in content_ids if cid is not None}
    if not wanted_ids:
        return {}

    should_conditions = [
        FieldCondition(key="contentid", match=MatchValue(value=cid))
        for cid in wanted_ids
    ]
    scroll_filter = Filter(should=should_conditions)

    photo_map = {cid: [] for cid in wanted_ids}
    offset = None

    while True:
        points, offset = await asyncio.to_thread(
            retriever.client.scroll,
            collection_name=PHOTOS_COLLECTION,
            scroll_filter=scroll_filter,
            limit=scroll_limit,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )

        for point in points:
            payload = point.payload or {}
            cid = str(payload.get("contentid", "")).strip()
            if not cid or cid not in wanted_ids:
                continue

            url = payload.get("image_url") or payload.get("image")
            if not url:
                continue

            current_urls = photo_map[cid]
            if url not in current_urls and len(current_urls) < per_place:
                current_urls.append(url)

        if offset is None:
            break

        if all(len(photo_map[cid]) >= per_place for cid in wanted_ids):
            break

    return photo_map
