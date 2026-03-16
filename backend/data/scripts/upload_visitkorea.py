"""
visitkorea 데이터 Qdrant 업로드 스크립트
==========================================
기존 places/photos 컬렉션에 upsert (재생성 안 함)

입력: data/preprocessed/visitkorea_{카테고리}.json
출력: Qdrant places 컬렉션 upsert + photos 컬렉션 upsert + 스냅샷 생성

사용법:
    PYTHONPATH=. python data/scripts/upload_visitkorea.py
    PYTHONPATH=. python data/scripts/upload_visitkorea.py --snapshot   # 업로드 후 스냅샷
"""

import json
import sys
import uuid
import os
import numpy as np
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(__file__).resolve().parent.parent
PRE_DIR = DATA_DIR / "preprocessed"
SNAP_DIR = DATA_DIR / "snapshots"
SNAP_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(BACKEND_DIR))

from app.utils.config import (
    TEXT_MODEL, TEXT_VECTOR_SIZE, DEVICE,
    VISION_MODEL, VISION_VECTOR_SIZE,
    PLACES_COLLECTION, PHOTOS_COLLECTION,
)
from app.scripts.preprocess_data import (
    download_image,
    enrich_payload_geo_and_addr_tokens,
    build_sparse_text,
    build_sparse_vector,
)

BATCH_SIZE = 32
CATEGORIES = ["관광지", "음식점"]


def make_point_id(contentid: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"visitkorea:{contentid}"))


def upload_category(client, text_model, vision_model, category: str):
    path = PRE_DIR / f"visitkorea_{category}.json"
    if not path.exists():
        print(f"  [SKIP] {path.name} 없음")
        return 0, 0, 0

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n  {category}: {len(data)}건 로드")

    places_success = 0
    photos_success = 0
    errors = 0

    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]

        llm_texts = [item.get("llm_text", item.get("title", "")) for item in batch]
        llm_texts_flat = [t.replace("\n", " ") for t in llm_texts]
        vecs = text_model.encode(llm_texts_flat, batch_size=BATCH_SIZE, show_progress_bar=False)

        place_points = []
        photo_points = []

        for item, vec in zip(batch, vecs):
            try:
                payload = dict(item)
                payload = enrich_payload_geo_and_addr_tokens(payload)

                sparse_text = build_sparse_text(payload)
                sparse_indices, sparse_values = build_sparse_vector(sparse_text)

                vector_payload = {"": vec.astype(np.float32).tolist()}
                if sparse_indices and sparse_values:
                    vector_payload["text_sparse"] = SparseVector(
                        indices=sparse_indices, values=sparse_values
                    )

                point_id = make_point_id(str(payload.get("contentid", "")))

                place_points.append(PointStruct(
                    id=point_id,
                    vector=vector_payload,
                    payload=payload,
                ))

                image_url = payload.get("image")
                if image_url:
                    img = download_image(image_url)
                    if img is not None:
                        img_vec = vision_model.encode(img).astype(np.float32)
                        photo_points.append(PointStruct(
                            id=str(uuid.uuid4()),
                            vector=img_vec.tolist(),
                            payload=payload,
                        ))

            except Exception as e:
                print(f"    [오류] '{item.get('title')}': {e}")
                errors += 1

        if place_points:
            client.upsert(collection_name=PLACES_COLLECTION, points=place_points)
            places_success += len(place_points)

        if photo_points:
            client.upsert(collection_name=PHOTOS_COLLECTION, points=photo_points)
            photos_success += len(photo_points)

        done = min(i + BATCH_SIZE, len(data))
        if (i // BATCH_SIZE + 1) % 5 == 0 or i == 0 or done == len(data):
            print(f"    진행: {done}/{len(data)} (places={places_success}, photos={photos_success})")

    print(f"  {category} 완료: places {places_success} / photos {photos_success} / 실패 {errors}")
    return places_success, photos_success, errors


def recreate_collections(client: QdrantClient):
    """places, photos 컬렉션 삭제 후 재생성"""
    from qdrant_client.models import (
        Distance, VectorParams, HnswConfigDiff, OptimizersConfigDiff,
        SparseVectorParams, SparseIndexParams, PayloadSchemaType,
    )
    for name in (PLACES_COLLECTION, PHOTOS_COLLECTION):
        if client.collection_exists(name):
            client.delete_collection(name)
            print(f"  삭제: {name}")

    client.create_collection(
        collection_name=PLACES_COLLECTION,
        vectors_config=VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
        sparse_vectors_config={
            "text_sparse": SparseVectorParams(index=SparseIndexParams(on_disk=True))
        },
        hnsw_config=HnswConfigDiff(on_disk=True, m=16, ef_construct=100),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=20000),
    )
    client.create_payload_index(PLACES_COLLECTION, "contenttypeid", PayloadSchemaType.KEYWORD)
    client.create_payload_index(PLACES_COLLECTION, "geo", PayloadSchemaType.GEO)
    client.create_payload_index(PLACES_COLLECTION, "addr_tokens", PayloadSchemaType.KEYWORD)
    print(f"  생성: {PLACES_COLLECTION}")

    client.create_collection(
        collection_name=PHOTOS_COLLECTION,
        vectors_config=VectorParams(size=VISION_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
        hnsw_config=HnswConfigDiff(on_disk=True, m=16, ef_construct=100),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=20000),
    )
    client.create_payload_index(PHOTOS_COLLECTION, "contenttypeid", PayloadSchemaType.KEYWORD)
    client.create_payload_index(PHOTOS_COLLECTION, "contentid", PayloadSchemaType.KEYWORD)
    client.create_payload_index(PHOTOS_COLLECTION, "geo", PayloadSchemaType.GEO)
    client.create_payload_index(PHOTOS_COLLECTION, "addr_tokens", PayloadSchemaType.KEYWORD)
    print(f"  생성: {PHOTOS_COLLECTION}")


def main():
    host = "localhost"
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=600)

    # 컬렉션 재생성 (visitkorea만 넣을 것이므로)
    print("컬렉션 재생성...")
    recreate_collections(client)

    print(f"\n텍스트 모델 로드: {TEXT_MODEL} ({DEVICE})")
    text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)

    print(f"비전 모델 로드: {VISION_MODEL} ({DEVICE})")
    vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)

    total_places = 0
    total_photos = 0
    total_errors = 0

    for cat in CATEGORIES:
        p, ph, e = upload_category(client, text_model, vision_model, cat)
        total_places += p
        total_photos += ph
        total_errors += e

    print(f"\n{'='*50}")
    print(f"전체 완료: places +{total_places} / photos +{total_photos} / 실패 {total_errors}")

    # 업로드 후 컬렉션 상태
    for name in [PLACES_COLLECTION, PHOTOS_COLLECTION]:
        info = client.get_collection(name)
        print(f"  {name}: 현재 {info.points_count}건")

    print("\n스냅샷 생성 중...")
    for name in [PLACES_COLLECTION, PHOTOS_COLLECTION]:
        snapshot = client.create_snapshot(collection_name=name)
        print(f"  {name}: {snapshot.name}")


if __name__ == "__main__":
    print("=" * 50)
    print("visitkorea Qdrant 업로드 (기존 컬렉션에 upsert)")
    print("=" * 50)
    main()
