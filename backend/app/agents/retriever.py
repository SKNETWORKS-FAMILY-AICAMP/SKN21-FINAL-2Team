from typing import Dict, Any, List
from app.agents.models.state import TravelState
from app.agents.models.output import IntentType
from app.retrieval.place import PlaceRetriever
from app.utils.geocoder import GeoCoder
from app.services.vision import describe_image
import asyncio
import random
import time


def _candidate_category(candidate: Dict[str, Any]) -> str:
    payload = candidate.get("payload", {})
    # 분산 기준 카테고리 우선순위
    return (
        str(payload.get("cat3") or "").strip()
        or str(payload.get("cat2") or "").strip()
        or str(payload.get("cat1") or "").strip()
        or "unknown"
    )


def _candidate_score(candidate: Dict[str, Any]) -> float:
    try:
        return max(float(candidate.get("score", 0.0)), 1e-6)
    except Exception:
        return 1e-6


def _pick_diverse_candidates(candidates: List[Dict[str, Any]], final_k: int = 5, top_pool: int = 12) -> List[Dict[str, Any]]:
    """
    상위 후보 풀에서 점수 가중 랜덤 샘플링 + 카테고리 분산을 적용해
    매 요청마다 장소 구성이 고정되지 않도록 한다.
    """
    if len(candidates) <= final_k:
        return candidates

    pool = list(candidates[:min(len(candidates), top_pool)])
    selected: List[Dict[str, Any]] = []
    used_categories = set()
    rng = random.Random(time.time_ns())

    while pool and len(selected) < final_k:
        unseen_pool = [c for c in pool if _candidate_category(c) not in used_categories]
        source = unseen_pool if unseen_pool else pool
        weights = [_candidate_score(c) for c in source]
        picked = rng.choices(source, weights=weights, k=1)[0]

        selected.append(picked)
        used_categories.add(_candidate_category(picked))
        pool.remove(picked)

    return selected

async def _search_for_trip_planning(state: TravelState, emotional_text: str = None) -> List[Dict[str, Any]]:
    """
    TRIP_PLANNING: planner가 생성한 itinerary의 각 항목에 대해 장소 검색
    """
    retriever = PlaceRetriever.get_instance()

    itinerary = state.get("itinerary", [])
    image_path = state.get("image_path")
    
    if not itinerary:
        return []

    # trip_concurrency: 병렬로 최대한 몇개 장소 검색할것인지? 10개라고 하면 최대 3개씩 병렬 검색
    trip_concurrency = 3
    semaphore = asyncio.Semaphore(trip_concurrency)

    async def search_item(item):
        async with semaphore:
            search_query = item.get("search_query", "")
            if not search_query:
                search_query = item.get("activity", "")

            if not search_query:
                return []

            print(f"[Retriever] Searching for itinerary item: '{search_query}'")
            try:
                # itinerary 항목의 category를 필터에 활용
                item_category = item.get("category")
                results = await retriever.search_hybrid(
                    query=search_query,
                    image_url=image_path,
                    limit=3,
                    category=item_category,
                    emotional_text=emotional_text
                )
                return results
            except Exception as e:
                print(f"[Retriever] Search error for '{search_query}': {e}")
                return []

    # 병렬 검색 실행
    tasks = [search_item(item) for item in itinerary]
    all_results_lists = await asyncio.gather(*tasks)
    
    # 리스트 평탄화
    all_candidates = [res for sublist in all_results_lists for res in sublist]
    return all_candidates


async def _search_for_general(state: TravelState, emotional_text: str = None) -> List[Dict[str, Any]]:
    """
    일반 검색: 사용자 입력 + 위치/이미지 기반으로 장소 검색
    """
    retriever = PlaceRetriever.get_instance()

    user_input = state.get("user_input", "")
    image_path = state.get("image_path")
    latitude = state.get("latitude")
    longitude = state.get("longitude")
    slots = state.get("slots")

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

    # 1. 하이브리드 검색 (텍스트 + 이미지)
    print(f"[Retriever] Hybrid search query: '{query[:100]}' category={category}")
    results = []
    try:
        results = await retriever.search_hybrid(
            query=query,
            image_url=image_path,
            limit=5,
            category=category,
            emotional_text=emotional_text
        )
    except Exception as e:
        print(f"[Retriever] Hybrid search error: {e}")

    return results


async def retriever_node(state: TravelState):
    """
    장소 검색 Agent
    """
    print("--- Retriever Agent ---")

    # missing_slots가 있으면 (planner가 추가 정보 요청 중) 검색 생략
    missing_slots = state.get("missing_slots", None)
    if missing_slots:
        print(f"[Retriever] Skipping search — missing_slots={missing_slots}")
        return state

    image_path = state.get("image_path")
    emotional_text = None
    if image_path:
        print(f"[Retriever] Image detected. Fetching description once...")
        emotional_text = await describe_image(image_path)

    primary_intent = state.get("primary_intent")

    print(f"[Retriever] Start General search!!!! primary intent: {primary_intent}")
    candidates = await _search_for_general(state, emotional_text=emotional_text)

    if primary_intent == IntentType.TRIP_PLANNING:
        print("[Retriever] Start Trip planning search!!!!")
        trip_candidates = await _search_for_trip_planning(state, emotional_text=emotional_text)
        candidates.extend(trip_candidates)

    print(f"[Retriever] Total candidates count: {len(candidates)}")

    # 중복 제거 (place_id 기준)
    seen_ids = set()
    unique_candidates = []
    for c in candidates:
        pid = c.get("id")
        if pid not in seen_ids:
            unique_candidates.append(c)
            seen_ids.add(pid)

    diversified_candidates = _pick_diverse_candidates(unique_candidates, final_k=5, top_pool=12)
    return {"candidates": diversified_candidates}
