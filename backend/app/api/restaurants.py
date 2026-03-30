from typing import List

from fastapi import APIRouter

from app.core.retrieval.place import PlaceRetriever
from app.utils.qdrant_utils import scroll_random_places

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


@router.get("", response_model=List[dict])
def get_random_restaurants(limit: int = 3):
    """음식점 데이터를 VectorDB(Qdrant)에서 랜덤으로 가져옵니다."""
    client = PlaceRetriever.get_instance().client
    return scroll_random_places(client, "음식점", limit)
