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

    def search_text(self, query: str, limit: int = 5):
        """
        Text-based search for places.
        Uses 'text_vec' in PLACES_COLLECTION.
        """
        query_vec = self.model.encode(query).astype(np.float32)
        
        # Search in places collection (text_vec)
        # Using query_points instead of search
        response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=query_vec.tolist(),
            using="text_vec",
            limit=limit,
            with_payload=True,
        )
        
        return response.points

    def search_image(self, image_url: str, limit: int = 5, group_size: int = 3):
        """
        Image-based search using Group By on PHOTOS_COLLECTION.
        Finds specific photos similar to the input image, then groups them by place_id.
        """
        img = download_image(image_url)
        if img is None:
            print("[WARN] Failed to download image for search.")
            return []

        query_vec = self.model.encode(img).astype(np.float32)

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
        
        return response.groups

    def search_hybrid(self, query: str, image_url: str = None, limit: int = 5, alpha: float = 0.5):
        """
        Hybrid search combining Text and Image (Visual) similarity.
        - Text Query -> text_vec similarity
        - Image Query -> img_vec_agg (aggregated visual embedding of the place) similarity
        
        alpha: Weight for text score (0.0 to 1.0). Image weight will be (1 - alpha).
               If image_url is None, performs only text search.
        """
        if not image_url:
            return self.search_text(query, limit)

        # 1. Text Vector
        text_emb = self.model.encode(query).astype(np.float32)

        # 2. Image Vector (Query Image)
        img = download_image(image_url)
        if img is None:
            # Fallback to text only if image download fails
            return self.search_text(query, limit)
        
        img_emb = self.model.encode(img).astype(np.float32)

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
        
        # Search by Text
        text_response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=text_emb.tolist(),
            using="text_vec",
            limit=candidates_limit,
            with_payload=True,
        )
        text_hits = text_response.points
        
        # Search by Image (Place's Aggregated Visual Vector)
        img_response = self.client.query_points(
            collection_name=PLACES_COLLECTION,
            query=img_emb.tolist(),
            using="img_vec_agg",
            limit=candidates_limit,
            with_payload=True,
        )
        img_hits = img_response.points
        
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
        
    def search_nearby(self, lat: float, lng: float, limit: int = 5, radius_km: float = 10.0):
        """
        Search for places near a specific coordinate.
        Since we don't have a Geo Index yet, we will fetch all (or many) and filter/sort in Python.
        For 177 items, this is efficient enough.
        """
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
        
        return results[:limit]

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
        # Instantiate retriever (In production, use dependency injection or singleton)
        # Note: This loads the model every time if not cached. 
        # For better performance, move instantiation outside or use lru_cache
        retriever = PlaceRetriever.get_instance() 
        
        # Main Search (Hybrid)
        search_results = retriever.search_hybrid(
            query=message_in.message,
            image_url=message_in.image_path,
            limit=3
        )
        
        formatted_results = []
        best_place = None
        
        if search_results:
            best_place = search_results[0] # Top 1
            
            formatted_results.append(f"### 🔎 Search Results")
            for i, res in enumerate(search_results):
                payload = res.get('payload', {})
                title = payload.get('title', 'Unknown')
                category = payload.get('category', 'Unknown')
                desc = payload.get('description', '')
                addr = payload.get('address', '')
                formatted_results.append(f"{i+1}. **{title}** ({category})\n   - Address: {addr}\n   - Description: {desc[:200]}...")

        # Nearby Search (if best match found and has coordinates)
        if best_place:
            bp_payload = best_place.get('payload', {})
            lat = bp_payload.get('lat', 0)
            lng = bp_payload.get('lng', 0)
            
            if lat != 0 and lng != 0:
                nearby_places = retriever.search_nearby(lat, lng, limit=3, radius_km=5.0)
                if nearby_places:
                    formatted_results.append(f"\n### 📍 Nearby Recommendations (near {bp_payload.get('title')})")
                    for i, res in enumerate(nearby_places):
                        # Filter out the place itself if needed, but Qdrant might return it. Use ID check.
                        if res['id'] == best_place['id']:
                            continue
                            
                        payload = res.get('payload', {})
                        title = payload.get('title', 'Unknown')
                        dist = res.get('distance_km', 0)
                        formatted_results.append(f"- **{title}** ({dist:.1f}km away) - {payload.get('category')}")

        if formatted_results:
            context_str = "\n".join(formatted_results)
            print(f"[INFO] Context Reference:\n{context_str}")
            
    except Exception as e:
        print(f"[ERROR] Retrieval failed: {e}")
        context_str = None

    return context_str
