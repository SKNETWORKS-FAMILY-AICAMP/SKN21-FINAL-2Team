import os
import time
import numpy as np
import asyncio

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, MatchAny, SparseVector,
    GeoBoundingBox, GeoPoint,
)
from sentence_transformers import SentenceTransformer

from app.utils.config import (
    PLACES_COLLECTION, PHOTOS_COLLECTION, DEVICE,
    TEXT_MODEL, VISION_MODEL, TEXT_VECTOR_SIZE, VISION_VECTOR_SIZE,
    ENABLE_ADDR_SPARSE_BOOST, ENABLE_GEO_FILTER,
    ENABLE_QDRANT_SPARSE, ENABLE_RERANKER,
    BOOST_WEIGHT,
    CANDIDATE_LIMIT_MULTIPLIER,
    GEO_PROXIMITY_RADIUS_KM,
    MAX_DISTANCE_KM, GEO_RETRY_MULTIPLIER,
    RRF_SCORE_MAX, FUSED_SCORE_MAX, MAX_BOOST_SUM,
    RERANK_GEO_BLEND_WEIGHT, GEO_MAX_BOOST,
    get_retrieval_params,
)
from app.scripts.preprocess_data import download_image, build_sparse_vector
from app.utils.common import dprint
from app.utils.vision import describe_image
from app.core.retrieval.place_score import PlaceScorer, _extract_place_id, _to_positive_int
from app.agents.models.output import CategoryType


