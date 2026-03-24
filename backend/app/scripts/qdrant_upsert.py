"""Qdrant upsert 스크립트 (전처리 완료 데이터용)

enrich된 *_enrich.json 파일을 읽어서 Qdrant에 업로드한다.
geo, addr_tokens는 이미 전처리에서 생성되어 있으므로 별도 처리 불필요.

사용법:
    # 컬렉션 재생성 + 전체 업로드
    python -m app.scripts.qdrant_upsert

    # 컬렉션 유지 + 특정 파일만 추가
    python -m app.scripts.qdrant_upsert --append data/preprocessed/enrich/popply_팝업스토어_enrich.json

    # 업로드 + 스냅샷 생성
    python -m app.scripts.qdrant_upsert --snapshot
"""

import hashlib
import json
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    PayloadSchemaType,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from app.utils.config import (
    DEVICE,
    PHOTOS_COLLECTION,
    PLACES_COLLECTION,
    TEXT_MODEL,
    TEXT_VECTOR_SIZE,
    VISION_MODEL,
    VISION_VECTOR_SIZE,
)

log = logging.getLogger(__name__)

SPARSE_TOKEN_PATTERN = re.compile(r"\d+-\d+|[0-9]+|[가-힣a-z]+")


# ─────────────────────── sparse vector ───────────────────────


def _build_sparse_text(payload: dict) -> str:
    title = str(payload.get("title") or "").strip()
    category = str(payload.get("contenttypeid") or "").strip()
    addr = str(payload.get("addr") or "").strip()
    addr_tokens = payload.get("addr_tokens") or []
    parts = [title, category, addr, " ".join(addr_tokens)]
    return " ".join(p for p in parts if p).strip()


def _build_sparse_vector(text: str) -> tuple[list[int], list[float]]:
    text = str(text or "").lower().strip()
    if not text:
        return [], []
    tokens = [t for t in SPARSE_TOKEN_PATTERN.findall(text) if t]
    if not tokens:
        return [], []
    counts = Counter(tokens)
    items = []
    for token, freq in counts.items():
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16)
        items.append((idx, float(freq)))
    items.sort(key=lambda x: x[0])
    return [i for i, _ in items], [v for _, v in items]


# ─────────────────────── Qdrant client ───────────────────────


