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

SERVING_RETRIEVER_CANDIDATE_K = int(os.getenv("SERVING_RETRIEVER_CANDIDATE_K", "20"))
SERVING_RETRIEVER_TOP_K = int(os.getenv("SERVING_RETRIEVER_TOP_K", "5"))
SERVING_RETRIEVER_RERANK_MAX_K = int(os.getenv("SERVING_RETRIEVER_RERANK_MAX_K", "8"))

EVAL_RETRIEVER_CANDIDATE_K = int(os.getenv("EVAL_RETRIEVER_CANDIDATE_K", "60"))
EVAL_RETRIEVER_TOP_K = int(os.getenv("EVAL_RETRIEVER_TOP_K", "10"))
EVAL_RETRIEVER_RERANK_MAX_K = int(os.getenv("EVAL_RETRIEVER_RERANK_MAX_K", "30"))


def get_retrieval_params(profile: str | None = None) -> dict[str, int]:
    effective = (profile or RETRIEVAL_PROFILE or "serving").lower()
    if effective == "evaluation":
        return {
            "candidate_k": max(EVAL_RETRIEVER_CANDIDATE_K, 1),
            "top_k": max(EVAL_RETRIEVER_TOP_K, 1),
            "rerank_max_k": max(EVAL_RETRIEVER_RERANK_MAX_K, 1),
        }
    # fallback 포함 serving 기본
    return {
        "candidate_k": max(SERVING_RETRIEVER_CANDIDATE_K, 1),
        "top_k": max(SERVING_RETRIEVER_TOP_K, 1),
        "rerank_max_k": max(SERVING_RETRIEVER_RERANK_MAX_K, 1),
    }


# 하위 호환 alias
_retrieval_defaults = get_retrieval_params(RETRIEVAL_PROFILE)
RETRIEVER_CANDIDATE_K = _retrieval_defaults["candidate_k"]
RETRIEVER_TOP_K = _retrieval_defaults["top_k"]
RETRIEVER_RERANK_MAX_K = _retrieval_defaults["rerank_max_k"]

# BM25 최적화
BM25_POOL_LIMIT = 100
BM25_ENABLE_THRESHOLD = 20
BM25_ENABLE_SCORE_THRESHOLD = 0.22

# Sparse/Geo 보강 플래그
ENABLE_SPARSE = os.getenv("ENABLE_SPARSE", "false").lower() in {"1", "true", "yes", "on"}
ENABLE_GEO_FILTER = os.getenv("ENABLE_GEO_FILTER", "true").lower() in {"1", "true", "yes", "on"}
ENABLE_QDRANT_SPARSE = os.getenv("ENABLE_QDRANT_SPARSE", "false").lower() in {"1", "true", "yes", "on"}
SPARSE_ADDR_EXACT_WEIGHT = float(os.getenv("SPARSE_ADDR_EXACT_WEIGHT", "0.04"))
SPARSE_ADDR_STEM_WEIGHT = float(os.getenv("SPARSE_ADDR_STEM_WEIGHT", "0.02"))
SPARSE_ADDR_MAX_BOOST = float(os.getenv("SPARSE_ADDR_MAX_BOOST", "0.20"))
