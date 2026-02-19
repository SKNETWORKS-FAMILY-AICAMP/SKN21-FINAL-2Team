import os
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, ScoredPoint
)
from sentence_transformers import SentenceTransformer
from app.core.config import PLACES_COLLECTION, PHOTOS_COLLECTION, VECTOR_SIZE
from app.schemas.chat import ChatMessageCreate
from app.scripts.preprocess_data import download_image
from app.utils.geocoder import GeoCoder



class PlaceRetriever:
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
        self.model = SentenceTransformer("clip-ViT-B-32")
        print("[INFO] PlaceRetriever ready (model=clip-ViT-B-32)")

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

    def search_text(self, query: str, limit: int = 5):
        """
        Text-based search for places.
        Uses 'text_vec' in PLACES_COLLECTION.
        """
        print(f"[INFO] search_text start query='{query[:80]}' limit={limit}")
        query_vec = self.model.encode(query).astype(np.float32)
        print(f"[DEBUG] text query vector shape={query_vec.shape} dtype={query_vec.dtype}")
        
        # Search in places collection (text_vec)
        # Using query_points instead of search
        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            using="text_vec",
            limit=limit,
            with_payload=True,
        )
        print(f"[INFO] search_text hits={len(response.points)}")
        return response.points

    def search_image(self, image_url: str, limit: int = 5, group_size: int = 3):
        """
        Image-based search using Group By on PHOTOS_COLLECTION.
        Finds specific photos similar to the input image, then groups them by place_id.
        """
        print(f"[INFO] search_image start image_url='{str(image_url)[:120]}' limit={limit} group_size={group_size}")
        img = download_image(image_url)
        if img is None:
            print("[WARN] Failed to download image for search.")
            return []

        query_vec = self.model.encode(img).astype(np.float32)
        print(f"[DEBUG] image query vector shape={query_vec.shape} dtype={query_vec.dtype}")

        # Search photos, grouped by place_id
        # Using query_points_groups instead of search_groups
        response = self.client.query_points_groups(
            collection_name=PHOTOS_COLLECTION,
            query=query_vec.tolist(),
            group_by="place_id",
            group_size=group_size,
            limit=limit,
            with_payload=True,
        )
        print(f"[INFO] search_image groups={len(response.groups)}")
        return response.groups

    def search_hybrid(self, query: str, image_url: str = None, limit: int = 5, alpha: float = 0.5):
        """
        Hybrid search combining Text and Image (Visual) similarity.
        - Text Query -> text_vec similarity
        - Image Query -> img_vec_agg (aggregated visual embedding of the place) similarity
        
        alpha: Weight for text score (0.0 to 1.0). Image weight will be (1 - alpha).
               If image_url is None, performs only text search.
        """
        print(
            f"[INFO] search_hybrid start query='{query[:80]}' image_url={'yes' if image_url else 'no'} "
            f"limit={limit} alpha={alpha}"
        )
        
        if not image_url:
            print("[INFO] search_hybrid fallback=text_only (no image)")
            return self.search_text(query, limit)

        # 1. Text Vector
        text_emb = self.model.encode(query).astype(np.float32)
        print(f"[DEBUG] hybrid text vector shape={text_emb.shape} dtype={text_emb.dtype}")

        # 2. Image Vector (Query Image)
        img = download_image(image_url)
        if img is None:
            # Fallback to text only if image download fails
            print("[WARN] search_hybrid fallback=text_only (image download failed)")
            return self.search_text(query, limit)
        
        img_emb = self.model.encode(img).astype(np.float32)
        print(f"[DEBUG] hybrid image vector shape={img_emb.shape} dtype={img_emb.dtype}")

        # 3. Prefetch candidates (we need a strategy here)
        # Since Qdrant doesn't support direct "weighted sum" of two different named vectors in one query easily without prefetch,
        # we will fetch candidates using both vectors and merge scores manually or use Qdrant's batch search + manual fusion.
        # Alternatively, we can use 2 separate searches and merge logic.
        
        # Strategy:
        # Fetch top N results from Text Search
        # Fetch top N results from Image Search (on PLACES_COLLECTION using img_vec_agg)
        # Combine results using RRF or Weighted Sum.
        # Here we implement Weighted Sum.
        
        candidates_limit = limit * 2
        print(f"[DEBUG] hybrid candidates_limit={candidates_limit}")
        
        # Search by Text
        text_response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=text_emb.tolist(),
            using="text_vec",
            limit=candidates_limit,
            with_payload=True,
        )
        text_hits = text_response.points
        print(f"[INFO] hybrid text_hits={len(text_hits)}")
        
        # Search by Image (Place's Aggregated Visual Vector)
        img_response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=img_emb.tolist(),
            using="img_vec_agg",
            limit=candidates_limit,
            with_payload=True,
        )
        img_hits = img_response.points
        print(f"[INFO] hybrid image_hits={len(img_hits)}")
        
        # Map: place_id -> {'text_score': 0, 'img_score': 0, 'payload': ...}
        score_map = {}
        
        for h in text_hits:
            if h.id not in score_map:
                score_map[h.id] = {"text_score": 0.0, "img_score": 0.0, "payload": h.payload}
            score_map[h.id]["text_score"] = h.score
            
        for h in img_hits:
            if h.id not in score_map:
                score_map[h.id] = {"text_score": 0.0, "img_score": 0.0, "payload": h.payload}
            score_map[h.id]["img_score"] = h.score
            
        # Compute Weighted Score
        # Note: API returns Cosine Similarity (if configured). 
        # range can be [-1, 1]. For safe weighted sum, usually 0..1 is preferred but raw sum often works for ranking.
        final_results = []
        for pid, scores in score_map.items():
            final_score = (scores["text_score"] * alpha) + (scores["img_score"] * (1 - alpha))
            final_results.append({
                "id": pid,
                "score": final_score,
                "payload": scores["payload"],
                "text_score": scores["text_score"],
                "img_score": scores["img_score"]
            })
            
        # Sort by final score
        final_results.sort(key=lambda x: x["score"], reverse=True)
        trimmed = final_results[:limit]
        print(
            f"[INFO] hybrid merged={len(score_map)} final={len(trimmed)} "
            f"preview={self._preview_results(trimmed)}"
        )
        return trimmed
        
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
            p_lat = p.payload.get("lat", 0)
            p_lng = p.payload.get("lng", 0)
            
            if p_lat == 0 and p_lng == 0:
                continue
                
            dist = self._haversine(lat, lng, p_lat, p_lng)
            if dist <= radius_km:
                results.append({
                    "id": p.id,
                    "payload": p.payload,
                    "score": 1.0 / (dist + 0.1), # Score inversely proportional to distance
                    "distance_km": dist
                })
        
        # Sort by distance (ascending)
        results.sort(key=lambda x: x["distance_km"])
        trimmed = results[:limit]
        print(f"[INFO] search_nearby matched={len(results)} returned={len(trimmed)}")
        return trimmed

    def _haversine(self, lat1, lon1, lat2, lon2):
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
            limit=3
        )
        print(f"[INFO] retrieval_place search_results_count={len(search_results) if search_results else 0}")
        
        formatted_results = []
        search_ids = []
        if search_results:            
            formatted_results.append(f"### 🔎 Search Results")
            for i, res in enumerate(search_results):
                if isinstance(res, dict):
                    payload = res.get('payload', {})
                    rid = res.get('id')
                    score = res.get('score')
                else:
                    payload = getattr(res, "payload", {}) or {}
                    rid = getattr(res, "id", None)
                    score = getattr(res, "score", None)

                search_ids.append(rid)

                title = payload.get('title', 'Unknown')
                category = payload.get('category', 'Unknown')
                desc = payload.get('description', '')
                addr = payload.get('address', '')
                print(f"[DEBUG] retrieval_place result[{i}] id={rid} title='{title}' score={score}")
                formatted_results.append(f"{i+1}. **{title}** ({category})\n   - Address: {addr}\n   - Description: {desc[:200]}...")
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
