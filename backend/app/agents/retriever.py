import asyncio
import random
from typing import Dict, Any, List

from app.agents.models.state import TravelState, get_effective_user_input
from app.agents.models.output import IntentType, InputType
from app.retrieval.place import PlaceRetriever
from app.utils.geocoder import GeoCoder
from app.utils.vision import describe_image
from app.utils.common import getattr_safe
from app.utils.place_id import get_candidate_point_id, get_place_id

from app.utils.config import get_retrieval_params


def _candidate_category(candidate: Dict[str, Any]) -> str:
    payload = candidate.get("payload", {})
    # 카테고리 필드는 아래 우선순위로 통일
    return (
        str(payload.get("contenttypeid") or "").strip()
        or str(payload.get("category") or "").strip()
        or "unknown"
    )

def _candidate_score(candidate: Dict[str, Any]) -> float:
    try:
        return max(float(candidate.get("score", 0.0)), 1e-6)
    except Exception:
        return 1e-6


def _resolve_search_scope(
    primary_intent: IntentType | None,
    slots: Any,
    image_path: str | None,
) -> str:
    """검색 범위를 단일 컬렉션으로 제한하기 위한 스코프 결정."""
    if primary_intent == IntentType.TRIP_PLANNING:
        return "place_only"

    if not image_path:
        return "place_only"

    input_type = None
    if slots:
        input_type = getattr_safe(slots, "input_type")

    if primary_intent == IntentType.IMAGE_SIMILAR:
        return "photo_only"

    if input_type == InputType.IMAGE or str(input_type) == str(InputType.IMAGE.value):
        return "photo_only"

    return "place_only"


def _pick_diverse_candidates_deterministic(candidates: List[Dict[str, Any]], final_k: int, top_pool: int) -> List[Dict[str, Any]]:
    """결정론 모드: 점수 우선 + 카테고리 분산 tie-break."""
    if len(candidates) <= final_k:
        return candidates

    pool = list(candidates[: min(len(candidates), top_pool)])
    selected: List[Dict[str, Any]] = []
    used_categories = set()

    # 1차: 카테고리 중복 최소화
    for c in pool:
        cat = _candidate_category(c)
        if cat not in used_categories:
            selected.append(c)
            used_categories.add(cat)
            if len(selected) >= final_k:
                return selected

    # 2차: 남은 슬롯은 점수 순으로 채움
    selected_ids = {get_place_id(c) for c in selected}
    for c in pool:
        cid = get_place_id(c)
        if cid and cid not in selected_ids:
            selected.append(c)
            selected_ids.add(cid)
            if len(selected) >= final_k:
                break

    return selected


def _pick_diverse_candidates_explore(
    candidates: List[Dict[str, Any]], final_k: int, top_pool: int, seed: int | None = None
) -> List[Dict[str, Any]]:
    """탐색 모드: 시드 기반 랜덤 다양화."""
    if len(candidates) <= final_k:
        return candidates

    pool = list(candidates[: min(len(candidates), top_pool)])
    selected: List[Dict[str, Any]] = []
    used_categories = set()
    rng = random.Random(seed)

    while pool and len(selected) < final_k:
        unseen_pool = [c for c in pool if _candidate_category(c) not in used_categories]
        source = unseen_pool if unseen_pool else pool
        weights = [_candidate_score(c) for c in source]
        picked = rng.choices(source, weights=weights, k=1)[0]

        selected.append(picked)
        used_categories.add(_candidate_category(picked))
        pool.remove(picked)

    return selected


def _pick_candidates(
    candidates: List[Dict[str, Any]],
    final_k: int = 5,
    top_pool: int = 20,
    selection_mode: str = "deterministic",
    seed: int | None = None,
) -> List[Dict[str, Any]]:
    if selection_mode == "explore":
        return _pick_diverse_candidates_explore(candidates, final_k=final_k, top_pool=top_pool, seed=seed)
    return _pick_diverse_candidates_deterministic(candidates, final_k=final_k, top_pool=top_pool)


