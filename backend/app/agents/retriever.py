from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.models.state import TravelState
from app.agents.models.output import IntentType
from app.utils.llm_factory import LLMFactory
from app.retrieval.place import PlaceRetriever
from app.utils.geocoder import GeoCoder

def _search_for_trip_planning(state: TravelState) -> List[Dict[str, Any]]:
    """
    TRIP_PLANNING: planner가 생성한 itinerary의 각 항목에 대해 장소 검색
    """
    retriever = PlaceRetriever.get_instance()

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
        except Exception as e:
            print(f"[Retriever] Search error for '{search_query}': {e}")

    return results


def _search_for_general(state: TravelState) -> List[Dict[str, Any]]:
    """
    일반 검색: 사용자 입력 + 위치/이미지 기반으로 장소 검색
    """
    retriever = PlaceRetriever.get_instance()

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
                if road:
                    query += f"\n현재 내 위치 주소: {road}"
                if jibun:
                    query += f"\n현재 내 위치 구주소: {jibun}"
        except Exception as e:
            print(f"[Retriever] Geocoding error: {e}")

    # slots에서 category 정보 추출 및 쿼리 구성
    category = None
    if slots:
        category = slots.category if hasattr(slots, 'category') else (slots.get("category") if isinstance(slots, dict) else None)
        
        # if location and location not in query:
        #     query += f"\n 관심 장소 주소: {location}"
                        
        # must_have = slots.must_have if hasattr(slots, 'must_have') else (slots.get("must_have") if isinstance(slots, dict) else None)
        # if must_have:
        #     query += f"\n 필수 포함 정보: {must_have}"
        
        # nice_to_have = slots.nice_to_have if hasattr(slots, 'nice_to_have') else (slots.get("nice_to_have") if isinstance(slots, dict) else None)
        # if nice_to_have:
        #     query += f"\n 있으면 좋은 정보: {nice_to_have}"

    # 1. 하이브리드 검색 (텍스트 + 이미지)
    print(f"[Retriever] Hybrid search query: '{query[:100]}' category={category}")
    results = []
    try:
        results = retriever.search_hybrid(
            query=query,
            image_url=image_path,
            limit=5,
            category=category,
        )
    except Exception as e:
        print(f"[Retriever] Hybrid search error: {e}")

    return results


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
    missing_slots = state.get("missing_slots", None)
    if missing_slots:
        print(f"[Retriever] Skipping search — missing_slots={missing_slots}")
        return state

    primary_intent = state.get("primary_intent")

    print(f"[Retriever] Start General search!!!! primary intent: {primary_intent}")
    candidates = _search_for_general(state)

    if primary_intent == IntentType.TRIP_PLANNING:
        print("[Retriever] Start Trip planning search!!!!")
        candidates.extend(_search_for_trip_planning(state))

    print(f"[Retriever] Total candidates: {candidates}")

    # 중복 제거
    

    return {"candidates": candidates}