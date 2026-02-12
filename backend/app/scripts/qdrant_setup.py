import io
import uuid
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    PayloadSchemaType, HnswConfigDiff, OptimizersConfigDiff,
)
from sentence_transformers import SentenceTransformer

from app.scripts.preprocess_data import download_image
import os
import json
from app.core.config import *
from app.scripts.preprocess_data import location_to_latlng

# CLIPProcessor가 자동으로 resize / center crop / normalize 수행

class QdrantClientDB:
    def __init__(self):
        # Qdrant / Embedding init
        self.client = QdrantClient(host=os.getenv('QDRANT_HOST', "localhost"), port=os.getenv('QDRANT_PORT', 6333))
        self.model = SentenceTransformer("clip-ViT-B-32")  # 512-dim

        self.ensure_collections()

    # Qdrant schema
    def ensure_collections(self):
        # 1) places: named vectors (text_vec, img_vec_agg)
        if not self.client.collection_exists(PLACES_COLLECTION):
            self.client.create_collection(
                collection_name=PLACES_COLLECTION,
                vectors_config={
                    "text_vec": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
                    "img_vec_agg": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
                },
                hnsw_config=HnswConfigDiff(
                    on_disk=True,
                    m=16,
                    ef_construct=100,
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=20000
                ),
            )
            # 필터 자주 쓰면 인덱스
            self.client.create_payload_index(PLACES_COLLECTION, "region", PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(PLACES_COLLECTION, "category", PayloadSchemaType.KEYWORD)

        # 2) photos: image vector only
        if not self.client.collection_exists(PHOTOS_COLLECTION):
            self.client.create_collection(
                collection_name=PHOTOS_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
                hnsw_config=HnswConfigDiff(
                    on_disk=True,
                    m=16,
                    ef_construct=100,
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=20000
                ),
            )
            # group_by 키 성능 위해 인덱스 추천
            self.client.create_payload_index(PHOTOS_COLLECTION, "place_id", PayloadSchemaType.KEYWORD)

    # Utils: aggregate image vectors (top-k mean)
    def aggregate_vectors(self, vectors: np.ndarray, top_k: int = 5) -> np.ndarray:
        if vectors is None or vectors.size == 0:
            return np.zeros((VECTOR_SIZE,), dtype=np.float32)

        if vectors.shape[0] > top_k:
            vectors = vectors[:top_k]

        agg = vectors.mean(axis=0)
        agg = agg / (np.linalg.norm(agg) + 1e-12)
        return agg.astype(np.float32)

    # 장소 저장
    # - description -> places.text_vec
    # - image_urls -> photos(img_vec) 여러개 저장 + places.img_vec_agg 대표벡터 저장
    def add_place(self, place_id: str, description: str, image_urls: list[str], payload: dict):
        # 1) 텍스트 임베딩
        text_vec = self.model.encode(description).astype(np.float32)

        # 2) 이미지 다운로드 -> 임베딩 -> photos upsert
        photo_points = []
        img_vecs = []

        for url in image_urls:
            img = download_image(url)
            if img is None:
                continue

            img_vec = self.model.encode(img).astype(np.float32)
            img_vecs.append(img_vec)

            photo_points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=img_vec.tolist(),
                    payload={
                        "place_id": place_id,
                        "photo_url": url,
                        "region": payload.get("region"),
                        "category": payload.get("category"),
                        "address": payload.get("address"),
                        "title": payload.get("title"),
                    },
                )
            )

        if photo_points:
            self.client.upsert(collection_name=PHOTOS_COLLECTION, points=photo_points)

        # 3) places 대표 이미지 벡터(img_vec_agg)
        if img_vecs:
            img_vec_agg = self.aggregate_vectors(np.vstack(img_vecs), top_k=5)
        else:
            img_vec_agg = np.zeros((VECTOR_SIZE,), dtype=np.float32)

        # 4) places upsert (named vectors)
        place_point = PointStruct(
            id=place_id,
            vector={
                "text_vec": text_vec.tolist(),
                "img_vec_agg": img_vec_agg.tolist(),
            },
            payload={
                "place_id": place_id,
                "description": description,
                "address": payload.get("address"),
                "category": payload.get("category"),
                "title": payload.get("title"),
                "photo_count": len(image_urls),
                "lat": payload.get("lat"),
                "lng": payload.get("lng"),
            },
        )
        self.client.upsert(collection_name=PLACES_COLLECTION, points=[place_point])

        return {"place_id": place_id, "photos_upserted": len(photo_points)}


    def ingest_data(self, file_path: str):
        import json
        
        if not os.path.exists(file_path):
            print(f"[ERROR] Date file not found: {file_path}")
            return
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"[INFO] Start ingestion.. total {len(data)} items.")
        
        success_count = 0
        for item in data:
            try:
                # 1. Prepare fields
                place_id = item.get("id")
                name = item.get("name", "")
                address = item.get("주소", "")
                
                # Description generation (combining relevant fields)
                desc_parts = []
                for key, value in item.items():
                    if isinstance(value, str) and key not in ["id", "name", "주소"]:
                        desc_parts.append(f"{key}: {value}")

                description = " ".join(desc_parts)
                
                # 2) 주소 -> 좌표 변환
                latlng = location_to_latlng(address)
                if latlng is None:
                    print(f"[ERROR] 좌표 변환 실패, 건너뜀: {address}")
                    pass
                
                # Region extraction (simple heuristic from address)
                region = address.split(" ")[1] if len(address.split(" ")) > 1 else "기타"
                
                # Category
                category = "관광지" # Fixed for now or extract if available
                
                # Image URLs
                image_urls = item.get("photo_urls", [])
                
                # 2. Add Place (which handles images internally)
                self.add_place(
                    place_id=place_id,
                    description=description,
                    image_urls=image_urls,
                    payload={
                        "region": region,
                        "category": category,
                        "address": address,
                        "title": name,
                        "lat": latlng.get("lat") if latlng else 0,
                        "lng": latlng.get("lng") if latlng else 0,
                    }
                )
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"  - Progress: {success_count}/{len(data)} done.")
                    
            except Exception as e:
                print(f"[ERROR] Failed to ingest item {item.get('name')}: {e}")
                
        print(f"[INFO] Ingestion finished. Success: {success_count}/{len(data)}")

if __name__ == "__main__":
    # Run ingestion
    client = QdrantClientDB()
    
    # Adjust path as needed. Assuming script is run from backend root or scripts dir.
    # We will try to find the file manually.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend/app
    root_dir = os.path.dirname(base_dir) # backend
    data_path = os.path.join(root_dir, "data", "visitkorea_data.json")
    
    client.ingest_data(data_path)