async def _search_for_trip_planning(
    state: TravelState,
    emotional_text: str | None = None,
    candidate_k: int = 20,
    rerank_max_k: int = 8,
) -> List[Dict[str, Any]]:
    """TRIP_PLANNING: planner itinerary 기반 후보 검색."""
    retriever = PlaceRetriever.get_instance()

    itinerary = state.get("itinerary", [])
    image_path = state.get("image_path")

    if not itinerary:
        return []

    # Semaphore(3) : 병렬로 최대한 몇개 장소 검색할것인지? 10개라고 하면 최대 3개씩 병렬 검색
    semaphore = asyncio.Semaphore(3)

    async def search_item(item):
        async with semaphore:
            search_query = item.get("search_query", "") or item.get("activity", "")
            print("[Retriever - search planning] query: ", search_query)
            if not search_query:
                return []

            try:
                item_category = item.get("category")
                # itinerary 항목별 검색은 전체 K를 쓰지 않고 상위 일부만 취합
                return await retriever.search_hybrid(
                    query=search_query,
                    image_url=image_path,
                    limit=max(10, candidate_k // 3),
                    candidate_k=max(10, candidate_k // 3),
                    category=item_category,
                    emotional_text=emotional_text,
                    user_latitude=state.get("latitude"),
                    user_longitude=state.get("longitude"),
                    preferred_location=getattr_safe(state.get("slots"), "location"),
                    enable_bm25=True,
                    enable_rerank=True,
                    rerank_top_k=min(rerank_max_k, max(10, candidate_k // 3)),
                    search_scope="place_only",
                )
            except Exception as e:
                print(f"[Retriever] Search error for '{search_query}': {e}")
                return []

    all_results_lists = await asyncio.gather(*[search_item(item) for item in itinerary])
    return [res for sublist in all_results_lists for res in sublist]


async def _search_for_general(
    state: TravelState,
    emotional_text: str | None = None,
    candidate_k: int = 20,
    rerank_max_k: int = 8,
    search_scope: str = "place_only",
) -> List[Dict[str, Any]]:
    """일반 검색: 텍스트/이미지/위치 기반 하이브리드 후보 풀 검색."""
    retriever = PlaceRetriever.get_instance()

    user_input = get_effective_user_input(state)
    image_path = state.get("image_path")
    latitude = state.get("latitude")
    longitude = state.get("longitude")
    slots = state.get("slots")

    print(f"[Retriever:general] user_input={repr(user_input)} slots={repr(slots)}")
    query = user_input
    if latitude and longitude:
        try:
            geocoder = GeoCoder()
            geocode_data = geocoder.reverse_geocoder(latitude, longitude)
            if geocode_data:
                road = (geocode_data.get("road_address") or "").strip()
                if road:
                    query += f"\n현재 내 위치 주소: {road}"
        except Exception as e:
            print(f"[Retriever] Geocoding error: {e}")

    category = None
    if slots:
        # 다중 카테고리(리스트) 우선, 없을 경우 단일 카테고리 사용
        category = getattr_safe(slots, "categories") or getattr_safe(slots, "category")

    try:
        return await retriever.search_hybrid(
            query=query,
            image_url=image_path,
            limit=candidate_k,
            candidate_k=candidate_k,
            category=category,
            emotional_text=emotional_text,
            user_latitude=latitude,
            user_longitude=longitude,
            preferred_location=getattr_safe(slots, "location"),
            enable_bm25=True,
            enable_rerank=True,
            rerank_top_k=min(rerank_max_k, candidate_k),
            search_scope=search_scope,
        )
    except Exception as e:
        print(f"[Retriever] Hybrid search error: {e}")
        return []


def _build_retrieval_diagnostics(candidate_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
    """채널 기여도와 순위 정보를 진단용으로 집계한다."""
    channel_hits: Dict[str, int] = {}
    top_preview = []
    for c in candidate_pool[:10]:
        for channel in c.get("match_types", []):
            channel_hits[channel] = channel_hits.get(channel, 0) + 1
        top_preview.append(
            {
                "id": get_place_id(c),
                "score": float(c.get("score", 0.0)),
                "first_stage_rank": c.get("first_stage_rank"),
                "final_rank": c.get("final_rank"),
                "match_types": c.get("match_types", []),
            }
        )

    return {
        "candidate_pool_size": len(candidate_pool),
        "channel_hits_top10": channel_hits,
        "top10": top_preview,
    }


async def retriever_node(state: TravelState):
    """장소 검색 Agent: 후보 풀 생성 + 최종 노출 후보 선택."""
    print("--- Retriever Agent ---")

    serving_params = get_retrieval_params("serving")
    user_input = get_effective_user_input(state)
    candidate_k = int(state.get("candidate_k") or serving_params["candidate_k"])
    final_k = int(state.get("final_k") or serving_params["top_k"])
    rerank_max_k = int(state.get("rerank_max_k") or serving_params["rerank_max_k"])
    candidate_k = max(candidate_k, 1)
    final_k = max(final_k, 1)
    rerank_max_k = max(rerank_max_k, 1)
    selection_mode = "deterministic"
    selection_seed = 42

    primary_intent = state.get("primary_intent")
    print(f"[Retriever] primary_intent={primary_intent} itinerary_len={len(state.get('itinerary', []))} user_input={repr(user_input)}")

    image_path = state.get("image_path")
    emotional_text = None
    if image_path:
        print("[Retriever] Image detected. Fetching description once...")
        emotional_text = await describe_image(image_path)

    search_scope = _resolve_search_scope(
        primary_intent=primary_intent,
        slots=state.get("slots"),
        image_path=image_path,
    )
    print(f"[Retriever] search_scope={search_scope}")
    candidate_pool = await _search_for_general(
        state,
        emotional_text=emotional_text,
        candidate_k=candidate_k,
        rerank_max_k=rerank_max_k,
        search_scope=search_scope,
    )
    print(f"[Retriever] general_pool={len(candidate_pool)}")

    if primary_intent == IntentType.TRIP_PLANNING:
        trip_candidates = await _search_for_trip_planning(
            state,
            emotional_text=emotional_text,
            candidate_k=candidate_k,
            rerank_max_k=rerank_max_k,
        )
        print(f"[Retriever] trip_candidates={len(trip_candidates)}")
        candidate_pool.extend(trip_candidates)

    print(f"[Retriever] candidate_pool total={len(candidate_pool)}")

    # pool 기준 dedup + 점수 정렬
    candidate_dict: Dict[str, Dict[str, Any]] = {}
    skipped = 0
    for c in candidate_pool:
        cid = get_place_id(c)
        if not cid:
            skipped += 1
            payload = c.get("payload", {}) if isinstance(c, dict) else {}
            print(
                f"[Retriever] SKIP candidate with empty place_id: "
                f"point_id={get_candidate_point_id(c)!r} payload.contentid={(payload.get('contentid') if isinstance(payload, dict) else None)!r}"
            )
            continue
        if cid not in candidate_dict or _candidate_score(c) > _candidate_score(candidate_dict[cid]):
            candidate_dict[cid] = c

    print(f"[Retriever] dedup: pool={len(candidate_pool)} skipped={skipped} unique={len(candidate_dict)}")
    candidates = sorted(candidate_dict.values(), key=_candidate_score, reverse=True)[:candidate_k]
    print(f"[Retriever] final candidates={len(candidates)}")

    exposed_candidates = _pick_candidates(
        candidates,
        final_k=final_k,
        top_pool=min(candidate_k, 30),
        selection_mode=selection_mode,
        seed=selection_seed,
    )

    diagnostics = _build_retrieval_diagnostics(candidate_pool)

    return {
        "candidate_pool": candidate_pool,
        "candidates": exposed_candidates,
        "retrieval_diagnostics": diagnostics,
        "selection_mode": selection_mode,
    }