class QdrantUploader:
    def __init__(self, recreate: bool = True):
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        log.info("Qdrant 연결: %s:%d", host, port)

        self.client = QdrantClient(host=host, port=port, timeout=600)
        self.text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)
        self.vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE)
        log.info("모델 로드 완료 (device=%s)", DEVICE)

        if recreate:
            self._create_collections()

    def _create_collections(self):
        # places
        if self.client.collection_exists(PLACES_COLLECTION):
            self.client.delete_collection(PLACES_COLLECTION)
        self.client.create_collection(
            collection_name=PLACES_COLLECTION,
            vectors_config=VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
            sparse_vectors_config={
                "text_sparse": SparseVectorParams(index=SparseIndexParams(on_disk=True))
            },
            hnsw_config=HnswConfigDiff(on_disk=True, m=16, ef_construct=100),
            optimizers_config=OptimizersConfigDiff(indexing_threshold=20000),
        )
        self.client.create_payload_index(PLACES_COLLECTION, "contenttypeid", PayloadSchemaType.KEYWORD)
        self.client.create_payload_index(PLACES_COLLECTION, "geo", PayloadSchemaType.GEO)
        self.client.create_payload_index(PLACES_COLLECTION, "addr_tokens", PayloadSchemaType.KEYWORD)

        # photos
        if self.client.collection_exists(PHOTOS_COLLECTION):
            self.client.delete_collection(PHOTOS_COLLECTION)
        self.client.create_collection(
            collection_name=PHOTOS_COLLECTION,
            vectors_config=VectorParams(size=VISION_VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
            hnsw_config=HnswConfigDiff(on_disk=True, m=16, ef_construct=100),
            optimizers_config=OptimizersConfigDiff(indexing_threshold=20000),
        )
        self.client.create_payload_index(PHOTOS_COLLECTION, "contenttypeid", PayloadSchemaType.KEYWORD)
        self.client.create_payload_index(PHOTOS_COLLECTION, "contentid", PayloadSchemaType.KEYWORD)
        self.client.create_payload_index(PHOTOS_COLLECTION, "geo", PayloadSchemaType.GEO)
        self.client.create_payload_index(PHOTOS_COLLECTION, "addr_tokens", PayloadSchemaType.KEYWORD)
        log.info("컬렉션 생성 완료")

    def upsert_file(self, path: str):
        """JSON 파일 하나를 읽어서 Qdrant에 upsert."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        fname = os.path.basename(path)
        log.info("[%s] %d건 업로드 시작", fname, len(data))

        success, failed = 0, 0
        for item in data:
            try:
                self._upsert_one(item)
                success += 1
                if success % 50 == 0:
                    log.info("  %s: %d건 완료", fname, success)
            except Exception as e:
                failed += 1
                log.warning("  [오류] %s: %s", item.get("title", ""), e)

        log.info("[%s] 완료: 성공 %d, 실패 %d", fname, success, failed)

    def _upsert_one(self, item: dict):
        payload = {k: v for k, v in item.items() if k != "llm_text"}
        llm_text = item.get("llm_text", "")

        contentid = item.get("contentid", "")
        # contentid를 int로 변환 (가능한 경우)
        try:
            point_id = int(contentid)
        except (ValueError, TypeError):
            point_id = abs(hash(contentid)) % (2**63)

        # ── places: text vector + sparse ──
        text_vec = self.text_model.encode(llm_text.replace("\n", " ")).astype(np.float32)
        sparse_text = _build_sparse_text(payload)
        sparse_indices, sparse_values = _build_sparse_vector(sparse_text)

        vector_payload = {"": text_vec.tolist()}
        if sparse_indices and sparse_values:
            vector_payload["text_sparse"] = SparseVector(indices=sparse_indices, values=sparse_values)

        self.client.upsert(
            collection_name=PLACES_COLLECTION,
            points=[PointStruct(id=point_id, vector=vector_payload, payload=payload)],
        )

        # ── photos: image vector ──
        import uuid
        from app.scripts.preprocess_data import download_image

        image_urls = []
        if item.get("image"):
            image_urls.append(item["image"])

        for url in image_urls:
            img = download_image(url)
            if img is None:
                continue
            img_vec = self.vision_model.encode(img).astype(np.float32)
            self.client.upsert(
                collection_name=PHOTOS_COLLECTION,
                points=[PointStruct(
                    id=str(uuid.uuid4()),
                    vector=img_vec.tolist(),
                    payload=payload,
                )],
            )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    append_mode = "--append" in sys.argv
    snapshot_mode = "--snapshot" in sys.argv
    paths = [a for a in sys.argv[1:] if a not in ("--append", "--snapshot")]

    if not paths:
        # 기본: enrich 폴더의 _enrich.json 전체
        base = Path(__file__).resolve().parents[2] / "data" / "enrich"
        paths = sorted(str(p) for p in base.glob("*_enrich.json"))

    # 폴더가 지정된 경우 내부 JSON 파일로 확장
    expanded = []
    for p in paths:
        if os.path.isdir(p):
            expanded.extend(sorted(str(f) for f in Path(p).glob("*_template.json")))
        else:
            expanded.append(p)
    paths = expanded

    log.info("모드: %s", "추가(append)" if append_mode else "재생성(recreate)")
    log.info("대상 파일: %d개", len(paths))
    for p in paths:
        log.info("  %s", os.path.basename(p))

    uploader = QdrantUploader(recreate=not append_mode)

    for p in paths:
        uploader.upsert_file(p)

    # 결과 확인
    info = uploader.client.get_collection(PLACES_COLLECTION)
    log.info("places 컬렉션: %d건", info.points_count)
    info2 = uploader.client.get_collection(PHOTOS_COLLECTION)
    log.info("photos 컬렉션: %d건", info2.points_count)

    # 스냅샷
    if snapshot_mode:
        _create_snapshots(uploader.client)


def _create_snapshots(client):
    import urllib.request

    snap_dir = Path(__file__).resolve().parents[2] / "data" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))

    for col in [PLACES_COLLECTION, PHOTOS_COLLECTION]:
        log.info("[%s] 스냅샷 생성 중...", col)
        snapshot = client.create_snapshot(collection_name=col)
        url = f"http://{host}:{port}/collections/{col}/snapshots/{snapshot.name}"
        out_path = snap_dir / f"{col}_{snapshot.name}"
        urllib.request.urlretrieve(url, str(out_path))
        size_mb = out_path.stat().st_size / 1024 / 1024
        log.info("[%s] 스냅샷 저장: %s (%.1fMB)", col, out_path.name, size_mb)


if __name__ == "__main__":
    main()
