import numpy as np
import os
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    PayloadSchemaType, HnswConfigDiff, OptimizersConfigDiff,
    SparseVectorParams, SparseIndexParams, SparseVector,
)
from sentence_transformers import SentenceTransformer

from app.scripts.preprocess_data import (
    download_image,
    enrich_payload_geo_and_addr_tokens,
    build_sparse_text,
    build_sparse_vector,
)

from app.utils.config import *
from app.scripts.preprocess_data import ingest_data

# CLIPProcessor가 자동으로 resize / center crop / normalize 수행

class QdrantClientDB:
    def __init__(self, setup_collections: bool = True):
        # Qdrant / Embedding init
        print("==== QdrantClientDB init")
        host = os.getenv('QDRANT_HOST', 'localhost')
        port = os.getenv('QDRANT_PORT', '6333')
        print("==== host, port : ", host, port)
        print("==== QdrantClientDB get env load")

        self.client = QdrantClient(host=host, port=int(port), timeout=600)

        print("==== QdrantClientDB get env load")
        # Load specialized models
        self.text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)
        self.vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)
        
        print(f"[INFO] Models loaded on {DEVICE}")
        if setup_collections:
            self.ensure_collections()

    # Qdrant schema
    def ensure_collections(self):
        # 1) places: named vectors (text_vec, img_vec_agg)
        if self.client.collection_exists(PLACES_COLLECTION):
             # recreate for schema change
             self.client.delete_collection(PLACES_COLLECTION)

        self.client.create_collection(
            collection_name=PLACES_COLLECTION,
            vectors_config=VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
            sparse_vectors_config={
                "text_sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=True)
                )
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
        self.client.create_payload_index(PLACES_COLLECTION, "contenttypeid", PayloadSchemaType.KEYWORD)
        self.client.create_payload_index(PLACES_COLLECTION, "geo", PayloadSchemaType.GEO)
        self.client.create_payload_index(PLACES_COLLECTION, "addr_tokens", PayloadSchemaType.KEYWORD)
        
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
        self.client.create_payload_index(PHOTOS_COLLECTION, "contentid", PayloadSchemaType.KEYWORD)

    # 장소 저장
    # - description -> places.text_vec (BGE-M3)
    # - image_urls -> photos(img_vec) 여러개 저장 + places.img_vec_agg 대표벡터 저장 (CLIP Vision)
    def add_place(self, payload: dict):
        payload = enrich_payload_geo_and_addr_tokens(dict(payload))
        llm_text = payload.pop('llm_text', '')

        contentid = int(payload['contentid'])
        
        # [IMAGE] : Photo Collection ================================
        # # 2) 이미지 다운로드 -> 임베딩 -> photos upsert (CLIP Vision)
        image_urls = payload.get('image_urls', [])
        image = payload.get('image')
        if image:
            image_urls.append(image)

        photo_points = []

        for url in image_urls:
            img = download_image(url)
            if img is None:
                continue

            # Explicitly use CLIP for images
            img_vec = self.vision_model.encode(img).astype(np.float32)
            
            photo_points.append(
                PointStruct(
                    id=str(uuid.uuid4()),  # 고유 UUID 사용
                    vector=img_vec.tolist(),
                    payload=payload,
                )
            )

        if len(photo_points) > 0:
            self.client.upsert(collection_name=PHOTOS_COLLECTION, points=photo_points)

        # [Text] : Place Collection ================================
        # 3) places upsert (named vectors)
        text_vec = self.text_model.encode(llm_text).astype(np.float32)
        sparse_text = build_sparse_text(payload)
        sparse_indices, sparse_values = build_sparse_vector(sparse_text)

        vector_payload = {"": text_vec.tolist()}
        if sparse_indices and sparse_values:
            vector_payload["text_sparse"] = SparseVector(indices=sparse_indices, values=sparse_values)

        place_point = PointStruct(
            id=contentid,
            vector=vector_payload,
            payload=payload,
        )
        self.client.upsert(collection_name=PLACES_COLLECTION, points=[place_point])



    def add_popup_places(self, jsonl_path: str):
        """
        팝업스토어 전용 업로드 함수.
        - ingest_data() / 지오코딩 API 재호출 없음
        - llm_text 벡터화 + payload에도 llm_text 포함하여 저장
        """
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f if line.strip()]

        print(f"[INFO] 팝업스토어 업로드 시작: {len(data)}건")
        success = 0
        for i, item in enumerate(data):
            try:
                # contenttypeid_code 제거 (Qdrant payload 불필요)
                payload = {k: v for k, v in item.items()
                           if v not in (None, "", [], {}) and k != 'contenttypeid_code'}
                self.add_place(payload)
                success += 1
                if success % 10 == 0:
                    print(f"  - Progress: {success}/{len(data)} done.")
            except Exception as e:
                import traceback
                print(f"  [ERROR] #{i+1} '{item.get('title')}': {e}")
                traceback.print_exc()


        print(f"[INFO] 팝업스토어 업로드 완료: {success}/{len(data)}건")


# cd backend
# docker exec -it skn21-final-2team-backend-1 python -m app.scripts.qdrant_setup
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    print("==== mode : ", mode)

    host = os.getenv('QDRANT_HOST')
    port = os.getenv('QDRANT_PORT')
    print("==== host, port : ", host, port)

    # popup 모드: 기존 컬렉션 유지 (삭제 X), 전체 모드: 컬렉션 재생성
    client = QdrantClientDB(setup_collections=(mode != "popup"))

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(base_dir)
    data_dir = os.path.join(root_dir, "data", "llm_result")

    if not os.path.exists(data_dir):
        print(f"[ERROR] Data dir not found: {data_dir}")
        sys.exit(1)

    if mode == "popup":
        # 팝업스토어만 추가 (기존 DB 유지, 지오코딩 재호출 없음)
        popup_path = os.path.join(data_dir, "99_팝업스토어_enriched.jsonl")
        print("==== popup_path : ", popup_path)
        client.add_popup_places(popup_path)
    else:
        # 기존 전체 업로드 (팝업 제외)
        file_names = []
        file_data = []
        for filename in os.listdir(data_dir):
            if filename.endswith(".jsonl") and not filename.startswith(("25_", "99_")):
                data_path = os.path.join(data_dir, filename)
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = [json.loads(line) for line in f]
                    file_names.append((filename, len(data)))
                    file_data.append(data)

        success_count = 0
        flat_data = [item for sublist in file_data for item in sublist]
        for data in ingest_data(flat_data):
            client.add_place(data)
            success_count += 1
            if success_count % 10 == 0:
                print(f"  - Progress: {success_count}/{len(flat_data)} done.")

        print("Finish Load Data - File : ", file_names)
