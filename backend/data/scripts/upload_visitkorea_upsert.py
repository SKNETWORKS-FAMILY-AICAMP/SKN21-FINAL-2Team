"""
visitkorea 데이터 Qdrant 업로드 (오직 upsert만 수행)
==================================================
기존 컬렉션을 삭제하지 않고, 새로운 데이터만 병렬로 추가합니다.
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

sys.path.insert(0, str(BACKEND_DIR))

from app.utils.config import (
    TEXT_MODEL, DEVICE, VISION_MODEL, PLACES_COLLECTION, PHOTOS_COLLECTION
)
from app.scripts.preprocess_data import (
    download_image, enrich_payload_geo_and_addr_tokens, 
    build_sparse_text, build_sparse_vector
)

BATCH_SIZE = 32

# 병렬 업로드를 위한 대상 파일 (사용자 요청 반영)
FILE_CATEGORIES = {
    "관광지_template": "visitkorea_관광지_template.json",
    "숙박_template": "visitkorea_숙박_template.json",
    "음식점_template": "visitkorea_음식점_teamplate.json",  # 오타 반영
    "콘텐츠_template": "visitkorea_콘텐츠_template.json",
    "투어_template": "visitkorea_투어_template.json",
}

def make_point_id(contentid: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"visitkorea:{contentid}"))

def upload_file(client, text_model, vision_model, category_name: str, file_name: str):
    path = PRE_DIR / file_name
    if not path.exists():
        print(f"  [SKIP] {path.name} 파일이 존재하지 않습니다.")
        return 0, 0, 0

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n  {category_name} ({file_name}): {len(data)}건 로드")

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

    print(f"  {category_name} 완료: places {places_success} / photos {photos_success} / 실패 {errors}")
    return places_success, photos_success, errors

def main():
    host = "localhost"
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port, timeout=600)

    # 연결 확인 및 현재 카운트 표시
    try:
        places_info = client.get_collection(PLACES_COLLECTION)
        photos_info = client.get_collection(PHOTOS_COLLECTION)
        print(f"[시작 전 상태] {PLACES_COLLECTION}: {places_info.points_count}건, {PHOTOS_COLLECTION}: {photos_info.points_count}건")
    except Exception as e:
        print(f"컬렉션 접근 오류 (DB 연결 확인 필요): {e}")
        return

    print(f"\n텍스트 모델 로드: {TEXT_MODEL} ({DEVICE})")
    text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)

    print(f"비전 모델 로드: {VISION_MODEL} ({DEVICE})")
    vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)

    total_places = 0
    total_photos = 0
    total_errors = 0

    for cat_name, file_name in FILE_CATEGORIES.items():
        p, ph, e = upload_file(client, text_model, vision_model, cat_name, file_name)
        total_places += p
        total_photos += ph
        total_errors += e

    print(f"\n{'='*50}")
    print(f"전체 병렬 upsert 완료: places +{total_places} / photos +{total_photos} / 실패 {total_errors}")

if __name__ == "__main__":
    print("=" * 50)
    print("visitkorea Qdrant 병렬 병합 업로드 (컬렉션 삭제 강제 비활성화)")
    print("=" * 50)
    main()
