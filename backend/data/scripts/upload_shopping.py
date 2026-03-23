"""
무신사/올리브영/다이소 데이터 Qdrant upsert 업로드
=================================================
기존 컬렉션을 삭제하지 않고, 새 데이터만 추가(upsert)합니다.
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
from qdrant_client.models import (
    PointStruct, SparseVector, Distance, VectorParams,
    PayloadSchemaType, HnswConfigDiff, OptimizersConfigDiff,
    SparseVectorParams, SparseIndexParams,
)
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BACKEND_DIR))

from app.utils.config import (
    TEXT_MODEL, DEVICE, VISION_MODEL, PLACES_COLLECTION, PHOTOS_COLLECTION,
    TEXT_VECTOR_SIZE, VISION_VECTOR_SIZE,
)
from app.scripts.preprocess_data import (
    download_image, enrich_payload_geo_and_addr_tokens,
    build_sparse_text, build_sparse_vector
)

BATCH_SIZE = 32

# 업로드 대상 파일 (data/ 디렉토리 직접 참조)
TARGET_FILES = {
    "다이소": "daiso_투어.json",
    "무신사": "musinsa_투어.json",
    "올리브영": "oliveyoung_투어.json",
}


def make_point_id(contentid: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"shopping:{contentid}"))


def upload_file(client, text_model, vision_model, label: str, file_name: str):
    path = DATA_DIR / file_name
    if not path.exists():
        print(f"  [SKIP] {path.name} 파일이 존재하지 않습니다.")
        return 0, 0, 0

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n  {label} ({file_name}): {len(data)}건 로드")

    places_ok = 0
    photos_ok = 0
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
            places_ok += len(place_points)

        if photo_points:
            client.upsert(collection_name=PHOTOS_COLLECTION, points=photo_points)
            photos_ok += len(photo_points)

        done = min(i + BATCH_SIZE, len(data))
        print(f"    진행: {done}/{len(data)} (places={places_ok}, photos={photos_ok})")

    print(f"  {label} 완료: places {places_ok} / photos {photos_ok} / 실패 {errors}")
    return places_ok, photos_ok, errors


def main():
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=600)

    # 컬렉션 존재 확인
    if not client.collection_exists(PLACES_COLLECTION):
        print(f"[오류] {PLACES_COLLECTION} 컬렉션이 없습니다. 먼저 qdrant_setup.py를 실행하세요.")
        return
    if not client.collection_exists(PHOTOS_COLLECTION):
        print(f"[오류] {PHOTOS_COLLECTION} 컬렉션이 없습니다. 먼저 qdrant_setup.py를 실행하세요.")
        return

    places_info = client.get_collection(PLACES_COLLECTION)
    photos_info = client.get_collection(PHOTOS_COLLECTION)
    print(f"[시작 전] {PLACES_COLLECTION}: {places_info.points_count}건, {PHOTOS_COLLECTION}: {photos_info.points_count}건")

    print(f"\n텍스트 모델 로드: {TEXT_MODEL} ({DEVICE})")
    text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)

    print(f"비전 모델 로드: {VISION_MODEL} ({DEVICE})")
    vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)

    total_places = 0
    total_photos = 0
    total_errors = 0

    for label, file_name in TARGET_FILES.items():
        p, ph, e = upload_file(client, text_model, vision_model, label, file_name)
        total_places += p
        total_photos += ph
        total_errors += e

    # 완료 후 상태
    places_info = client.get_collection(PLACES_COLLECTION)
    photos_info = client.get_collection(PHOTOS_COLLECTION)

    print(f"\n{'='*50}")
    print(f"업로드 완료: places +{total_places} / photos +{total_photos} / 실패 {total_errors}")
    print(f"[최종] {PLACES_COLLECTION}: {places_info.points_count}건, {PHOTOS_COLLECTION}: {photos_info.points_count}건")


if __name__ == "__main__":
    print("=" * 50)
    print("쇼핑 매장 데이터 Qdrant upsert (다이소/무신사/올리브영)")
    print("=" * 50)
    main()
