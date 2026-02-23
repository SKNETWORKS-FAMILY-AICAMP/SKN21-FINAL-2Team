import os
import json
import uuid
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    PayloadSchemaType, HnswConfigDiff, OptimizersConfigDiff,
)
from sentence_transformers import SentenceTransformer
from app.core.config import PLACES_COLLECTION, PHOTOS_COLLECTION, VECTOR_SIZE
from app.scripts.preprocess_data import download_image, ingest_data

# 로컬 실행을 위한 환경 변수 (평가 시와 동일)
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"

class Reindexer:
    def __init__(self):
        self.client = QdrantClient(host=os.environ["QDRANT_HOST"], port=int(os.environ["QDRANT_PORT"]))
        self.model = SentenceTransformer("clip-ViT-B-32")
        print(f"[INFO] Initialized Qdrant client and CLIP model (dim={VECTOR_SIZE})")

    def recreate_collections(self):
        print(f"[INFO] Recreating collections: {PLACES_COLLECTION}, {PHOTOS_COLLECTION}")
        
        # Drop existing
        if self.client.collection_exists(PLACES_COLLECTION):
            self.client.delete_collection(PLACES_COLLECTION)
        if self.client.collection_exists(PHOTOS_COLLECTION):
            self.client.delete_collection(PHOTOS_COLLECTION)
            
        # Create PLACES
        self.client.create_collection(
            collection_name=PLACES_COLLECTION,
            vectors_config={
                "text_vec": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
                "img_vec_agg": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
            }
        )
        self.client.create_payload_index(PLACES_COLLECTION, "category", PayloadSchemaType.KEYWORD)
        self.client.create_payload_index(PLACES_COLLECTION, "place_id", PayloadSchemaType.KEYWORD)

        # Create PHOTOS
        self.client.create_collection(
            collection_name=PHOTOS_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True)
        )
        self.client.create_payload_index(PHOTOS_COLLECTION, "place_id", PayloadSchemaType.KEYWORD)
        print("[INFO] Collections recreated successfully.")

    def aggregate_vectors(self, vectors: np.ndarray, top_k: int = 5) -> np.ndarray:
        if vectors is None or vectors.size == 0:
            return np.zeros((VECTOR_SIZE,), dtype=np.float32)
        if vectors.shape[0] > top_k:
            vectors = vectors[:top_k]
        agg = vectors.mean(axis=0)
        agg = agg / (np.linalg.norm(agg) + 1e-12)
        return agg.astype(np.float32)

    def add_place(self, payload: dict):
        place_id = int(payload['place_id'])
        description = payload['description'] or payload['title']
        image_urls = payload['image_urls']

        # 1) 텍스트 임베딩 (제목과 설명을 조합)
        text_to_embed = f"{payload['title']} {description}"
        text_vec = self.model.encode(text_to_embed).astype(np.float32)

        # 2) 이미지 임베딩
        img_vecs = []
        photo_points = []
        for url in image_urls[:3]: # 가속화를 위해 최대 3개까지만
            img = download_image(url)
            if img:
                vec = self.model.encode(img).astype(np.float32)
                img_vecs.append(vec)
                photo_points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec.tolist(),
                    payload={"place_id": place_id, "photo_url": url, "category": payload.get("category")}
                ))
        
        if photo_points:
            self.client.upsert(PHOTOS_COLLECTION, points=photo_points)

        # 3) 장소 통합 벡터
        img_vec_agg = self.aggregate_vectors(np.vstack(img_vecs)) if img_vecs else np.zeros((VECTOR_SIZE,))
        
        place_point = PointStruct(
            id=place_id,
            vector={"text_vec": text_vec.tolist(), "img_vec_agg": img_vec_agg.tolist()},
            payload=payload
        )
        self.client.upsert(PLACES_COLLECTION, points=[place_point])

def run_reindexing():
    reindexer = Reindexer()
    reindexer.recreate_collections()
    
    # backend 디렉토리 기준으로 data 경로 설정
    current_dir = os.getcwd()
    data_dir = os.path.join(current_dir, "data")
    
    if not os.path.exists(data_dir):
        print(f"[ERROR] Data directory not found at: {data_dir}")
        return

    success_count = 0
    file_list = [f for f in os.listdir(data_dir) if f.endswith(".jsonl") and not f.startswith("25_")]
    print(f"[INFO] Found {len(file_list)} files to process.")
    
    for filename in file_list:
        print(f"[PROCESS] Indexing file: {filename}")
        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = [json.loads(line) for line in f]
                # 각 파일에서 최대 20개씩만 샘플로 색인 (평가 속도 및 리소스 고려)
                for payload in ingest_data(data[:20]):
                    reindexer.add_place(payload)
                    success_count += 1
                    if success_count % 10 == 0:
                        print(f"  - Indexed {success_count} points total...")
        except Exception as e:
            print(f"  - [ERROR] Failed to process {filename}: {e}")

    print(f"[DONE] Reindexing finished. Total {success_count} places indexed.")

if __name__ == "__main__":
    run_reindexing()