class PlaceRetriever(PlaceScorer):
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            dprint("[INFO] Initializing PlaceRetriever (Singleton)...")
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        host = os.getenv('QDRANT_HOST', "localhost")
        port = os.getenv('QDRANT_PORT', 6333)
        dprint(f"[INFO] Connecting to Qdrant at {host}:{port}")
        self.client = QdrantClient(host=host, port=port)

        dprint(f"[INFO] Loading models: Text={TEXT_MODEL}, Vision={VISION_MODEL}")
        self.text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)
        self.vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)
        self._reranker = None
        self._reranker_load_attempted = False

        dprint(f"[INFO] PlaceRetriever ready on {DEVICE}")

    # 관광지 ↔ 투어는 사용자 입장에서 겹치는 개념이므로 항상 함께 검색한다.
    _CATEGORY_SYNONYMS: dict[str, list[str]] = {
        CategoryType.TOURIST_ATTRACTION.value: [CategoryType.TOUR.value],
        CategoryType.TOUR.value: [CategoryType.TOURIST_ATTRACTION.value],
    }

    def _resolve_category_values(self, categories: list[CategoryType] | None, strict: bool = False) -> list[str]:
        """LLM 추출 카테고리 → DB contenttypeid 값으로 변환.

        DB 실존 값: 음식점, 관광지, 숙박, 콘텐츠, 투어
        관광지/투어는 동의어 처리: 어느 쪽이든 포함되면 양쪽 모두 MatchAny에 추가.
        strict=True 이면 동의어 확장을 생략하고 입력 카테고리만 사용한다.
        """
        if not categories:
            return []
        values: set[str] = {cat.value for cat in categories}
        if not strict:
            for v in list(values):
                for synonym in self._CATEGORY_SYNONYMS.get(v, []):
                    values.add(synonym)
        return list(values)

    def _merge_geo_bboxes(
        self,
        gps_bbox: tuple[float, float, float, float],
        anchor_bbox: tuple[float, float, float, float],
    ) -> tuple[tuple[float, float, float, float], str]:
        """GPS와 anchor bbox를 보수적으로 병합한다.

        - 겹치면 교집합 사용
        - 겹치지 않으면 사용자가 명시한 anchor bbox 우선
        """
        min_lat = max(gps_bbox[0], anchor_bbox[0])
        max_lat = min(gps_bbox[1], anchor_bbox[1])
        min_lng = max(gps_bbox[2], anchor_bbox[2])
        max_lng = min(gps_bbox[3], anchor_bbox[3])

        if min_lat <= max_lat and min_lng <= max_lng:
            return (min_lat, max_lat, min_lng, max_lng), "intersection"
        return anchor_bbox, "anchor_only"

    def _filter_candidates_by_distance(
        self,
        candidates: list[dict],
        anchor_lat: float | None,
        anchor_lon: float | None,
        max_distance_km: float,
    ) -> list[dict]:
        """기준 좌표에서 너무 먼 후보를 최종 단계에서 제거한다."""
        if anchor_lat in (None, 0, 0.0) or anchor_lon in (None, 0, 0.0):
            return candidates

        filtered: list[dict] = []
        for candidate in candidates:
            payload = candidate.get("payload") or {}
            point_lat, point_lng = self._payload_coordinates(payload)
            if point_lat is None or point_lng is None:
                continue

            distance_km = self._haversine(float(anchor_lat), float(anchor_lon), point_lat, point_lng)
            candidate["distance_km"] = round(distance_km, 3)
            if distance_km <= max_distance_km:
                filtered.append(candidate)

        return filtered

    def _build_query_filter(
        self,
        categories: list[CategoryType] = None,
        has_image: bool = False,
        anchor_lat: float | None = None,
        anchor_lon: float | None = None,
        radius_m: float | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        strict_category: bool = False,
    ) -> Filter | None:
        """카테고리, 이미지 유무, Geo 조건을 합성한 Qdrant 필터 생성.

        - category / has_image: PLACES_COLLECTION, PHOTOS_COLLECTION 공용
        - bbox (min_lat, max_lat, min_lng, max_lng): union bounding box geo filter (우선)
        - anchor_lat/lon/radius_m: circle geo filter (bbox 없을 때 사용)
        """
        must_conditions = []
        must_not_conditions = []
        # fallback 포함 DB 실존값으로 변환 (예: "문화시설" → ["관광지"])
        category_values = self._resolve_category_values(categories, strict=strict_category)

        if category_values:
            if len(category_values) >= 2:
                dprint(f"[INFO] category candidates built: {category_values}")
            must_conditions.append(
                FieldCondition(key="contenttypeid", match=MatchAny(any=category_values))
            )

        if has_image:
            from qdrant_client.models import IsEmptyCondition, PayloadField
            must_not_conditions.append(IsEmptyCondition(is_empty=PayloadField(key="image")))

        if bbox is not None:
            min_lat, max_lat, min_lng, max_lng = bbox
            must_conditions.append(
                FieldCondition(
                    key="geo",
                    geo_bounding_box=GeoBoundingBox(
                        top_left=GeoPoint(lat=float(max_lat), lon=float(min_lng)),
                        bottom_right=GeoPoint(lat=float(min_lat), lon=float(max_lng)),
                    ),
                )
            )
            # print(f"[INFO] geo bbox filter: lat=[{min_lat:.4f},{max_lat:.4f}] lng=[{min_lng:.4f},{max_lng:.4f}]")
        elif anchor_lat is not None and anchor_lon is not None and radius_m is not None:
            must_conditions.append(
                FieldCondition(
                    key="geo",
                    geo_radius={
                        "center": {"lat": float(anchor_lat), "lon": float(anchor_lon)},
                        "radius": float(radius_m),
                    },
                )
            )
            # print(f"[INFO] geo circle filter: lat={anchor_lat} lon={anchor_lon} radius_m={radius_m}")

        if not must_conditions and not must_not_conditions:
            return None

        built = Filter(
            must=must_conditions if must_conditions else None,
            must_not=must_not_conditions if must_not_conditions else None,
        )
        dprint(f"[INFO] query_filter built: category={categories} values={category_values} geo={'bbox' if bbox else 'circle' if anchor_lat else 'no'}")
        return built

    def search_by_vector(
        self,
        query_vec: np.ndarray,
        limit: int = 5,
        categories: list[CategoryType] = None,
        has_image: bool = False,
    ):
        """
        Vector-based search for places (pre-encoded).
        Accepts an already-encoded numpy vector to avoid redundant encoding.
        strict_category=True (기본값): 관광지↔투어 동의어 확장 없이 입력 카테고리만 사용.
        """
        query_filter = self._build_query_filter(categories, has_image, strict_category=True)

        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        dprint(f"[INFO] search_by_vector hits={len(response.points)}")
        return response.points

    async def search_hybrid(
        self,
        query: str,
        image_url: str = None,
        limit: int = 5,
        categories: list[CategoryType] = None,
        emotional_text: str = None,
        user_latitude: float | None = None,
        user_lon: float | None = None,
        preferred_location: str | None = None,
        candidate_k: int | None = None,
        enable_rerank: bool = True,
        rerank_top_k: int | None = None,
        search_scope: str = "auto",
        location_anchor_lat: float | None = None,
        location_anchor_lon: float | None = None,
        location_radius_m: float | None = None,
        geo_retry_count: int = 0,
        input_tags: list[str] | None = None,
    ):
        """
        Refined Hybrid search combining Text (BGE-M3) and Image (CLIP-L) with Place-ID Fusion.
        1. Text Input -> BGE-M3 (Text DB) + CLIP Text (Image DB)
        2. Image Input -> CLIP Vision (Image DB) + Emotional Extraction (Text DB)
        """
        scope = (search_scope or "auto").strip().lower()
        if scope not in {"auto", "place_only", "photo_only"}:
            scope = "auto"
        _hybrid_start = time.perf_counter()
        dprint(
            f"[TIMING] search_hybrid START query='{query[:80]}' has_image={'yes' if image_url else 'no'} "
            f"scope={scope}"
        )

        defaults = get_retrieval_params()

        # geo filter는 PLACES_COLLECTION 전용. PHOTOS_COLLECTION에는 geo 필드가 없으므로 분리.
        # 두 좌표가 모두 있으면 union bounding box, 하나만 있으면 circle filter 사용.
        import math as _math

        def _km_to_bbox(lat, lng, r_km):
            """중심 좌표 + 반경(km)을 위경도 bbox (min_lat, max_lat, min_lng, max_lng)로 변환."""
            r_lat = r_km / 111.0
            r_lng = r_km / (111.0 * _math.cos(_math.radians(lat)))
            return lat - r_lat, lat + r_lat, lng - r_lng, lng + r_lng

        geo_bbox = None
        apply_geo = ENABLE_GEO_FILTER
        has_gps = (
            user_latitude is not None and user_lon is not None
            and not (abs(user_latitude) < 1e-6 and abs(user_lon) < 1e-6)
        )
        has_anchor = (
            location_anchor_lat is not None
            and location_anchor_lon is not None
            and location_radius_m is not None
        )

        if apply_geo and has_gps and has_anchor:
            # 두 좌표 모두 있을 때: 과도한 확장을 막기 위해 교집합 우선, 미겹치면 anchor 우선
            expanded_radius_km = MAX_DISTANCE_KM * (GEO_RETRY_MULTIPLIER if geo_retry_count > 0 else 1.0)
            expanded_anchor_km = (location_radius_m / 1000.0) * (GEO_RETRY_MULTIPLIER if geo_retry_count > 0 else 1.0)
            gps_bbox = _km_to_bbox(user_latitude, user_lon, expanded_radius_km)
            anchor_bbox = _km_to_bbox(location_anchor_lat, location_anchor_lon, expanded_anchor_km)
            geo_bbox, geo_bbox_mode = self._merge_geo_bboxes(gps_bbox, anchor_bbox)
            dprint(f"[INFO] combined bbox from GPS+anchor ({geo_bbox_mode}): {geo_bbox}")
        elif apply_geo and has_gps:
            # GPS만 있을 때: GPS 기준 bbox
            expanded_radius_km = MAX_DISTANCE_KM * (GEO_RETRY_MULTIPLIER if geo_retry_count > 0 else 1.0)
            geo_bbox = _km_to_bbox(user_latitude, user_lon, expanded_radius_km)
            dprint(f"[INFO] GPS-only bbox: {geo_bbox}")

        expanded_radius_m = (location_radius_m * (GEO_RETRY_MULTIPLIER if geo_retry_count > 0 else 1.0)) if location_radius_m else None
        
        places_filter = self._build_query_filter(
            categories,
            anchor_lat=location_anchor_lat if (apply_geo and has_anchor and not has_gps) else None,
            anchor_lon=location_anchor_lon if (apply_geo and has_anchor and not has_gps) else None,
            radius_m=expanded_radius_m if (apply_geo and has_anchor and not has_gps) else None,
            bbox=geo_bbox,
        )
        photos_filter = self._build_query_filter(categories)  # geo 없이 category만

        candidate_k = max(int(candidate_k or defaults["candidate_k"]), int(limit or 0), 1)
        rerank_top_k = min(
            max(int(rerank_top_k or defaults["top_k"]), int(limit or 0), 1),
            min(defaults["rerank_max_k"], candidate_k),
        )
        # 채널별 Qdrant fetch 상한. *CANDIDATE_LIMIT_MULTIPLIER(기본 3)으로 축소.
        # 채널 수(최대 4)를 감안해도 candidate_k*3이면 RRF 융합에 충분한 pool 확보 가능.
        candidates_limit = max(candidate_k * CANDIDATE_LIMIT_MULTIPLIER, 20)
        score_map = {}  # place_id -> {score, payload, matches}
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

        # --- 검색 채널 병렬 실행 ---
        has_text = bool(query and query.strip())

        async def _ch_text_semantic():
            if not (has_text and scope in {"auto", "place_only"}):
                return None
            t0 = time.perf_counter()
            emb = np.asarray(await asyncio.to_thread(self.text_model.encode, query), dtype=np.float32)
            t1 = time.perf_counter()
            resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PLACES_COLLECTION,
                query=emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=places_filter,
            )
            t2 = time.perf_counter()
            dprint(f"[TIMING] text_semantic  encode={t1-t0:.3f}s  qdrant={t2-t1:.3f}s  hits={len(resp.points)} (filter={'yes' if places_filter else 'no'} geo={apply_geo})")
            return ("text_semantic", PLACES_COLLECTION, resp.points, 1.0, None)

        async def _ch_sparse():
            if not (ENABLE_QDRANT_SPARSE and has_text and scope in {"auto", "place_only"}):
                return None
            try:
                t0 = time.perf_counter()
                sparse_indices, sparse_values = await asyncio.to_thread(build_sparse_vector, query)
                if not sparse_indices or not sparse_values:
                    return None
                t1 = time.perf_counter()
                resp = await asyncio.to_thread(
                    self.client.query_points,
                    collection_name=PLACES_COLLECTION,
                    query=SparseVector(indices=sparse_indices, values=sparse_values),
                    using="text_sparse",
                    limit=candidates_limit,
                    with_payload=True,
                    query_filter=places_filter,
                )
                t2 = time.perf_counter()
                dprint(f"[TIMING] qdrant_sparse  build={t1-t0:.3f}s  qdrant={t2-t1:.3f}s  hits={len(resp.points)}")
                return ("qdrant_sparse", PLACES_COLLECTION, resp.points, 0.85, None)
            except Exception as e:
                dprint(f"[WARN] qdrant sparse channel failed: {e}")
                return None

        async def _ch_text_to_image():
            if not (has_text and scope in {"auto", "photo_only"}):
                return None
            t0 = time.perf_counter()
            emb = np.asarray(await asyncio.to_thread(self.vision_model.encode, query), dtype=np.float32)
            t1 = time.perf_counter()
            resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PHOTOS_COLLECTION,
                query=emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=photos_filter,
            )
            t2 = time.perf_counter()
            dprint(f"[TIMING] text_to_image  encode={t1-t0:.3f}s  qdrant={t2-t1:.3f}s  hits={len(resp.points)}")
            return ("text_to_image", PHOTOS_COLLECTION, resp.points, 0.5, None)

        async def _ch_image_visual():
            if not (image_url and scope in {"auto", "photo_only"}):
                return None
            t0 = time.perf_counter()
            img = await asyncio.to_thread(download_image, image_url)
            if not img:
                return None
            t1 = time.perf_counter()
            emb = np.asarray(await asyncio.to_thread(self.vision_model.encode, img), dtype=np.float32)
            t2 = time.perf_counter()
            resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PHOTOS_COLLECTION,
                query=emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=photos_filter,
            )
            t3 = time.perf_counter()
            dprint(f"[TIMING] image_visual  download={t1-t0:.3f}s  encode={t2-t1:.3f}s  qdrant={t3-t2:.3f}s  hits={len(resp.points)}")
            return ("image_visual", PHOTOS_COLLECTION, resp.points, 1.0, None)

        async def _ch_image_emotional():
            if not (image_url and scope == "auto"):
                return None
            t0 = time.perf_counter()
            emo_text = emotional_text or await describe_image(image_url)
            if not emo_text:
                return None
            t1 = time.perf_counter()
            emb = np.asarray(await asyncio.to_thread(self.text_model.encode, emo_text), dtype=np.float32)
            t2 = time.perf_counter()
            resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PLACES_COLLECTION,
                query=emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=places_filter,
            )
            t3 = time.perf_counter()
            dprint(f"[TIMING] image_emotional  describe={t1-t0:.3f}s  encode={t2-t1:.3f}s  qdrant={t3-t2:.3f}s  hits={len(resp.points)}")
            return ("image_emotional", PLACES_COLLECTION, resp.points, 0.8, emo_text)

        _gather_start = time.perf_counter()
        channel_outputs = await asyncio.gather(
            _ch_text_semantic(),
            _ch_sparse(),
            _ch_text_to_image(),
            _ch_image_visual(),
            _ch_image_emotional(),
            return_exceptions=True,
        )
        dprint(f"[TIMING] gather total={time.perf_counter()-_gather_start:.3f}s")

        for output in channel_outputs:
            if output is None:
                continue
            if isinstance(output, BaseException):
                dprint(f"[WARN] channel exception: {output}")
                continue
            match_type, source_col, hits, weight, extra = output
            if match_type == "image_emotional" and extra:
                emotional_text = extra
            collect_hits(hits, weight, match_type, source_col)

        # --- geo filter 0결과 ---
        # geo_retry_count > 0 (이미 확장 반경)인데도 후보가 없으면 빈 결과 반환.
        # geo_retry_count == 0 (초회)이면 그래프 레벨에서 retriever 노드를 재실행하며
        # geo_retry_count=1 을 전달해 확장 반경 검색을 수행한다.
        if apply_geo and not score_map:
            radius_info = (
                f"anchor_lat={location_anchor_lat} anchor_lon={location_anchor_lon} "
                f"anchor_radius_m={location_radius_m} gps_radius_km={MAX_DISTANCE_KM} "
                f"geo_retry_count={geo_retry_count}"
            )
            if geo_retry_count == 0:
                dprint(
                    f"[INFO] search_hybrid: geo filter returned 0 candidates ({radius_info}). "
                    f"Returning empty — graph will retry with {GEO_RETRY_MULTIPLIER:.1f}x expanded radius."
                )
            else:
                dprint(
                    f"[INFO] search_hybrid: expanded geo filter still returned 0 candidates "
                    f"(expanded_by={GEO_RETRY_MULTIPLIER:.1f}x, {radius_info}). Returning empty."
                )
            return []

        # geo proximity 기준 좌표: 사용자 GPS 우선, 없으면 landmark anchor
        prox_lat = user_latitude if user_latitude else location_anchor_lat
        prox_lon = user_lon if user_lon else location_anchor_lon

        # --- B. Fusion & Boosting ---
        results = self._fuse_and_boost(
            score_map=score_map,
            query=query,
            preferred_location=preferred_location,
            categories=categories,
            input_tags=input_tags,
            prox_lat=prox_lat,
            prox_lon=prox_lon,
        )

        # --- C. Rerank ---
        reranked = await self._apply_rerank(
            first_stage_results=results[:candidate_k],
            enable_rerank=enable_rerank,
            rerank_top_k=rerank_top_k,
            candidate_k=candidate_k,
            query=query,
            emotional_text=emotional_text,
        )

        # --- D. Geo Blend & Distance Filter ---
        final_candidates = self._apply_geo_blend(
            reranked=reranked,
            prox_lat=prox_lat,
            prox_lon=prox_lon,
            geo_retry_count=geo_retry_count,
        )

        final = final_candidates[: max(int(limit or 0), 1)]
        dprint(f"[TIMING] search_hybrid DONE  total={time.perf_counter()-_hybrid_start:.3f}s  returned={len(final)}  score_map={len(score_map)}  reranked={len(reranked)}")
        return final


    # ------------------------------------------------------------------
    # search_hybrid 서브 메서드
    # ------------------------------------------------------------------

    def _fuse_and_boost(
        self,
        score_map: dict,
        query: str,
        preferred_location: str | None,
        categories: list[CategoryType] | None,
        input_tags: list[str] | None,
        prox_lat: float | None,
        prox_lon: float | None,
    ) -> list[dict]:
        """RRF score_map → 부스팅 적용 → min-max 정규화 → results 리스트 반환."""
        fused = []
        query_addr_tokens = self._extract_query_addr_tokens(query or "")
        sparse_enabled = ENABLE_ADDR_SPARSE_BOOST and (
            bool(categories) or bool(query_addr_tokens)
        )

        for pid, data in score_map.items():
            payload = data.get("payload") or {}
            keyword_boost = self._keyword_match_bonus(query=query or "", payload=payload, location_hint=preferred_location)
            location_text_boost = self._location_text_bonus(preferred_location=preferred_location, payload=payload)
            geo_proximity_boost = self._geo_proximity_bonus(
                payload=payload,
                anchor_lat=prox_lat,
                anchor_lon=prox_lon,
                radius_km=GEO_PROXIMITY_RADIUS_KM,
            )
            payload_addr_tokens = self._payload_addr_tokens(payload)
            addr_sparse_boost = 0.0
            if sparse_enabled:
                addr_sparse_boost = self._addr_sparse_bonus(
                    query_addr_tokens=query_addr_tokens,
                    payload_addr_tokens=payload_addr_tokens,
                )
                if addr_sparse_boost > 0.0:
                    data["matches"].add("addr_sparse")

            tag_boost = 0.0
            if input_tags:
                tag_boost = self._tag_match_bonus(input_tags=input_tags, payload=payload)
                if tag_boost > 0.0:
                    data["matches"].add("tag_match")

            boost = keyword_boost + location_text_boost + geo_proximity_boost + addr_sparse_boost + tag_boost
            fused.append((
                pid,
                data,
                float(data.get("score", 0.0)) + BOOST_WEIGHT * boost,
                {
                    "keyword": keyword_boost,
                    "location_text": location_text_boost,
                    "geo_proximity": geo_proximity_boost,
                    "addr_sparse": addr_sparse_boost,
                    "tag": tag_boost,
                    "total": boost,
                },
            ))

        fused.sort(key=lambda x: x[2], reverse=True)

        # min-max 정규화
        if fused:
            all_final = [x[2]          for x in fused]
            all_rrf   = [x[1]["score"] for x in fused]
            fused_max = all_final[0]; fused_min = all_final[-1]
            fused_range = max(fused_max - fused_min, 1e-9)
            rrf_max = max(all_rrf); rrf_min = min(all_rrf)
            rrf_range = max(rrf_max - rrf_min, 1e-9)
        else:
            fused_min = fused_range = rrf_min = rrf_range = 1.0

        results = []
        for idx, (pid, data, final_score, boost_detail) in enumerate(fused, start=1):
            results.append({
                "id": pid,
                "score":             round((final_score   - fused_min) / fused_range, 4),
                "first_stage_score": round((data["score"] - rrf_min)   / rrf_range,  4),
                "first_stage_rank": idx,
                "payload": data["payload"],
                "match_types": sorted(list(data["matches"])),
                "keyword_match_boost":  boost_detail["keyword"],
                "location_text_boost":  boost_detail["location_text"],
                "geo_proximity_boost":  boost_detail["geo_proximity"],
                "addr_sparse_boost":    boost_detail["addr_sparse"],
                "tag_match_boost":      boost_detail["tag"],
                "score_boost_total":    round(min(1.0, boost_detail["total"] / MAX_BOOST_SUM), 4),
            })

        dprint(f"[TIMING] fusion & boosting  candidates={len(results)}")
        return results

    async def _apply_rerank(
        self,
        first_stage_results: list[dict],
        enable_rerank: bool,
        rerank_top_k: int,
        candidate_k: int,
        query: str,
        emotional_text: str | None,
    ) -> list[dict]:
        """Reranker(CrossEncoder) 적용. ENABLE_RERANKER=False 또는 enable_rerank=False면 스킵."""
        _do_rerank = enable_rerank and ENABLE_RERANKER
        if _do_rerank:
            # 이미지 전용 검색(query="")일 때 emotional_text를 fallback으로 사용.
            rerank_query = (query or "").strip() or (emotional_text or "").strip()
            _rerank_start = time.perf_counter()
            reranked = await self._rerank_candidates(
                query=rerank_query,
                candidates=first_stage_results,
                top_k=min(rerank_top_k, candidate_k),
            )
            dprint(f"[TIMING] rerank  input={len(first_stage_results)}  top_k={min(rerank_top_k, candidate_k)}  elapsed={time.perf_counter()-_rerank_start:.3f}s")
        else:
            if not ENABLE_RERANKER:
                dprint("[INFO] reranker disabled by ENABLE_RERANKER=False")
            reranked = first_stage_results[: min(rerank_top_k, candidate_k)]
            for idx, c in enumerate(reranked, start=1):
                c["rerank_score"] = None
                c["final_rank"] = idx
        return reranked

    def _apply_geo_blend(
        self,
        reranked: list[dict],
        prox_lat: float | None,
        prox_lon: float | None,
        geo_retry_count: int = 0,
    ) -> list[dict]:
        """rerank 점수와 geo proximity boost를 블렌딩하고 거리 하드 필터를 적용한다.
        prox_lat/lon이 없으면 reranked를 그대로 반환.
        """
        if prox_lat is None or prox_lon is None:
            return reranked

        for c in reranked:
            rerank_score = c.get("rerank_score")
            raw_text = float(rerank_score) if rerank_score is not None else float(c.get("score", 0.0))
            raw_geo = float(c.get("geo_proximity_boost") or 0.0)
            normalized_geo = min(raw_geo / GEO_MAX_BOOST, 1.0)
            c["blended_score"] = (
                (1 - RERANK_GEO_BLEND_WEIGHT) * raw_text
                + RERANK_GEO_BLEND_WEIGHT * normalized_geo
            )
        reranked.sort(key=lambda x: float(x.get("blended_score", 0.0)), reverse=True)
        for idx, c in enumerate(reranked, start=1):
            c["final_rank"] = idx
        dprint(f"[INFO] geo-blended reranking applied (blend_weight={RERANK_GEO_BLEND_WEIGHT})")

        # 안전망: 블렌딩 후에도 너무 먼 장소가 남아 있을 경우 거리 하드 필터
        nearby_candidates = self._filter_candidates_by_distance(
            reranked,
            anchor_lat=prox_lat,
            anchor_lon=prox_lon,
            max_distance_km=MAX_DISTANCE_KM * (GEO_RETRY_MULTIPLIER if geo_retry_count > 0 else 1.0),
        )
        if nearby_candidates:
            return nearby_candidates
        dprint(
            f"[INFO] search_hybrid distance post-filter kept 0 candidates; "
            f"falling back to blended results (anchor=({prox_lat}, {prox_lon}))"
        )
        return reranked




