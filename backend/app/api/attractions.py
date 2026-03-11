import random
from typing import List
from fastapi import APIRouter

from app.core.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION
from app.utils.common import to_client_image_url
from qdrant_client.models import Filter, FieldCondition, MatchValue

router = APIRouter(prefix="/api/attractions", tags=["attractions"])

@router.get("", response_model=List[dict])
def get_random_attractions(limit: int = 3):
    """
    관광지 데이터를 VectorDB(Qdrant)에서 랜덤으로 가져옵니다.
    hot_place.py와 유사하게 간결한 형식을 유지합니다.
    """
    client = PlaceRetriever.get_instance().client
    
    try:
        # 1. '관광지' 데이터 50개를 먼저 가져온 후 랜덤 샘플링 (무작위성 확보)
        points, _ = client.scroll(
            collection_name=PLACES_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="contenttypeid", match=MatchValue(value="관광지"))]
            ),
            limit=50,
            with_payload=True
        )
        
        if not points:
            return []
            
        sampled = random.sample(points, min(limit, len(points)))
        
        # 2. 필수 필드(contentid, name, address, image)만 포함하여 반환
        return [
            {
                "contentid": str(p.id),
                "name": p.payload.get("title", "Unknown"),
                "address": p.payload.get("addr") or p.payload.get("address") or "주소 정보 없음",
                "image": to_client_image_url(p.payload.get("image") or p.payload.get("firstimage", ""))
            }
            for p in sampled
        ]
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch random attractions: {e}")
        return []
