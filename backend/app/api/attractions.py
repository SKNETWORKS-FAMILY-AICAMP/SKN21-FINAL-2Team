from typing import List

from fastapi import APIRouter

from app.core.retrieval.place import PlaceRetriever
from app.utils.qdrant_utils import scroll_random_places

router = APIRouter(prefix="/api/attractions", tags=["attractions"])


@router.get("", response_model=List[dict])
def get_random_attractions(limit: int = 3):
    """관광지 데이터를 VectorDB(Qdrant)에서 랜덤으로 가져옵니다."""
    client = PlaceRetriever.get_instance().client
    return scroll_random_places(client, "관광지", limit)
