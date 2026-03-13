import os
import numpy as np
import asyncio

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, MatchAny, SparseVector
)
from sentence_transformers import SentenceTransformer

from app.utils.config import (
    PLACES_COLLECTION, PHOTOS_COLLECTION, DEVICE,
    TEXT_MODEL, VISION_MODEL, TEXT_VECTOR_SIZE, VISION_VECTOR_SIZE,
    BM25_POOL_LIMIT, BM25_ENABLE_THRESHOLD, BM25_ENABLE_SCORE_THRESHOLD,
    ENABLE_ADDR_SPARSE_BOOST, ENABLE_GEO_FILTER,
    ENABLE_QDRANT_SPARSE,
    BOOST_WEIGHT,
    CANDIDATE_LIMIT_MULTIPLIER,
    GEO_PROXIMITY_RADIUS_KM,
    RRF_SCORE_MAX, FUSED_SCORE_MAX, MAX_BOOST_SUM,
    get_retrieval_params,
)
from app.schemas.chat import ChatMessageCreate
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

    def _build_query_filter(
        self,
        categories: list[CategoryType] = None,
        has_image: bool = False,
        anchor_lat: float | None = None,
        anchor_lon: float | None = None,
        radius_m: float | None = None,
    ) -> Filter | None:
        """카테고리, 이미지 유무, Geo 조건을 합성한 Qdrant 필터 생성.

        - category / has_image: PLACES_COLLECTION, PHOTOS_COLLECTION 공용
        - anchor_lat/lon/radius_m: PLACES_COLLECTION 전용 geo 조건 (hard filter)
          지정하지 않으면 geo 조건 없이 빌드.
        """
        must_conditions = []
        must_not_conditions = []
        category_values = [c.value for c in (categories or [])]

        if category_values:
            if len(category_values) >= 2:
                print(f"[INFO] category candidates built: {category_values}")
            must_conditions.append(
                FieldCondition(key="contenttypeid", match=MatchAny(any=category_values))
            )

        if has_image:
            from qdrant_client.models import IsEmptyCondition, PayloadField
            must_not_conditions.append(IsEmptyCondition(is_empty=PayloadField(key="image")))

        if anchor_lat is not None and anchor_lon is not None and radius_m is not None:
            must_conditions.append(
                FieldCondition(
                    key="geo",
                    geo_radius={
                        "center": {"lat": float(anchor_lat), "long": float(anchor_lon)},
                        "radius": float(radius_m),
                    },
                )
            )
            print(f"[INFO] geo filter added: lat={anchor_lat} lon={anchor_lon} radius_m={radius_m}")

        if not must_conditions and not must_not_conditions:
            return None

        built = Filter(
            must=must_conditions if must_conditions else None,
            must_not=must_not_conditions if must_not_conditions else None,
        )
        print(f"[INFO] query_filter built: category={categories} values={category_values} geo={'yes' if anchor_lat else 'no'}")
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
        user_longitude: float | None = None,
        preferred_location: str | None = None,
        candidate_k: int | None = None,
        enable_bm25: bool = True,
        enable_rerank: bool = True,
        rerank_top_k: int | None = None,
        search_scope: str = "auto",
        location_anchor_lat: float | None = None,
        location_anchor_long: float | None = None,
        location_radius_m: float | None = None,
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
        apply_geo = (
            ENABLE_GEO_FILTER
            and location_anchor_lat is not None
            and location_anchor_long is not None
            and location_radius_m is not None
        )
        places_filter = self._build_query_filter(
            categories,
            anchor_lat=location_anchor_lat if apply_geo else None,
            anchor_lon=location_anchor_long if apply_geo else None,
            radius_m=location_radius_m if apply_geo else None,
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
            place_vector_points.extend(t_t_resp.points)
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
                        query_filter=places_filter,  # geo filter 적용
                    )
                    place_vector_points.extend(sparse_resp.points)
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
                    query_filter=places_filter,  # geo filter 적용
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
                    # BM25는 벡터 pool 재채점이므로 반환 상한은 candidate_k에 맞춤. (#10)
                    # candidates_limit(채널 fetch 상한)이 아닌 실제 필요 후보 수 사용.
                    lexical_hits = await self._search_bm25_lexical(
                        query=query,
                        categories=categories,
                        candidate_points=point_pool,
                        candidate_k=candidate_k,
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

        # --- geo filter 0결과 fallback ---
        # geo filter 적용 후 후보가 하나도 없으면 geo 없이 재시도
        if apply_geo and not score_map:
            print(
                f"[INFO] search_hybrid: geo filter returned 0 candidates "
                f"(lat={location_anchor_lat} lon={location_anchor_long} r={location_radius_m}), "
                f"retrying without geo filter"
            )
            return await self.search_hybrid(
                query=query,
                image_url=image_url,
                limit=limit,
                categories=categories,
                emotional_text=emotional_text,
                user_latitude=user_latitude,
                user_longitude=user_longitude,
                preferred_location=preferred_location,
                candidate_k=candidate_k,
                enable_bm25=enable_bm25,
                enable_rerank=enable_rerank,
                rerank_top_k=rerank_top_k,
                search_scope=search_scope,
                # anchor None → 재귀 방지
                location_anchor_lat=None,
                location_anchor_long=None,
                location_radius_m=None,
            )

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
        prox_long = user_longitude if user_longitude else location_anchor_long

        for pid, data in score_map.items():
            payload = data.get("payload") or {}
            keyword_boost = self._keyword_match_bonus(query=query or "", payload=payload)
            location_text_boost = self._location_text_bonus(preferred_location=preferred_location, payload=payload)
            geo_proximity_boost = self._geo_proximity_bonus(
                payload=payload,
                anchor_lat=prox_lat,
                anchor_lng=prox_long,
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

            boost = keyword_boost + location_text_boost + geo_proximity_boost + addr_sparse_boost
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
                        "total": boost,
                    },
                )
            )

        fused.sort(key=lambda x: x[2], reverse=True)
        for idx, (pid, data, final_score, boost_detail) in enumerate(fused, start=1):
            results.append({
                "id": pid,
                # 모든 점수를 [0.0, 1.0] 범위로 정규화
                "score":             round(min(1.0, final_score        / FUSED_SCORE_MAX), 4),
                "first_stage_score": round(min(1.0, data["score"]      / RRF_SCORE_MAX),   4),
                "first_stage_rank": idx,
                "payload": data["payload"],
                "match_types": sorted(list(data["matches"])),
                "keyword_match_boost":  boost_detail["keyword"],
                "location_text_boost":  boost_detail["location_text"],
                "geo_proximity_boost":  boost_detail["geo_proximity"],
                "addr_sparse_boost":    boost_detail["addr_sparse"],
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

        # 기존 인터페이스 호환: limit 기준으로 반환
        final = reranked[: max(int(limit or 0), 1)]
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
                                "center": {"lat": float(lat), "long": float(lng)},
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
