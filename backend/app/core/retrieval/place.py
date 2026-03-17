import os
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
    ENABLE_QDRANT_SPARSE,
    BOOST_WEIGHT,
    CANDIDATE_LIMIT_MULTIPLIER,
    GEO_PROXIMITY_RADIUS_KM,
    MAX_DISTANCE_KM, GEO_RETRY_MULTIPLIER,
    RRF_SCORE_MAX, FUSED_SCORE_MAX, MAX_BOOST_SUM,
    RERANK_GEO_BLEND_WEIGHT, GEO_MAX_BOOST,
    get_retrieval_params,
)
from app.scripts.preprocess_data import download_image, build_sparse_vector
from app.utils.geocoder import GeoCoder
from app.utils.vision import describe_image
from app.core.retrieval.place_score import PlaceScorer, _extract_place_id, _to_positive_int
from app.agents.models.output import CategoryType


class PlaceRetriever(PlaceScorer):
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            print("[INFO] Initializing PlaceRetriever (Singleton)...")
            cls._instance = cls()
        return cls._instance

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

    @staticmethod
    def _resolve_category_values(categories: list[CategoryType] | None) -> list[str]:
        """LLM 추출 카테고리 → DB contenttypeid 값으로 변환.

        DB 실존 값: 음식점, 관광지, 숙박, 콘텐츠, 투어
        """
        if not categories:
            return []
        return list({cat.value for cat in categories})

    @staticmethod
    def _merge_geo_bboxes(
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
    ) -> Filter | None:
        """카테고리, 이미지 유무, Geo 조건을 합성한 Qdrant 필터 생성.

        - category / has_image: PLACES_COLLECTION, PHOTOS_COLLECTION 공용
        - bbox (min_lat, max_lat, min_lng, max_lng): union bounding box geo filter (우선)
        - anchor_lat/lon/radius_m: circle geo filter (bbox 없을 때 사용)
        """
        must_conditions = []
        must_not_conditions = []
        # fallback 포함 DB 실존값으로 변환 (예: "문화시설" → ["관광지"])
        category_values = self._resolve_category_values(categories)

        if category_values:
            if len(category_values) >= 2:
                print(f"[INFO] category candidates built: {category_values}")
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
        print(f"[INFO] query_filter built: category={categories} values={category_values} geo={'bbox' if bbox else 'circle' if anchor_lat else 'no'}")
        return built

    def search_text(self, query: str, limit: int = 5, categories: list[CategoryType] = None, has_image: bool = False):
        """
        Text-based search for places (Semantic).
        Uses 'text_vec' (BGE-M3) in PLACES_COLLECTION.
        """
        print(f"[INFO] search_text (Semantic) start query='{query[:80]}' limit={limit} categories={categories} has_image={has_image}")
        query_vec = self.text_model.encode(query).astype(np.float32)

        query_filter = self._build_query_filter(categories, has_image)

        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        print(f"[INFO] search_text hits={len(response.points)}")
        return response.points

    def search_text_to_image(self, query: str, limit: int = 5, categories: list[CategoryType] = None):
        """
        Text-to-Image cross-modal search.
        Uses CLIP Text Encoder to find images in 'img_vec_agg'.
        """
        print(f"[INFO] search_text_to_image (Cross-modal) start query='{query[:80]}'")
        # Using CLIP to encode text for image matching
        query_vec = self.vision_model.encode(query).astype(np.float32)

        query_filter = self._build_query_filter(categories)

        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            using="img_vec_agg",
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        return response.points

    async def search_image(self, image_url: str, limit: int = 5, group_size: int = 3, categories: list[CategoryType] = None):
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
        query_filter = self._build_query_filter(categories)

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
        print(
            f"[INFO] search_hybrid start query='{query[:80]}' has_image={'yes' if image_url else 'no'} "
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
            print(f"[INFO] combined bbox from GPS+anchor ({geo_bbox_mode}): {geo_bbox}")
        elif apply_geo and has_gps:
            # GPS만 있을 때: GPS 기준 bbox
            expanded_radius_km = MAX_DISTANCE_KM * (GEO_RETRY_MULTIPLIER if geo_retry_count > 0 else 1.0)
            geo_bbox = _km_to_bbox(user_latitude, user_lon, expanded_radius_km)
            print(f"[INFO] GPS-only bbox: {geo_bbox}")

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
        # 채널별 Qdrant fetch 상한. *5는 과도 → *CANDIDATE_LIMIT_MULTIPLIER(기본 3)으로 축소.
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

        # --- A. Text Search Channel ---
        if query and query.strip() and scope in {"auto", "place_only"}:
            # 1. Scenario: Semantic Text Search (BGE-M3) — PLACES_COLLECTION (geo filter 적용)
            text_emb = await asyncio.to_thread(self.text_model.encode, query)
            text_emb = np.asarray(text_emb, dtype=np.float32)
            t_t_resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PLACES_COLLECTION,
                query=text_emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=places_filter,
            )
            print(f"[INFO] text_semantic hits={len(t_t_resp.points)} (filter={'yes' if places_filter else 'no'} geo={apply_geo})")
            collect_hits(t_t_resp.points, 1.0, "text_semantic", PLACES_COLLECTION)

        if ENABLE_QDRANT_SPARSE and query and query.strip() and scope in {"auto", "place_only"}:
            try:
                sparse_indices, sparse_values = build_sparse_vector(query)
                if sparse_indices and sparse_values:
                    sparse_resp = await asyncio.to_thread(
                        self.client.query_points,
                        collection_name=PLACES_COLLECTION,
                        query=SparseVector(indices=sparse_indices, values=sparse_values),
                        using="text_sparse",
                        limit=candidates_limit,
                        with_payload=True,
                        query_filter=places_filter,
                    )
                    collect_hits(sparse_resp.points, 0.85, "qdrant_sparse", PLACES_COLLECTION)
                    print(f"[INFO] qdrant_sparse hits={len(sparse_resp.points)}")
            except Exception as e:
                print(f"[WARN] qdrant sparse channel failed: {e}")

        if query and query.strip() and scope in {"auto", "photo_only"}:
            # 2. Scenario: Cross-modal Text-to-Image (CLIP Text) — PHOTOS_COLLECTION (geo 없음)
            clip_text_emb = await asyncio.to_thread(self.vision_model.encode, query)
            clip_text_emb = np.asarray(clip_text_emb, dtype=np.float32)
            t_i_resp = await asyncio.to_thread(
                self.client.query_points,
                collection_name=PHOTOS_COLLECTION,
                query=clip_text_emb.tolist(),
                limit=candidates_limit,
                with_payload=True,
                query_filter=photos_filter,  # PHOTOS에는 geo 필드 없으므로 category만
            )
            collect_hits(t_i_resp.points, 0.5, "text_to_image", PHOTOS_COLLECTION)

        # --- B. Image Search Channel ---
        if image_url and scope in {"auto", "photo_only"}:
            img = await asyncio.to_thread(download_image, image_url)
            if img:
                # 3. Scenario: Visual Similarity (CLIP Vision) — PHOTOS_COLLECTION (geo 없음)
                img_emb = await asyncio.to_thread(self.vision_model.encode, img)
                img_emb = np.asarray(img_emb, dtype=np.float32)
                i_i_resp = await asyncio.to_thread(
                    self.client.query_points,
                    collection_name=PHOTOS_COLLECTION,
                    query=img_emb.tolist(),
                    limit=candidates_limit,
                    with_payload=True,
                    query_filter=photos_filter,  # geo 없음
                )
                collect_hits(i_i_resp.points, 1.0, "image_visual", PHOTOS_COLLECTION)

        if image_url and scope == "auto":
            # 4. Scenario: Emotional Enrichment (GPT-4o-mini -> BGE-M3) — PLACES_COLLECTION (geo filter 적용)
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
                    query_filter=places_filter,
                )
                collect_hits(i_e_resp.points, 0.8, "image_emotional", PLACES_COLLECTION)

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
                print(
                    f"[INFO] search_hybrid: geo filter returned 0 candidates ({radius_info}). "
                    f"Returning empty — graph will retry with {GEO_RETRY_MULTIPLIER:.1f}x expanded radius."
                )
            else:
                print(
                    f"[INFO] search_hybrid: expanded geo filter still returned 0 candidates "
                    f"(expanded_by={GEO_RETRY_MULTIPLIER:.1f}x, {radius_info}). Returning empty."
                )
            return []

        # --- C. Fusion & Boosting ---
        results = []
        fused = []
        query_addr_tokens = self._extract_query_addr_tokens(query or "")
        # preferred_location은 _location_text_bonus가 전담 처리.
        # _addr_sparse_bonus는 query 원문 주소 토큰만 담당 → preferred_addr_tokens 불필요. (#11)
        sparse_enabled = ENABLE_ADDR_SPARSE_BOOST and (
            bool(categories)
            or bool(query_addr_tokens)
        )

        # geo proximity boost anchor: 사용자 좌표 우선, 없으면 landmark anchor 사용
        prox_lat = user_latitude if user_latitude else location_anchor_lat
        prox_lon = user_lon if user_lon else location_anchor_lon

        for pid, data in score_map.items():
            payload = data.get("payload") or {}
            keyword_boost = self._keyword_match_bonus(query=query or "", payload=payload, location_hint=preferred_location)
            location_text_boost = self._location_text_bonus(preferred_location=preferred_location, payload=payload)
            geo_proximity_boost = self._geo_proximity_bonus(
                payload=payload,
                anchor_lat=prox_lat,
                anchor_lon=prox_lon,
                radius_km=GEO_PROXIMITY_RADIUS_KM,  # config 기반 반경 (#9)
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

            # input_tags ↔ payload.tags 부분 문자열 매칭 보너스
            tag_boost = 0.0
            if input_tags:
                tag_boost = self._tag_match_bonus(input_tags=input_tags, payload=payload)
                if tag_boost > 0.0:
                    data["matches"].add("tag_match")

            boost = keyword_boost + location_text_boost + geo_proximity_boost + addr_sparse_boost + tag_boost
            # BOOST_WEIGHT로 스케일 보정: RRF first_stage_score(0.01~0.05) 대비
            # boost 합계(최대 0.65) 스케일 불균형 완화.
            # 적용 후 boost 최대 기여 ≈ 0.65 * 0.3 = 0.195
            fused.append(
                (
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
                )
            )

        fused.sort(key=lambda x: x[2], reverse=True)

        # min-max 정규화: 고정 분모(FUSED_SCORE_MAX) 대신 결과셋 내 최솟값·최댓값 사용.
        # 이전 방식은 FUSED_SCORE_MAX(0.20)보다 실제 max가 크면 상위 결과가 모두
        # 1.0으로 clamp되어 점수 분포가 의미 없어지는 문제가 있었다.
        if fused:
            all_final   = [x[2]          for x in fused]
            all_rrf     = [x[1]["score"] for x in fused]
            fused_max   = all_final[0];   fused_min  = all_final[-1]
            fused_range = max(fused_max - fused_min, 1e-9)
            rrf_max     = max(all_rrf);   rrf_min    = min(all_rrf)
            rrf_range   = max(rrf_max - rrf_min, 1e-9)
        else:
            fused_min = fused_range = rrf_min = rrf_range = 1.0

        for idx, (pid, data, final_score, boost_detail) in enumerate(fused, start=1):
            results.append({
                "id": pid,
                # min-max 정규화: 이 결과셋 내에서 [0.0, 1.0] 상대 점수
                "score":             round((final_score    - fused_min) / fused_range, 4),
                "first_stage_score": round((data["score"]  - rrf_min)   / rrf_range,  4),
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

        print(f"[INFO] fusion & boosting returning {len(results)} candidates")

        first_stage_results = results[:candidate_k]
        if enable_rerank:
            # 이미지 전용 검색(query="")일 때 emotional_text를 fallback으로 사용.
            # 둘 다 없으면 _rerank_candidates 내부에서 rerank를 스킵하고 score 순 유지.
            rerank_query = (query or "").strip() or (emotional_text or "").strip()
            reranked = await self._rerank_candidates(
                query=rerank_query,
                candidates=first_stage_results,
                top_k=min(rerank_top_k, candidate_k)
            )
        else:
            reranked = first_stage_results[: min(rerank_top_k, candidate_k)]
            for idx, c in enumerate(reranked, start=1):
                c["rerank_score"] = None
                c["final_rank"] = idx

        # rerank 후 거리 블렌딩: geo_proximity_boost(이미 퓨전 단계에서 계산됨)를
        # rerank_score와 가중 합산하여 텍스트 관련도와 근접성을 함께 반영.
        # prox_lat/lng 이 있을 때만 적용 (없으면 순수 rerank 순위 유지).
        final_candidates = reranked
        if prox_lat is not None and prox_lon is not None:
            for c in reranked:
                raw_rerank = float(c.get("rerank_score") or 0.0)
                raw_geo = float(c.get("geo_proximity_boost") or 0.0)
                normalized_geo = min(raw_geo / GEO_MAX_BOOST, 1.0)  # [0, 1]
                c["blended_score"] = (
                    (1 - RERANK_GEO_BLEND_WEIGHT) * raw_rerank
                    + RERANK_GEO_BLEND_WEIGHT * normalized_geo
                )
            reranked.sort(key=lambda x: float(x.get("blended_score", 0.0)), reverse=True)
            for idx, c in enumerate(reranked, start=1):
                c["final_rank"] = idx
            print(f"[INFO] geo-blended reranking applied (blend_weight={RERANK_GEO_BLEND_WEIGHT})")
            final_candidates = reranked

            # 안전망: 블렌딩 후에도 너무 먼 장소가 남아 있을 경우를 대비한 거리 하드 필터
            nearby_candidates = self._filter_candidates_by_distance(
                reranked,
                anchor_lat=prox_lat,
                anchor_lon=prox_lon,
                max_distance_km=MAX_DISTANCE_KM * (GEO_RETRY_MULTIPLIER if geo_retry_count > 0 else 1.0),
            )
            if nearby_candidates:
                final_candidates = nearby_candidates
            else:
                print(
                    f"[INFO] search_hybrid distance post-filter kept 0 candidates; "
                    f"falling back to blended results (anchor=({prox_lat}, {prox_lon}))"
                )

        # 기존 인터페이스 호환: limit 기준으로 반환
        final = final_candidates[: max(int(limit or 0), 1)]
        print(f"[INFO] search_hybrid returning {len(final)} candidates (score_map={len(score_map)} reranked={len(reranked)})")
        return final

    def search_nearby(self, lat: float, lng: float, limit: int = 5, radius_km: float = 10.0):
        """
        Search for places near a specific coordinate.
        GEO 인덱스 사용이 가능하면 반경 필터 기반으로 조회하고, 아니면 제한적 fallback scroll을 사용한다.
        """
        print(f"[INFO] search_nearby start lat={lat} lng={lng} limit={limit} radius_km={radius_km}")
        candidate_points = []
        radius_m = max(float(radius_km), 0.1) * 1000.0
        scan_limit = max(int(limit or 0) * 20, 50)

        if ENABLE_GEO_FILTER:
            try:
                geo_filter = Filter(
                    must=[
                        FieldCondition(
                            key="geo",
                            geo_radius={
                                "center": {"lat": float(lat), "lon": float(lng)},
                                "radius": radius_m,
                            },
                        )
                    ]
                )
                points, _ = self.client.scroll(
                    collection_name=PLACES_COLLECTION,
                    scroll_filter=geo_filter,
                    limit=scan_limit,
                    with_payload=True,
                    with_vectors=False,
                )
                candidate_points = list(points)
                print(f"[DEBUG] search_nearby geo-filter candidates={len(candidate_points)}")
            except Exception as e:
                print(f"[WARN] search_nearby geo filter failed, fallback scroll: {e}")

        # fallback: legacy scroll (제한된 수량만 조회)
        if not candidate_points:
            points, _ = self.client.scroll(
                collection_name=PLACES_COLLECTION,
                limit=scan_limit,
                with_payload=True,
                with_vectors=False,
            )
            candidate_points = list(points)
            print(f"[DEBUG] search_nearby fallback candidates={len(candidate_points)}")

        results = []
        for p in candidate_points:
            payload = p.payload or {}
            p_lat, p_lng = self._payload_coordinates(payload)
            if p_lat is None or p_lng is None:
                continue

            dist = self._haversine(float(lat), float(lng), p_lat, p_lng)
            if dist <= radius_km:
                results.append({
                    "id": p.id,
                    "payload": payload,
                    "score": 1.0 / (dist + 0.1),
                    "distance_km": dist,
                })

        results.sort(key=lambda x: x["distance_km"])
        trimmed = results[:limit]
        print(f"[INFO] search_nearby matched={len(results)} returned={len(trimmed)}")
        return trimmed


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
