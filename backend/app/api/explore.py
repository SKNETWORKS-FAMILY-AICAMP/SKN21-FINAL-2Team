from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import random

from app.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION, PHOTOS_COLLECTION
from app.utils.common import to_client_image_url
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
def get_random_places(categories: Optional[str] = None, limit: int = 3, db: Session = Depends(db_manager.get_db)):
    """
    Explore 탭에 띄울 무작위 장소를 요청된 카테고리별로 반환합니다.
    예: ?categories=hot_places,tourist_spots,restaurants,팝업스토어
    - hot_places는 MySQL (RDB)에서 조회
    - 그 외(관광지, 음식점, 팝업스토어 등)는 Qdrant (Vector DB)에서 조회
    """
    retriever = PlaceRetriever.get_instance()
    client = retriever.client
    
    # 쉼표로 구분된 카테고리 파싱, 안 들어오면 기본값 3개
    requested_cats = [c.strip() for c in categories.split(",")] if categories else ["hot_places", "tourist_spots", "restaurants"]
    
    # Qdrant 내부 contenttypeid 매핑용 (영문 키워드가 들어올 수 있으므로 매핑)
    # 한글 카테고리(예: '팝업스토어')가 들어오면 그대로 사용합니다.
    qdrant_cat_map = {
        "tourist_spots": "관광지",
        "restaurants": "음식점",
        "activities": "축제공연행사",
        "accommodations": "숙박"
    }

    results = {cat: [] for cat in requested_cats}

    # 1. 핫플레이스 (SQL Database)
    if "hot_places" in requested_cats:
        try:
            hot_places = db.query(HotPlace).order_by(func.rand()).limit(limit * 3).all()
            valid_hot_places = [hp for hp in hot_places if is_valid_image(hp.image_path)]  # type: ignore
            candidates = valid_hot_places if valid_hot_places else hot_places
            
            if candidates:
                sampled = random.sample(candidates, min(limit, len(candidates)))
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

    # 2. Vector DB 조회 카테고리들
    vector_cats = [cat for cat in requested_cats if cat != "hot_places"]
    
    for req_cat in vector_cats:
        # 매핑된 한글 분류값 가져오기 (매핑 시도가 없으면 요청된 문자열 그대로, ex: "팝업스토어")
        actual_qdrant_val = qdrant_cat_map.get(req_cat, req_cat)
        
        try:
            # Category 명칭으로 Qdrant 검색
            points, _ = client.scroll(
                collection_name=PLACES_COLLECTION,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="contenttypeid", match=MatchValue(value=actual_qdrant_val))
                    ]
                ),
                limit=100,
                with_payload=True
            )
            
            valid_points = []
            for p in points:
                payload = p.payload or {}
                img = payload.get("image") or payload.get("firstimage") or payload.get("firstimage2")
                
                # 팝업스토어는 과거 종료된 항목 필터링
                if actual_qdrant_val == "팝업스토어":
                    from datetime import date
                    today = date.today().isoformat()
                    end_date = payload.get("end_date", "")
                    if end_date and end_date < today:
                        continue

                if is_valid_image(img):
                    valid_points.append((p, img))

            if valid_points:
                sampled_pairs = random.sample(valid_points, min(limit, len(valid_points)))
                for sp, img_url in sampled_pairs:
                    payload = sp.payload or {}
                    results[req_cat].append(
                        PlaceExploreItem(
                            contentid=str(sp.id),
                            title=payload.get("title", "Unknown"),
                            address=payload.get("addr") or payload.get("address") or "주소 정보 없음",
                            image_url=to_client_image_url(img_url),
                            description=payload.get("description", "")[:200],
                            start_date=payload.get("start_date") if actual_qdrant_val == "팝업스토어" else None,
                            end_date=payload.get("end_date") if actual_qdrant_val == "팝업스토어" else None
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch {req_cat} from Qdrant: {e}")

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
                img_url = to_client_image_url(payload.get("image", payload.get("firstimage", "")))
                
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

