from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.models.state import TravelState
from app.agents.models.output import IntentType
from app.utils.llm_factory import LLMFactory
from app.retrieval.place import PlaceRetriever
from app.utils.geocoder import GeoCoder


def _normalize_result(res) -> Dict[str, Any]:
    """검색 결과를 통일된 dict 형태로 정규화"""
    if isinstance(res, dict):
        payload = res.get("payload", {})
        return {
            "id": str(res.get("id", "")),
            "name": payload.get("title", ""),
            "address": payload.get("address", ""),
            "description": payload.get("description", ""),
            "category": payload.get("category", ""),
            "score": round(float(res.get("score", 0.0)), 4),
            "lat": payload.get("lat"),
            "lng": payload.get("lng"),
            "image_url": payload.get("image_url", ""),
            "distance_km": res.get("distance_km"),
        }
    else:
        # ScoredPoint 등 Qdrant 객체
        payload = getattr(res, "payload", {}) or {}
        return {
            "id": str(getattr(res, "id", "")),
            "name": payload.get("title", ""),
            "address": payload.get("address", ""),
            "description": payload.get("description", ""),
            "category": payload.get("category", ""),
            "score": round(float(getattr(res, "score", 0.0)), 4),
            "lat": payload.get("lat"),
            "lng": payload.get("lng"),
            "image_url": payload.get("image_url", ""),
            "distance_km": None,
        }


def _search_for_trip_planning(state: TravelState, retriever: PlaceRetriever) -> List[Dict[str, Any]]:
    """
    TRIP_PLANNING: planner가 생성한 itinerary의 각 항목에 대해 장소 검색
    """
    itinerary = state.get("itinerary", [])
    image_path = state.get("image_path")
    all_candidates = []
    seen_ids = set()

    for item in itinerary:
        search_query = item.get("search_query", "")
        if not search_query:
            search_query = item.get("activity", "")

        if not search_query:
            continue

        print(f"[Retriever] Searching for itinerary item: '{search_query}'")
        try:
            # itinerary 항목의 category를 필터에 활용
            item_category = item.get("category")
            results = retriever.search_hybrid(
                query=search_query,
                image_url=image_path,
                limit=3,
                category=item_category,
            )
            if results:
                for res in results:
                    normalized = _normalize_result(res)
                    if normalized["id"] not in seen_ids:
                        # 일정 항목 정보를 후보에 연결
                        normalized["itinerary_day"] = item.get("day")
                        normalized["itinerary_time_slot"] = item.get("time_slot")
                        normalized["itinerary_activity"] = item.get("activity")
                        all_candidates.append(normalized)
                        seen_ids.add(normalized["id"])
        except Exception as e:
            print(f"[Retriever] Search error for '{search_query}': {e}")

    return all_candidates


def _search_for_general(state: TravelState, retriever: PlaceRetriever) -> List[Dict[str, Any]]:
    """
    일반 검색: 사용자 입력 + 위치/이미지 기반으로 장소 검색
    """
    user_input = state.get("user_input", "")
    image_path = state.get("image_path")
    latitude = state.get("latitude")
    longitude = state.get("longitude")
    slots = state.get("slots")

    all_candidates = []
    seen_ids = set()

    # 위치 정보가 있으면 검색 쿼리에 주소 추가
    query = user_input
    if latitude and longitude:
        try:
            geocoder = GeoCoder()
            geocode_data = geocoder.reverse_geocoder(latitude, longitude)
            if geocode_data:
                road = (geocode_data.get("road_address") or "").strip()
                jibun = (geocode_data.get("jibun_address") or "").strip()
                address = " ".join(part for part in [road, jibun] if part).strip()
                if address:
                    query += f"\n위치: {address}"
                    print(f"[Retriever] Enriched query with address: {address}")
        except Exception as e:
            print(f"[Retriever] Geocoding error: {e}")

    # slots에서 category 정보 추출 및 쿼리 구성
    category = None
    if slots:
        category = slots.category if hasattr(slots, 'category') else (slots.get("category") if isinstance(slots, dict) else None)
        
        location = slots.location if hasattr(slots, 'location') else (slots.get("location") if isinstance(slots, dict) else None)
        if location and location not in query:
            query += f" {location}"
            
        themes = slots.themes if hasattr(slots, 'themes') else (slots.get("themes", []) if isinstance(slots, dict) else [])
        if themes:
            query += f" {' '.join(themes)}"
            
        must_have = slots.must_have if hasattr(slots, 'must_have') else (slots.get("must_have") if isinstance(slots, dict) else None)
        if must_have:
            query += f" {must_have}"

    # 1. 하이브리드 검색 (텍스트 + 이미지)
    print(f"[Retriever] Hybrid search query: '{query[:100]}' category={category}")
    try:
        results = retriever.search_hybrid(
            query=query,
            image_url=image_path,
            limit=5,
            category=category,
        )
        if results:
            for res in results:
                normalized = _normalize_result(res)
                if normalized["id"] not in seen_ids:
                    all_candidates.append(normalized)
                    seen_ids.add(normalized["id"])
    except Exception as e:
        print(f"[Retriever] Hybrid search error: {e}")

    # 2. 위치 기반 주변 검색 (위도/경도가 있는 경우)
    if latitude and longitude:
        print(f"[Retriever] Nearby search: lat={latitude}, lng={longitude}")
        try:
            nearby_results = retriever.search_nearby(
                lat=latitude,
                lng=longitude,
                limit=3,
                radius_km=5.0,
            )
            if nearby_results:
                for res in nearby_results:
                    normalized = _normalize_result(res)
                    if normalized["id"] not in seen_ids:
                        all_candidates.append(normalized)
                        seen_ids.add(normalized["id"])
        except Exception as e:
            print(f"[Retriever] Nearby search error: {e}")

    return all_candidates


def retriever_node(state: TravelState):
    """
    장소 검색 Agent
    1. state의 primary_intent가 TRIP_PLANNING인 경우,
    - planner가 결정한 장소 검색을 위한 정보를 바탕으로 장소를 검색한다.
    - 검색된 장소들을 state에 저장한다.
    2. 그 외,
    - 사용자의 입력을 분석해 장소(특정 장소 or 주변 장소)를 검색한다.
    - 검색된 장소들을 state에 저장한다.
    """
    print("--- Retriever Agent ---")

    # missing_slots가 있으면 (planner가 추가 정보 요청 중) 검색 생략
    missing_slots = state.get("missing_slots", [])
    if missing_slots and state.get("answer"):
        print(f"[Retriever] Skipping search — missing_slots={missing_slots}")
        return state

    primary_intent = state.get("primary_intent")
    retriever = PlaceRetriever.get_instance()

    if primary_intent == IntentType.TRIP_PLANNING:
        candidates = _search_for_trip_planning(state, retriever)
    else:
        candidates = _search_for_general(state, retriever)

    print(f"[Retriever] Total candidates: {len(candidates)}")

    return {"candidates": candidates}