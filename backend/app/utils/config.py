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
