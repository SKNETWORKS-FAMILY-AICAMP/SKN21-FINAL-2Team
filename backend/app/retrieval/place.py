import os
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, ScoredPoint
)
from sentence_transformers import SentenceTransformer
from app.core.config import (
    PLACES_COLLECTION, PHOTOS_COLLECTION, DEVICE,
    TEXT_MODEL, VISION_MODEL, TEXT_VECTOR_SIZE, VISION_VECTOR_SIZE
)
from app.schemas.chat import ChatMessageCreate
from app.scripts.preprocess_data import download_image
from app.utils.geocoder import GeoCoder
from app.services.vision import describe_image


class PlaceRetriever:
    _instance = None
    
    # 카테고리 명칭 -> contenttypeid 매핑
    CATEGORY_MAP = {
        "관광지": "12",
        "문화시설": "14",
        "축제공연행사": "15",
        "레포츠": "28",
        "숙박": "32",
        "쇼핑": "38",
        "음식점": "39",
        "카페": "39", # 카페는 보통 음식점(39)에 포함됨
    }
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
        
        print(f"[INFO] PlaceRetriever ready on {DEVICE}")

    def _preview_results(self, results, top_n: int = 3):
        preview = []
        for r in results[:top_n]:
            payload = r.get("payload", {})
            preview.append(
                {
                    "id": str(r.get("id")),
                    "title": payload.get("title"),
                    "score": round(float(r.get("score", 0.0)), 4),
                    "text_score": round(float(r.get("text_score", 0.0)), 4),
                    "img_score": round(float(r.get("img_score", 0.0)), 4),
                }
            )
        return preview

    def _build_category_filter(self, category: str = None) -> Filter | None:
        """카테고리 필터 생성 (데이터에 명칭이 저장되어 있으므로 명칭 그대로 필터링)"""
        if not category:
            return None
            
        # DB에 '관광지', '음식점' 등으로 저장되어 있음
        return Filter(
            must=[FieldCondition(key="category", match=MatchValue(value=category))]
        )

    def search_text(self, query: str, limit: int = 5, category: str = None):
        """
        Text-based search for places (Semantic).
        Uses 'text_vec' (BGE-M3) in PLACES_COLLECTION.
        """
        print(f"[INFO] search_text (Semantic) start query='{query[:80]}' limit={limit} category={category}")
        query_vec = self.text_model.encode(query).astype(np.float32)
        
        query_filter = self._build_category_filter(category)

        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            using="text_vec",
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        print(f"[INFO] search_text hits={len(response.points)}")
        return response.points

    def search_text_to_image(self, query: str, limit: int = 5, category: str = None):
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

    def search_image(self, image_url: str, limit: int = 5, group_size: int = 3, category: str = None):
        """
        Image-based search (Visual Similarity).
        Uses CLIP Vision Encoder on PHOTOS_COLLECTION.
        """
        print(f"[INFO] search_image (Visual) start image_url='{str(image_url)[:120]}'")
        img = download_image(image_url)
        if img is None:
            return []

        query_vec = self.vision_model.encode(img).astype(np.float32)
        query_filter = self._build_category_filter(category)

        response = self.client.query_points_groups(
            collection_name=PHOTOS_COLLECTION,
            query=query_vec.tolist(),
            group_by="place_id",
            group_size=group_size,
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        return response.groups

    def search_hybrid(self, query: str, image_url: str = None, limit: int = 5, category: str = None):
        """
        Refined Hybrid search combining Text (BGE-M3) and Image (CLIP-L) with Place-ID Fusion.
        1. Text Input -> BGE-M3 (Text DB) + CLIP Text (Image DB)
        2. Image Input -> CLIP Vision (Image DB) + Emotional Extraction (Text DB)
        """
        print(f"[INFO] search_hybrid start query='{query[:80]}' has_image={'yes' if image_url else 'no'}")
        
        query_filter = self._build_category_filter(category)
        candidates_limit = limit * 5
        score_map = {} # place_id -> {score, payload, match_types}

        def collect_hits(hits, weight, match_type):
            for h in hits:
                pid = h.id
                if pid not in score_map:
                    score_map[pid] = {"score": 0.0, "payload": h.payload, "matches": []}
                # Scoring: Sum of (ScoredPoint.score * weight) + Fusion Boost
                score_map[pid]["score"] += h.score * weight
                score_map[pid]["matches"].append(match_type)

        # --- A. Text Search Channel ---
        if query and query.strip():
            # 1. Scenario: Semantic Text Search (BGE-M3)
            text_emb = self.text_model.encode(query).astype(np.float32)
            t_t_hits = self.client.query_points(
                collection_name=PLACES_COLLECTION,
                query=text_emb.tolist(),
                using="text_vec",
                limit=candidates_limit,
                with_payload=True,
                query_filter=query_filter,
            ).points
            collect_hits(t_t_hits, 1.0, "text_semantic")

            # 2. Scenario: Cross-modal Text-to-Image (CLIP Text)
            clip_text_emb = self.vision_model.encode(query).astype(np.float32)
            t_i_hits = self.client.query_points(
                collection_name=PLACES_COLLECTION,
                query=clip_text_emb.tolist(),
                using="img_vec_agg",
                limit=candidates_limit,
                with_payload=True,
                query_filter=query_filter,
            ).points
            collect_hits(t_i_hits, 0.5, "text_to_image")

        # --- B. Image Search Channel ---
        if image_url:
            img = download_image(image_url)
            if img:
                # 3. Scenario: Visual Similarity (CLIP Vision)
                img_emb = self.vision_model.encode(img).astype(np.float32)
                i_i_hits = self.client.query_points(
                    collection_name=PLACES_COLLECTION,
                    query=img_emb.tolist(),
                    using="img_vec_agg",
                    limit=candidates_limit,
                    with_payload=True,
                    query_filter=query_filter,
                ).points
                collect_hits(i_i_hits, 1.0, "image_visual")

                # 4. Scenario: Emotional Enrichment (GPT-4o-mini -> BGE-M3)
                emotional_text = describe_image(image_url)
                if emotional_text:
                    emo_emb = self.text_model.encode(emotional_text).astype(np.float32)
                    i_e_hits = self.client.query_points(
                        collection_name=PLACES_COLLECTION,
                        query=emo_emb.tolist(),
                        using="text_vec",
                        limit=candidates_limit,
                        with_payload=True,
                        query_filter=query_filter,
                    ).points
                    collect_hits(i_e_hits, 0.8, "image_emotional")

        # --- C. Fusion & Boosting ---
        results = []
        for pid, data in score_map.items():
            final_score = data["score"]
            # Fusion Boost: If the place matches multiple scenarios, it's a stronger candidate
            num_matches = len(data["matches"])
            if num_matches > 1:
                final_score *= (1.0 + 0.2 * (num_matches - 1)) # 20% boost per extra scenario
            
            results.append({
                "id": pid,
                "score": final_score,
                "payload": data["payload"],
                "match_types": list(set(data["matches"]))
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
        
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


def retrieval_place(message_in: ChatMessageCreate):
    # Retrieval (Search Places)
    context_str = None
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
        search_results = retriever.search_hybrid(
            query=query,
            image_url=message_in.image_path,
            limit=5
        )
        print(f"[INFO] retrieval_place search_results_count={len(search_results) if search_results else 0}")
        
        formatted_results = []
        search_ids = []
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
                
                # PHOTOS_COLLECTION에서 place_id가 일치하는 사진들을 가져옴
                photos_response, _ = retriever.client.scroll(
                    collection_name=PHOTOS_COLLECTION,
                    scroll_filter=Filter(must=[FieldCondition(key="place_id", match=MatchValue(value=rid))]),
                    limit=5,
                    with_payload=True
                )
                photo_urls = [p.payload.get("image_url") for p in photos_response if p.payload.get("image_url")]

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
