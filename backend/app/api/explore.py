from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import random

from app.retrieval.place import PlaceRetriever
from app.core.config import PLACES_COLLECTION, PHOTOS_COLLECTION
from qdrant_client.models import Filter, FieldCondition, MatchValue

router = APIRouter(prefix="/api/explore", tags=["explore"])

class PlaceExploreResponse(BaseModel):
    contentid: str
    title: str
    address: str
    image_url: str

@router.get("/random-places", response_model=Dict[str, List[PlaceExploreResponse]])
def get_random_places():
    """
    Explore 탭에 띄울 무작위 장소를 카테고리별 콜렉션에서 3개씩 반환합니다.
    카테고리 콜렉션 (예정): 핫플, 음식점, 관광지, 콘텐츠
    """
    retriever = PlaceRetriever.get_instance()
    client = retriever.client
    
    # 카테고리와 매핑될 Qdrant Collection 이름 정의
    # (실제 생성할 콜렉션 이름에 맞게 수정 가능)
    # 추후 '핫플', '음식점', '관광지', '콘텐츠' 콜렉션이 각각 생성된다고 가정
    category_collections = {
        "핫플": "hotplaces",      # 핫플 컬렉션 예시 (명칭 추후 확정)
        "음식점": "restaurants",  # 음식점 컬렉션 예시
        "관광지": "attractions",  # 관광지 컬렉션 예시
        "콘텐츠": "contents"      # 콘텐츠 컬렉션 예시
    }

    results = {
        "핫플": [],
        "음식점": [],
        "관광지": [],
        "콘텐츠": []
    }

    for cat_name, collection_name in category_collections.items():
        all_points = []
        offset = None
        
        # 각 콜렉션이 존재하는지 확인 (예외 방지)
        try:
            while True:
                points, offset = client.scroll(
                    collection_name=collection_name,
                    limit=100,
                    with_payload=True,
                    offset=offset,
                    with_vectors=False
                )
                all_points.extend(points)
                if offset is None:
                    break
        except Exception as e:
            # 아직 컬렉션이 없거나 연결 오류 시 빈 리스트로 처리
            print(f"[WARN] Failed to scroll collection '{collection_name}': {e}")
            all_points = []

        if not all_points:
            continue
            
        # 데이터가 겹칠 수 있으므로 고유 장소 ID 기준 중복 제거
        unique_points = list({p.id: p for p in all_points}.values())
        sampled = random.sample(unique_points, min(3, len(unique_points)))
        
        for sp in sampled:
            pid = sp.id
            payload = sp.payload or {}
            
            # PHOTOS_COLLECTION에서 사진이 있으면 1장 조회
            # 모든 장소의 사진이 PHOTOS_COLLECTION에 통합 관리된다고 가정
            image_url = ""
            try:
                photos_response, _ = client.scroll(
                    collection_name=PHOTOS_COLLECTION,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="place_id", match=MatchValue(value=pid))]
                    ),
                    limit=1,
                    with_payload=True
                )
                
                if photos_response and photos_response[0].payload:
                    image_url = photos_response[0].payload.get("image_url", "")
            except Exception as e:
                print(f"[WARN] Failed to fetch photo for place_id {pid}: {e}")
                
            if not image_url:
                image_url = payload.get("firstimage", "")
                
            results[cat_name].append(
                PlaceExploreResponse(
                    contentid=str(pid),
                    title=payload.get("title", "Unknown"),
                    address=payload.get("address", "Unknown"),
                    image_url=image_url
                )
            )

    return results
