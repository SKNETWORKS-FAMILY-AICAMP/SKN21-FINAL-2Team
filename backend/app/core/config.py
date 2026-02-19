import torch

# Model
LLM_MODEL = "gpt-4o-mini"

# Device
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# Embedding Models
TEXT_MODEL = "BAAI/bge-m3"
CLIP_MODEL = "clip-ViT-B-32"

# Vector Dimensions
TEXT_VECTOR_SIZE = 1024  # BGE-M3
IMG_VECTOR_SIZE = 512    # CLIP

# Qdrant
PLACES_COLLECTION = "places"
PHOTOS_COLLECTION = "photos"
