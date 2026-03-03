import random
from typing import List
from fastapi import APIRouter

from app.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION
from qdrant_client.models import Filter, FieldCondition, MatchValue

router = APIRouter(prefix="/api", tags=["recommendations"])

def get_random_places_by_type(content_type: str, limit: int = 3):
    """
    VectorDB(Qdrant)에서 특정 타입의 장소를 랜덤으로 가져오는 공통 함수입니다.
    """
    client = PlaceRetriever.get_instance().client
    
    try:
        # 1. 해당 타입의 데이터 50개를 먼저 가져온 후 랜덤 샘플링
        points, _ = client.scroll(
            collection_name=PLACES_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="contenttypeid", match=MatchValue(value=content_type))]
            ),
            limit=50,
            with_payload=True
        )
        
        if not points:
            return []
            
        sampled = random.sample(points, min(limit, len(points)))
        
        # 2. 필수 필드(contentid, name, address, image) 반환
        return [
            {
                "contentid": str(p.id),
                "name": p.payload.get("title", "Unknown"),
                "address": p.payload.get("addr") or p.payload.get("address") or "주소 정보 없음",
                "image": p.payload.get("image") or p.payload.get("firstimage", "")
            }
            for p in sampled
        ]
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch random {content_type}: {e}")
        return []

@router.get("/attractions", response_model=List[dict])
def get_random_attractions(limit: int = 3):
    """관광지 추천 상위 limit개를 반환합니다."""
    return get_random_places_by_type("관광지", limit)

@router.get("/restaurants", response_model=List[dict])
def get_random_restaurants(limit: int = 3):
    """음식점 추천 상위 limit개를 반환합니다."""
    return get_random_places_by_type("음식점", limit)
