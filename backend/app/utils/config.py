import os
import torch

# Model
LLM_MODEL = "gpt-4o-mini"

# Device
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# Embedding
TEXT_MODEL = "BAAI/bge-m3"
VISION_MODEL = "clip-ViT-L-14"
TEXT_VECTOR_SIZE = 1024
VISION_VECTOR_SIZE = 768

# Legacy (will be updated in collections)
VECTOR_SIZE = 768 # Standardizing to vision size for now or keep for legacy reference

# Qdrant
PLACES_COLLECTION = "places"
PHOTOS_COLLECTION = "photos"

# Agent
RETRIEVAL_PROFILE = os.getenv("RETRIEVAL_PROFILE", "serving").lower()

SERVING_RETRIEVER_CANDIDATE_K = 20
SERVING_RETRIEVER_RERANK_MAX_K = 8
SERVING_RETRIEVER_TOP_K = 5

EVAL_RETRIEVER_CANDIDATE_K = 60
EVAL_RETRIEVER_RERANK_MAX_K = 30
EVAL_RETRIEVER_TOP_K = 10


def get_retrieval_params(profile: str | None = None) -> dict[str, int]:
    effective = (profile or RETRIEVAL_PROFILE or "serving").lower()
    if effective == "evaluation":
        return {
            "candidate_k": EVAL_RETRIEVER_CANDIDATE_K,
            "top_k": EVAL_RETRIEVER_TOP_K,
            "rerank_max_k": EVAL_RETRIEVER_RERANK_MAX_K,
        }
    # fallback 포함 serving 기본
    return {
        "candidate_k": SERVING_RETRIEVER_CANDIDATE_K,
        "top_k": SERVING_RETRIEVER_TOP_K,
        "rerank_max_k": SERVING_RETRIEVER_RERANK_MAX_K,
    }


# BM25 최적화
BM25_POOL_LIMIT = 100
BM25_ENABLE_THRESHOLD = 20
BM25_ENABLE_SCORE_THRESHOLD = 0.22

# Sparse/Geo 보강 플래그
ENABLE_ADDR_SPARSE_BOOST = False
ENABLE_QDRANT_SPARSE = False
ENABLE_GEO_FILTER = True
SPARSE_ADDR_EXACT_WEIGHT = 0.04
SPARSE_ADDR_STEM_WEIGHT = 0.02
SPARSE_ADDR_MAX_BOOST = 0.20

# Score 스케일 균형
# RRF first_stage_score(0.010~0.050) 대비 boost 합계(최대 0.65) 스케일 불균형을 보정.
# boost * BOOST_WEIGHT ≈ 최대 0.195 → RRF 점수와 유사한 스케일로 정규화.
BOOST_WEIGHT = float(os.getenv("BOOST_WEIGHT", "0.3"))

# Qdrant 채널별 candidates_limit 배수 (#8)
# candidates_limit = candidate_k * CANDIDATE_LIMIT_MULTIPLIER
# 기존 *5(100개)는 과도한 메모리/CPU 사용. *3으로 줄여도 RRF 융합에 충분한 pool 확보 가능.
CANDIDATE_LIMIT_MULTIPLIER = int(os.getenv("CANDIDATE_LIMIT_MULTIPLIER", "3"))

# Geo proximity boost 반경 (#9)
# 기본값 20km → 서울 전역 + 경기 일부까지 포함되어 "근처" 의도 희석.
# 10km로 줄이면 시내 이동 범위에 집중.
GEO_PROXIMITY_RADIUS_KM = float(os.getenv("GEO_PROXIMITY_RADIUS_KM", "10.0"))

# 점수 정규화 기준값 — 결과 필드를 [0.0, 1.0] 범위로 표시하기 위한 참조 최대값
# RRF_SCORE_MAX : first_stage_score 상한 (모든 채널이 동시에 1위인 이론적 최대)
# FUSED_SCORE_MAX: score 상한 (first_stage_score 최대 + BOOST_WEIGHT * 최대 boost)
# MAX_BOOST_SUM  : raw boost 합계 상한 (addr_sparse 포함 모든 보너스가 최대인 경우)
RRF_SCORE_MAX   = 0.08
FUSED_SCORE_MAX = 0.20
MAX_BOOST_SUM   = 0.65
