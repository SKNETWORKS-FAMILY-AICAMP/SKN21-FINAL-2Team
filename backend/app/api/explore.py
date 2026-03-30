from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION
from app.utils.common import to_client_image_url
from app.utils.qdrant_utils import scroll_random_places
from qdrant_client.models import Filter, FieldCondition, MatchAny
from app.database.connection import db_manager
from app.models.hot_place import HotPlace
from app.agents.models.output import CategoryType
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
    category: Optional[str] = None
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
    
    # 영문 키워드 → 한글 contenttypeid 매핑 (DB 실존 값: 관광지, 콘텐츠, 숙박, 음식점, 투어)
    qdrant_cat_map = {
        "tourist_spots": "관광지",
        "restaurants": "음식점",
        "tour_courses": "투어",
        "accommodations": "숙박",
        "contents": "콘텐츠",
        "콘텐츠": "콘텐츠",
        "숙박": "숙박",
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
        # 영문 → 한글 매핑 (매핑 없으면 그대로 사용)
        korean_val = qdrant_cat_map.get(req_cat, req_cat)
        db_values = [korean_val]

        try:
            # MatchAny로 복수 DB값을 OR 조건으로 검색
            points, _ = client.scroll(
                collection_name=PLACES_COLLECTION,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="contenttypeid", match=MatchAny(any=db_values))
                    ]
                ),
                limit=100,
                with_payload=True
            )
            
            valid_points = []
            for p in points:
                payload = p.payload or {}
                img = payload.get("image") or payload.get("firstimage") or payload.get("firstimage2")

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
                            category=payload.get("category") if "콘텐츠" in db_values else None,
                            start_date=payload.get("start_date") if "콘텐츠" in db_values else None,
                            end_date=payload.get("end_date") if "콘텐츠" in db_values else None,
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
    return scroll_random_places(client, "음식점", limit)


@router.get("/attractions", response_model=List[dict])
def get_random_attractions_legacy(limit: int = 3):
    """관광지 데이터 랜덤 반환 (기존 attractions.py 통합)"""
    client = PlaceRetriever.get_instance().client
    return scroll_random_places(client, "관광지", limit)


# =====================================================
# 카테고리별 장소 검색 (사용자 취향 기반)
# =====================================================

class CategoryPlacesRequest(BaseModel):
    user_prefs: str  # 사용자 취향 텍스트 (예: "자연 경관을 좋아하고 맛집 탐방을 즐김")


SEARCH_CATEGORIES = ["관광지", "음식점", "투어"]


@router.post("/category-places", response_model=Dict[str, List[PlaceExploreItem]])
def get_category_places(request: CategoryPlacesRequest):
    """
    사용자 취향(user_prefs)을 기반으로 카테고리별 장소 3개를 추천합니다.
    - places 컬렉션의 contenttypeid 필드로 카테고리 필터링
    - 인코딩 1회 + 3개 카테고리 병렬 Qdrant 검색으로 응답 시간 단축
    """
    retriever = PlaceRetriever.get_instance()

    # 인코딩 1회만 수행
    query_vec = retriever.text_model.encode(request.user_prefs).astype(np.float32)

    def search_category(cat: str):
        matched_enum = next((ct for ct in CategoryType if ct.value == cat), None)
        try:
            search_results = retriever.search_by_vector(
                query_vec=query_vec,
                limit=20,
                categories=[matched_enum] if matched_enum else None,
                has_image=True,
            )
        except Exception as e:
            print(f"[WARN] Category '{cat}' search failed: {e}")
            return cat, []

        items = []
        for res in search_results:
            payload = res.payload or {}
            img_url = to_client_image_url(payload.get("image", payload.get("firstimage", "")))
            if not is_valid_image(img_url):
                continue
            items.append(
                PlaceExploreItem(
                    contentid=str(res.id),
                    title=payload.get("title", "Unknown"),
                    address=payload.get("addr") or payload.get("address") or payload.get("road_address", "주소 없음"),
                    image_url=img_url,
                    score=round(res.score, 4),
                    description=payload.get("description", "")[:200],
                )
            )
        return cat, random.sample(items, min(3, len(items)))

    # 3개 카테고리 병렬 검색
    results: Dict[str, List[PlaceExploreItem]] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(search_category, cat): cat for cat in SEARCH_CATEGORIES}
        for future in as_completed(futures):
            cat, items = future.result()
            results[cat] = items

    return results

