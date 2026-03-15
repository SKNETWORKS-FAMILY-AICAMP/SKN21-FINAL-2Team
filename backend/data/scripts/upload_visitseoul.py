"""
Visit Seoul 데이터 Qdrant 업로드 스크립트
==========================================
입력: data/preprocessed/visitseoul_{카테고리}_{버전}.json
출력: Qdrant places 컬렉션 upsert + photos 컬렉션 upsert + 스냅샷 생성

사용법:
    python upload_visitseoul.py 관광지 template
    python upload_visitseoul.py 관광지 ai

주요 차이점 (기존 qdrant_setup.py 대비):
    - contentid가 문자열(KOP000036)이므로 UUID5로 변환
    - llm_text를 payload에도 포함 (기존은 embed만 하고 제외)
    - enrich_payload_llm_text skip (OpenAI 생성 llm_text 그대로 사용)
    - image 필드(단일 URL) → photos 컬렉션에 CLIP 임베딩
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

# 경로 설정 (backend/ 기준으로 실행 가능하도록)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
DATA_DIR = Path(__file__).resolve().parent.parent            # backend/data/
PRE_DIR = DATA_DIR / "preprocessed"

sys.path.insert(0, str(BACKEND_DIR))

from qdrant_client.models import (
    Distance, VectorParams, HnswConfigDiff, OptimizersConfigDiff,
    SparseVectorParams, SparseIndexParams, PayloadSchemaType,
)

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

BATCH_SIZE = 32   # 임베딩 배치 크기


def make_point_id(contentid: str) -> str:
    """contentid(문자열)를 결정적 UUID로 변환"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"visitseoul:{contentid}"))


def recreate_collections(client: QdrantClient):
    """places, photos 컬렉션 삭제 후 재생성"""
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


def upload(category: str, version: str, recreate: bool = False):
    filename = f"visitseoul_{category}_{version}.json"
    path = PRE_DIR / filename
    if not path.exists():
        print(f"파일 없음: {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"로드: {len(data)}건 ({filename})")

    # Qdrant 연결
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=600)
    print(f"Qdrant 연결: {host}:{port}")

    if recreate:
        print("컬렉션 재생성 중...")
        recreate_collections(client)

    # 텍스트 임베딩 모델
    print(f"텍스트 모델 로드: {TEXT_MODEL} ({DEVICE})")
    text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)

    # 이미지 임베딩 모델 (CLIP)
    print(f"비전 모델 로드: {VISION_MODEL} ({DEVICE})")
    vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)

    # 업로드
    places_success = 0
    photos_success = 0
    errors = 0

    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]

        # 배치 텍스트 임베딩
        llm_texts = [item.get("llm_text", item.get("title", "")) for item in batch]
        llm_texts_flat = [t.replace("\n", " ") for t in llm_texts]
        vecs = text_model.encode(llm_texts_flat, batch_size=BATCH_SIZE, show_progress_bar=False)

        place_points = []
        photo_points = []

        for item, vec in zip(batch, vecs):
            try:
                payload = dict(item)

                # geo + addr_tokens 추가
                payload = enrich_payload_geo_and_addr_tokens(payload)

                # llm_text는 payload에 유지

                # sparse vector
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

                # 이미지 임베딩 → photos 컬렉션
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
                print(f"  [오류] '{item.get('title')}': {e}")
                errors += 1

        if place_points:
            client.upsert(collection_name=PLACES_COLLECTION, points=place_points)
            places_success += len(place_points)

        if photo_points:
            client.upsert(collection_name=PHOTOS_COLLECTION, points=photo_points)
            photos_success += len(photo_points)

        if (i // BATCH_SIZE + 1) % 5 == 0 or i == 0:
            print(f"  진행: {min(i + BATCH_SIZE, len(data))}/{len(data)}")

    print(f"\n업로드 완료: places {places_success}건 / photos {photos_success}건 / 실패 {errors}건")

    # 스냅샷 생성
    print("스냅샷 생성 중...")
    snapshot = client.create_snapshot(collection_name=PLACES_COLLECTION)
    print(f"스냅샷 완료 (places): {snapshot.name}")
    snapshot = client.create_snapshot(collection_name=PHOTOS_COLLECTION)
    print(f"스냅샷 완료 (photos): {snapshot.name}")


def main():
    category = sys.argv[1] if len(sys.argv) > 1 else "관광지"
    version  = sys.argv[2] if len(sys.argv) > 2 else "ai"
    recreate = "--recreate" in sys.argv
    print("=" * 50)
    print(f"Visit Seoul 업로드: {category} / {version} 버전" + (" (컬렉션 재생성)" if recreate else ""))
    print("=" * 50)
    upload(category, version, recreate=recreate)
    print("=" * 50)


if __name__ == "__main__":
    main()
