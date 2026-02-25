import io
import uuid
import numpy as np
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    PayloadSchemaType, HnswConfigDiff, OptimizersConfigDiff,
)
from sentence_transformers import SentenceTransformer

from app.scripts.preprocess_data import download_image

from app.core.config import *
from app.scripts.preprocess_data import ingest_data

# CLIPProcessor가 자동으로 resize / center crop / normalize 수행

class QdrantClientDB:
    def __init__(self):
        # Qdrant / Embedding init
        host = os.getenv('QDRANT_HOST')
        port = os.getenv('QDRANT_PORT')
        self.client = QdrantClient(host=host, port=int(port))
        
        # Load specialized models
        self.text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)
        self.vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)
        
        print(f"[INFO] Models loaded on {DEVICE}")
        self.ensure_collections()

    # Qdrant schema
    def ensure_collections(self):
        # 1) places: named vectors (text_vec, img_vec_agg)
        if self.client.collection_exists(PLACES_COLLECTION):
             # recreate for schema change
             self.client.delete_collection(PLACES_COLLECTION)

        self.client.create_collection(
            collection_name=PLACES_COLLECTION,
            vectors_config={
                "text_vec": VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
                "img_vec_agg": VectorParams(size=VISION_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
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
        if self.client.collection_exists(PHOTOS_COLLECTION):
            self.client.delete_collection(PHOTOS_COLLECTION)

        self.client.create_collection(
            collection_name=PHOTOS_COLLECTION,
            vectors_config=VectorParams(size=VISION_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
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
            return np.zeros((VISION_VECTOR_SIZE,), dtype=np.float32)

        if vectors.shape[0] > top_k:
            vectors = vectors[:top_k]

        agg = vectors.mean(axis=0)
        agg = agg / (np.linalg.norm(agg) + 1e-12)
        return agg.astype(np.float32)

    # 장소 저장
    # - description -> places.text_vec (BGE-M3)
    # - image_urls -> photos(img_vec) 여러개 저장 + places.img_vec_agg 대표벡터 저장 (CLIP Vision)
    def add_place(self, payload: dict):
        place_id = int(payload['place_id'])
        description = payload.get('description', "")
        emotional_desc = payload.get('emotional_description', "")
        image_urls = payload.get('image_urls', [])
        
        # 1) 텍스트 임베딩 (BGE-M3)
        # Priority: emotional_description > description > title + address
        title = payload.get("title", "")
        address = payload.get("address", "") or payload.get("addr1", "")
        
        text_to_embed = emotional_desc if emotional_desc else description
        if not text_to_embed:
            text_to_embed = f"{title} {address}"
            
        text_vec = self.text_model.encode(text_to_embed).astype(np.float32)

        # 2) 이미지 다운로드 -> 임베딩 -> photos upsert (CLIP Vision)
        photo_points = []
        img_vecs = []

        for url in image_urls:
            img = download_image(url)
            if img is None:
                continue

            # Explicitly use CLIP for images
            img_vec = self.vision_model.encode(img).astype(np.float32)
            img_vecs.append(img_vec)
            
            photo_points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=img_vec.tolist(),
                    payload={
                        "place_id": place_id,
                        "photo_url": url,
                        "category": payload.get("category"),
                        "address": address,
                        "title": title,
                    },
                )
            )

        if photo_points:
            self.client.upsert(collection_name=PHOTOS_COLLECTION, points=photo_points)

        # 3) places 대표 이미지 벡터(img_vec_agg)
        if img_vecs:
            img_vec_agg = self.aggregate_vectors(np.vstack(img_vecs), top_k=5)
        else:
            img_vec_agg = np.zeros((VISION_VECTOR_SIZE,), dtype=np.float32)

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
                "emotional_description": emotional_desc,
                "address": address,
                "category": payload.get("category"),
                "title": title,
                "lat": payload.get("lat"),
                "lng": payload.get("lng"),
            },
        )
        self.client.upsert(collection_name=PLACES_COLLECTION, points=[place_point])

        return {"place_id": place_id, "photos_upserted": len(photo_points)}

# cd backend
# docker exec -it skn21-final-2team-backend-1 python -m app.scripts.qdrant_setup
if __name__ == "__main__":
    # Run ingestion
    client = QdrantClientDB()
    
    # Adjust path as needed. Assuming script is run from backend root or scripts dir.
    # We will try to find the file manually.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend/app
    root_dir = os.path.dirname(base_dir) # backend
    data_dir = os.path.join(root_dir, "data")
    
        
    if not os.path.exists(data_dir):
        print(f"[ERROR] Date file not found: {data_dir}")

    file_names = []
    file_data = []
        
    for filename in os.listdir(data_dir):
        if filename.endswith(".jsonl") and not filename.startswith("25_"):
            data_path = os.path.join(data_dir, filename)
            with open(data_path, 'r', encoding='utf-8') as f:
                data = [json.loads(line) for line in f]
                file_names.append((filename, len(data)))
                file_data.append(data)

    success_count = 0
    # Flatten the list of lists into a single list of items
    flat_data = [item for sublist in file_data for item in sublist]
    for data in ingest_data(flat_data):
        client.add_place(data)
        success_count += 1
        if success_count % 10 == 0:
            print(f"  - Progress: {success_count}/{len(flat_data)} done.")

    print("Finish Load Data - File : ", file_names)