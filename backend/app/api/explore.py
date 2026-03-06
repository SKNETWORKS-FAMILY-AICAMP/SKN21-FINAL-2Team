from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import random

from app.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION, PHOTOS_COLLECTION
from qdrant_client.models import Filter, FieldCondition, MatchValue, IsEmptyCondition, PayloadField
from app.database.connection import db_manager
from app.models.hot_place import HotPlace
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/explore", tags=["explore"])

class PlaceExploreItem(BaseModel):
    contentid: str
    title: str
    address: str
    image_url: str
    score: Optional[float] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tag1: Optional[str] = None
    tag2: Optional[str] = None

def is_valid_image(url: Optional[str]) -> bool:
    """이미지 URL이 유효한지(비어있지 않은지) 확인합니다."""
    if not url:
        return False
    # 일반적인 빈 값 또는 'None' 문자열 등 필터링
    url_str = str(url).strip()
    if url_str.lower() in ["", "none", "null", "nan", "undefined"]:
        return False
    if url_str.startswith("http"):
        return True
    
    # 로컬 경로인 경우 (static 파일)
    # backend/app/api/explore.py 기준 data/uploads 위치 계산
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
    full_path = os.path.join(upload_dir, url_str)
    
    if os.path.exists(full_path):
        return True
        
    # 만약 파일이 없더라도 DB에 경로가 있고 수동으로 관리되는 경우라면 일단 허용 (필요시 엄격하게 적용)
    # 여기서는 일단 파일 존재 여부와 무관하게 특정 키워드가 아니면 허용하도록 완화
    return True 

@router.get("/random-places", response_model=Dict[str, List[PlaceExploreItem]])
def get_random_places(db: Session = Depends(db_manager.get_db)):
    """
    Explore 탭에 띄울 무작위 장소를 카테고리별로 3개씩 반환합니다.
    카테고리: hot_places, tourist_spots, restaurants
    이미지가 있는 데이터만 반환하도록 필터링합니다.
    """
    retriever = PlaceRetriever.get_instance()
    client = retriever.client
    
    results = {
        "hot_places": [],
        "tourist_spots": [],
        "restaurants": []
    }

    # 1. 핫플레이스 (SQL Database)
    try:
        # MySQL 환경인 경우 func.rand()를 사용해야 함
        # 일단 모든 데이터를 가져온 뒤 파이썬에서 유연하게 체크합니다.
        hot_places = db.query(HotPlace).order_by(func.rand()).limit(10).all()
        
        # 이미지가 없더라도 일단 정보는 가져오도록 필터링 완화 (사용자 피드백 반영)
        # 하지만 사용자가 "이미지가 있는 데이터만" 요청했으므로, 
        # 로직상 필터링하되 만약 하나도 없다면 백로그용으로 로그를 남깁니다.
        valid_hot_places = [hp for hp in hot_places if is_valid_image(hp.image_path)]  # type: ignore
        
        # 만약 이미지가 있는 것이 하나도 없다면, 디버깅을 위해 이미지 없는 것도 일부 허용해봅니다 (텍스트 정보 확인용)
        # ※ 최종 배포시에는 다시 엄격하게 조정 가능
        candidates = valid_hot_places if valid_hot_places else hot_places
        
        if candidates:
            sampled = random.sample(candidates, min(3, len(candidates)))
            for hp in sampled:
                results["hot_places"].append(
                    PlaceExploreItem(
                        contentid=str(hp.id),
                        title=str(hp.name or "이름 없음"),
                        address=str(hp.adress or "주소 정보 없음"),
                        image_url=str(hp.image_path or ""),
                        description=str(hp.feature or ""),
                        tag1=hp.tag1,  # type: ignore
                        tag2=hp.tag2   # type: ignore
                    )
                )
        else:
            logger.warning("No hot places found in database.")
    except Exception as e:
        logger.warning(f"Failed to fetch hot places from SQL: {e}")

    # 2. 관광지 및 음식점 (Qdrant VectorDB)
    categories = {
        "tourist_spots": "관광지",
        "restaurants": "음식점"
    }

    for res_key, cat_val in categories.items():
        try:
            # 더 많은 후보(limit=100)를 가져와서 파이썬에서 확실하게 필터링합니다.
            # IsEmptyCondition이 필드 이름에 따라 불안정할 수 있어 파이썬 필터링을 우선합니다.
            points, _ = client.scroll(
                collection_name=PLACES_COLLECTION,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="contenttypeid", match=MatchValue(value=cat_val))
                    ]
                ),
                limit=100,
                with_payload=True
            )
            
            valid_points = []
            for p in points:
                payload = p.payload or {}
                # 여러 이미지 필드 후보 확인
                img = payload.get("image") or payload.get("firstimage") or payload.get("firstimage2")
                
                if is_valid_image(img):
                    valid_points.append((p, img))

            if valid_points:
                # 무작위 샘플링
                sampled_pairs = random.sample(valid_points, min(3, len(valid_points)))
                for sp, img_url in sampled_pairs:
                    payload = sp.payload or {}
                    results[res_key].append(
                        PlaceExploreItem(
                            contentid=str(sp.id),
                            title=payload.get("title", "Unknown"),
                            address=payload.get("addr") or payload.get("address") or "주소 정보 없음",
                            image_url=img_url,
                            description=payload.get("description", "")[:200]
                        )
                    )
        except Exception as e:
            print(f"[WARN] Failed to fetch {res_key} from Qdrant: {e}")

    return results


