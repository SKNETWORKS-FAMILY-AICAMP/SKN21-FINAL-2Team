import torch

# Model
LLM_MODEL = "gpt-4o-mini"

# Device
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# Embedding
VECTOR_SIZE = 512

# Qdrant
PLACES_COLLECTION = "places"
PHOTOS_COLLECTION = "photos"