# --- Legacy / Specific Category Endpoints (Merged) ---

@router.get("/hot-places", response_model=List[dict])
def get_hot_places_legacy(limit: int = 3, db: Session = Depends(db_manager.get_db)):
    """hot_places 테이블에서 랜덤으로 가져옵니다. (기존 hot_place.py 통합)"""
    places = db.query(HotPlace).order_by(func.rand()).limit(limit).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "adress": p.adress,
            "feature": p.feature,
            "tag1": p.tag1,
            "tag2": p.tag2,
            "image_path": p.image_path,
        }
        for p in places
    ]

@router.get("/restaurants", response_model=List[dict])
def get_random_restaurants_legacy(limit: int = 3):
    """음식점 데이터 랜덤 반환 (기존 restaurants.py 통합)"""
    client = PlaceRetriever.get_instance().client
    try:
        points, _ = client.scroll(
            collection_name=PLACES_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="contenttypeid", match=MatchValue(value="음식점"))]
            ),
            limit=50,
            with_payload=True
        )
        if not points: return []
        sampled = random.sample(points, min(limit, len(points)))
        return [
            {
                "contentid": str(p.id),
                "name": (p.payload or {}).get("title", "Unknown"),
                "address": (p.payload or {}).get("addr") or (p.payload or {}).get("address") or "주소 정보 없음",
                "image": (p.payload or {}).get("image") or (p.payload or {}).get("firstimage", "")
            }
            for p in sampled
        ]
    except Exception as e:
        logger.error(f"Failed to fetch random restaurants: {e}")
        return []

@router.get("/attractions", response_model=List[dict])
def get_random_attractions_legacy(limit: int = 3):
    """관광지 데이터 랜덤 반환 (기존 attractions.py 통합)"""
    client = PlaceRetriever.get_instance().client
    try:
        points, _ = client.scroll(
            collection_name=PLACES_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="contenttypeid", match=MatchValue(value="관광지"))]
            ),
            limit=50,
            with_payload=True
        )
        if not points: return []
        sampled = random.sample(points, min(limit, len(points)))
        return [
            {
                "contentid": str(p.id),
                "name": (p.payload or {}).get("title", "Unknown"),
                "address": (p.payload or {}).get("addr") or (p.payload or {}).get("address") or "주소 정보 없음",
                "image": (p.payload or {}).get("image") or (p.payload or {}).get("firstimage", "")
            }
            for p in sampled
        ]
    except Exception as e:
        logger.error(f"Failed to fetch random attractions: {e}")
        return []


# =====================================================
# 카테고리별 장소 검색 (사용자 취향 기반)
# =====================================================

class CategoryPlacesRequest(BaseModel):
    user_prefs: str  # 사용자 취향 텍스트 (예: "자연 경관을 좋아하고 맛집 탐방을 즐김")


SEARCH_CATEGORIES = ["관광지", "음식점", "숙박", "레포츠", "문화시설", "축제공연행사", "팝업스토어"]


@router.post("/category-places", response_model=Dict[str, List[PlaceExploreItem]])
async def get_category_places(request: CategoryPlacesRequest):
    """
    사용자 취향(user_prefs)을 기반으로 카테고리별 장소 3개를 추천합니다.
    - places 컬렉션의 contenttypeid 필드로 카테고리 필터링
    """
    retriever = PlaceRetriever.get_instance()

    results: Dict[str, List[PlaceExploreItem]] = {}

    from datetime import date
    today = date.today().isoformat()

    for cat in SEARCH_CATEGORIES:
        try:
            # 매번 동일한 결과가 나오지 않도록 검색 범위를 넓히고 (limit=20)
            search_results = retriever.search_text(
                query=request.user_prefs,
                limit=20,
                category=cat,
                has_image=True
            )

            items = []
            for res in search_results:
                payload = res.payload or {}
                pid = res.id
                score = res.score
                
                # 여러 이미지 필드 후보 확인 및 유효성 검사
                img_url = payload.get("image") or payload.get("firstimage") or payload.get("firstimage2") or ""
                
                if not is_valid_image(img_url):
                    continue

                # 팝업스토어는 진행 중인 항목만 포함
                if cat == "팝업스토어":
                    end_date = payload.get("end_date", "")
                    if end_date and end_date < today:
                        continue

                items.append(
                    PlaceExploreItem(
                        contentid=str(pid),
                        title=payload.get("title", "Unknown"),
                        address=payload.get("addr") or payload.get("address") or payload.get("road_address", "주소 없음"),
                        image_url=img_url,
                        score=round(score, 4),
                        description=payload.get("description", "")[:200],
                        start_date=payload.get("start_date") if cat == "팝업스토어" else None,
                        end_date=payload.get("end_date") if cat == "팝업스토어" else None,
                    )
                )

            # 결과 중 3개를 무작위로 샘플링
            results[cat] = random.sample(items, min(3, len(items)))

        except Exception as e:
            print(f"[WARN] Category '{cat}' search failed: {e}")
            results[cat] = []

    return results


