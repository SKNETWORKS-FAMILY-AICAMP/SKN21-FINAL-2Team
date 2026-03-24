import asyncio
import random
import re
import time
from typing import Dict, Any, List

from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.state import TravelState, get_effective_user_input
from app.agents.models.output import IntentType, InputType
from app.core.retrieval.place import PlaceRetriever
from app.utils.geocoder import LANDMARK_DICTIONARY
from app.utils.vision import describe_image
from app.utils.common import getattr_safe, in_seoul_bbox, normalize_text, dprint
from app.utils.place_id import get_candidate_point_id, get_contenttypeid

from app.utils.config import get_retrieval_params, CANDIDATE_THRESHOLD


def _candidate_category(candidate: Dict[str, Any]) -> str:
    payload = candidate.get("payload", {})
    # 카테고리 필드는 아래 우선순위로 통일
    return (
        str(payload.get("contenttypeid") or "").strip()
        or str(payload.get("category") or "").strip()
        or "unknown"
    )

def _candidate_score(candidate: Dict[str, Any]) -> float:
    """blended_score → rerank_score → score 순으로 최종 품질 점수를 반환."""
    try:
        for key in ("blended_score", "rerank_score", "score"):
            val = candidate.get(key)
            if val is not None:
                return max(float(val), 1e-6)
        return 1e-6
    except Exception:
        return 1e-6


def _candidate_name_signature(candidate: Dict[str, Any]) -> str:
    """
    같은 장소 여부를 판별하기 위한 이름 시그니처.
    후보의 대표 장소명을 추출한다.
    """
    payload = candidate.get("payload", {}) or {}
    name = str(
        payload.get("place")
        or payload.get("title")
        or payload.get("name")
        or ""
    ).strip()

    return normalize_text(name)


def _resolve_search_scope(
    primary_intent: IntentType | None,
    slots: Any,
    image_path: str | None,
) -> str:
    """검색 범위를 결정한다.

    - "place_only": PLACES_COLLECTION(BGE-M3 text) 전용
    - "photo_only": PHOTOS_COLLECTION(CLIP vision/text) 전용
    - "auto":       양쪽 모두 검색
                    → Channel A(text_semantic) + Channel C(text_to_image) 활성화
                    → image_url=None이면 Channel B/D는 search_hybrid 내에서 자동 스킵
    """
    if primary_intent == IntentType.TRIP_PLANNING:
        return "place_only"

    input_type = None
    if slots:
        input_type = getattr_safe(slots, "input_type")

    if primary_intent == IntentType.IMAGE_SIMILAR:
        return "photo_only"

    if input_type == InputType.IMAGE or str(input_type) == str(InputType.IMAGE.value):
        return "photo_only"

    # 텍스트 전용 or 텍스트+이미지 복합 → "auto"
    # Channel C(CLIP Text→PHOTOS) 활성화: 시각적 묘사 쿼리("바다 보이는 카페" 등) 품질 향상
    # image_url=None 시 Channel B(image_visual)/D(image_emotional)는 내부에서 자동 스킵됨
    return "auto"


def _pick_diverse_candidates_deterministic(candidates: List[Dict[str, Any]], final_k: int, top_pool: int) -> List[Dict[str, Any]]:
    """결정론 모드: 점수 우선 + 카테고리 분산 tie-break."""
    if len(candidates) <= final_k:
        return candidates

    pool = list(candidates[: min(len(candidates), top_pool)])
    selected: List[Dict[str, Any]] = []
    used_categories = set()
    used_name_signatures = set()

    # 1차: 카테고리 중복은 줄이되, 동일 장소명은 반드시 제외
    for c in pool:
        cat = _candidate_category(c)
        name_signature = _candidate_name_signature(c)
        if not name_signature or name_signature in used_name_signatures:
            continue
        if cat not in used_categories:
            selected.append(c)
            used_categories.add(cat)
            used_name_signatures.add(name_signature)
            if len(selected) >= final_k:
                return selected

    # 2차: 같은 카테고리여도 장소명이 다르면 채움
    selected_ids = {get_contenttypeid(c) for c in selected}
    for c in pool:
        cid = get_contenttypeid(c)
        name_signature = _candidate_name_signature(c)
        if not name_signature or name_signature in used_name_signatures:
            continue
        if cid and cid not in selected_ids:
            selected.append(c)
            selected_ids.add(cid)
            used_name_signatures.add(name_signature)
            if len(selected) >= final_k:
                return selected

    # 3차: 남은 슬롯은 점수 순으로 채움
    selected_ids = {get_contenttypeid(c) for c in selected}
    for c in pool:
        cid = get_contenttypeid(c)
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
    used_name_signatures = set()
    rng = random.Random(seed)

    while pool and len(selected) < final_k:
        unseen_pool = [
            c for c in pool
            if _candidate_category(c) not in used_categories
            and _candidate_name_signature(c)
            and _candidate_name_signature(c) not in used_name_signatures
        ]
        unique_name_pool = [
            c for c in pool
            if _candidate_name_signature(c)
            and _candidate_name_signature(c) not in used_name_signatures
        ]
        source = unseen_pool if unseen_pool else unique_name_pool if unique_name_pool else pool
        weights = [_candidate_score(c) for c in source]
        picked = rng.choices(source, weights=weights, k=1)[0]

        selected.append(picked)
        used_categories.add(_candidate_category(picked))
        name_signature = _candidate_name_signature(picked)
        if name_signature:
            used_name_signatures.add(name_signature)
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


def _pick_candidates_for_trip_planning(
    candidate_pool: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """TRIP_PLANNING 전용: itinerary 항목(item_idx)별로 최고 점수 후보 1개씩 선택.

    - item_idx 별로 점수 순 정렬 후 아직 선택되지 않은 장소명 중 최고점 1개 선택
    - 다른 항목에서 이미 선택된 장소는 중복 배치하지 않음
    - item_idx가 없는 후보(fallback general 검색 결과 등)는 처리하지 않음
    """
    item_groups: dict[tuple, List[Dict[str, Any]]] = {}
    for c in candidate_pool:
        day = c.get("itinerary_day") or 0
        item_idx = c.get("itinerary_item_idx")
        if not day or item_idx is None:
            continue
        item_groups.setdefault((day, item_idx), []).append(c)

    selected: List[Dict[str, Any]] = []
    used_name_signatures: set[str] = set()

    for key in sorted(item_groups.keys()):
        item_candidates = sorted(item_groups[key], key=_candidate_score, reverse=True)
        for c in item_candidates:
            name_sig = _candidate_name_signature(c)
            if name_sig and name_sig not in used_name_signatures:
                selected.append(c)
                used_name_signatures.add(name_sig)
                break

    return selected


async def _search_for_trip_planning(
    state: TravelState,
    emotional_text: str | None = None,
    candidate_k: int = 20,
    rerank_max_k: int = 8,
) -> List[Dict[str, Any]]:
    """TRIP_PLANNING: planner itinerary 기반 후보 검색."""
    retriever = PlaceRetriever.get_instance()

    itinerary = state.get("itinerary", [])
    image_path = state.get("input_image")

    if not itinerary:
        return []

    # Semaphore(3) : 병렬로 최대한 몇개 장소 검색할것인지? 10개라고 하면 최대 3개씩 병렬 검색
    semaphore = asyncio.Semaphore(3)

    async def search_item(item_with_idx):
        item, item_idx = item_with_idx
        async with semaphore:
            search_query = item.get("search_query", "") or item.get("activity", "")
            dprint("[Retriever - search planning] query: ", search_query)
            if not search_query:
                return []

            try:
                item_category = item.get("category")
                # itinerary 항목별 검색은 전체 K를 쓰지 않고 상위 일부만 취합
                results = await retriever.search_hybrid(
                    query=search_query,
                    image_url=image_path,
                    limit=max(10, candidate_k // 3),
                    candidate_k=max(10, candidate_k // 3),
                    categories=[item_category] if item_category else None,
                    emotional_text=emotional_text,
                    user_latitude=state.get("input_lat"),
                    user_lon=state.get("input_lon"),
                    preferred_location=getattr_safe(state.get("slots"), "location").name if getattr_safe(state.get("slots"), "location") else None,
                    enable_rerank=True,
                    rerank_top_k=min(rerank_max_k, max(10, candidate_k // 3)),
                    search_scope="place_only",
                )

                # 일정 정보 및 item_idx를 각 장소 결과 객체에 추가
                for res in results:
                    res["itinerary_day"] = item.get("day", 1)
                    res["itinerary_time_slot"] = item.get("time_slot", "")
                    res["itinerary_item_idx"] = item_idx
                    res["itinerary_activity"] = item.get("activity", "")

                return results

            except Exception as e:
                dprint(f"[Retriever] Search error for '{search_query}': {e}")
                return []

    all_results_lists = await asyncio.gather(*[search_item((item, idx)) for idx, item in enumerate(itinerary)])
    return [res for sublist in all_results_lists for res in sublist]


async def _search_for_general(
    state: TravelState,
    emotional_text: str | None = None,
    candidate_k: int = 20,
    rerank_max_k: int = 8,
    search_scope: str = "place_only",
    geo_retry_count: int = 0,
) -> List[Dict[str, Any]]:
    """일반 검색: 텍스트/이미지/위치 기반 하이브리드 후보 풀 검색."""
    retriever = PlaceRetriever.get_instance()

    user_input = get_effective_user_input(state)
    input_tags = state.get("input_tags")
    image_path = state.get("input_image")
    latitude = state.get("input_lat")
    longitude = state.get("input_lon")
    slots = state.get("slots")

    dprint(f"[Retriever:general] user_input={repr(user_input)} slots={repr(slots)}")
    query = user_input

    if state.get("semantic_input_image"):
        query += f"\n입력 이미지에 대한 설명: {state.get('semantic_input_image')}"

    input_address = state.get("input_address")
    if input_address:
        query += f"\n현재 내 위치 주소: {input_address}"

    if input_tags:
        query += f"\n입력 키워드: {', '.join(input_tags)}"

    if state.get("prefs_info"):
        query += f"\n사용자의 선호도(참고용): {state.get('prefs_info')}"

    categories = None
    raw_location = None
    if slots:
        categories = getattr_safe(slots, "categories")
        location_obj = getattr_safe(slots, "location")
        raw_location = location_obj.name if location_obj else None

    # geocoder_node에서 미리 확인된 anchor 좌표를 state에서 읽는다.
    anchor_lat = state.get("location_anchor_lat")
    anchor_lon = state.get("location_anchor_lon")
    anchor_radius_m = state.get("location_anchor_radius_m")
    dprint(f"[Retriever] anchor from state: lat={anchor_lat} lon={anchor_lon} r={anchor_radius_m}m")

    try:
        return await retriever.search_hybrid(
            query=query,
            image_url=image_path,
            limit=candidate_k,
            candidate_k=candidate_k,
            categories=categories,
            emotional_text=emotional_text,
            user_latitude=latitude,
            user_lon=longitude,
            preferred_location=raw_location,
            enable_rerank=True,
            rerank_top_k=min(rerank_max_k, candidate_k),
            search_scope=search_scope,
            location_anchor_lat=anchor_lat,
            location_anchor_lon=anchor_lon,
            location_radius_m=anchor_radius_m,
            geo_retry_count=geo_retry_count,
            input_tags=list(input_tags) if input_tags else None,
        )
    except Exception as e:
        dprint(f"[Retriever] Hybrid search error: {e}")
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
                "id": get_contenttypeid(c),
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
    """장소 검색 Agent: 후보 풀 생성 + 최종 노출 후보 선택.

    그래프 레벨 재시도 흐름
    ─────────────────────
    retriever_retry_count == 0 : 초회 — 정상 반경(geo_retry_count=0)으로 검색
    retriever_retry_count == 1 : 재시도 — GEO_RETRY_MULTIPLIER 배 확장 반경(geo_retry_count=1)
    결과가 없고 카운트가 0이면 route_after_retriever 가 다시 retriever 로 라우팅한다.
    """
    retry_count = int(state.get("retriever_retry_count") or 0)
    _node_start = time.perf_counter()
    dprint(f"--- Retriever Agent (retry_count={retry_count}) ---")
    # 재시도 여부를 직접 알고 있으므로 step 이름을 명확하게 전달
    _step_key = "retriever_retry" if retry_count > 0 else "retriever"
    await adispatch_custom_event("pipeline_step", {"node": _step_key, "status": "start"})

    serving_params = get_retrieval_params("serving")
    user_input = get_effective_user_input(state)
    candidate_k = int(state.get("candidate_k") or serving_params["candidate_k"])
    final_k = int(state.get("final_k") or serving_params["top_k"])
    rerank_max_k = int(state.get("rerank_max_k") or serving_params["rerank_max_k"])
    candidate_k = max(candidate_k, 1)
    final_k = max(final_k, 1)
    rerank_max_k = max(rerank_max_k, 1)
    # 매 턴마다 다른 결과를 내기 위해 room_id + 대화 턴 수 기반 seed 사용.
    # state에서 외부 오버라이드(selection_mode)가 있으면 그것을 존중한다.
    selection_mode = state.get("selection_mode") or "explore"
    room_id = state.get("room_id") or 0
    turn_count = len(state.get("messages") or [])
    selection_seed = (hash(str(room_id)) + turn_count) % (2 ** 31)

    primary_intent = state.get("primary_intent")
    dprint(f"[Retriever] primary_intent={primary_intent} itinerary_len={len(state.get('itinerary', []))} user_input={repr(user_input)}")

    image_path = state.get("input_image")
    emotional_text = state.get("semantic_input_image") or None
    if image_path and not emotional_text:
        dprint("[Retriever] semantic_input_image missing, calling describe_image as fallback...")
        emotional_text = await describe_image(image_path)

    search_scope = _resolve_search_scope(
        primary_intent=primary_intent,
        slots=state.get("slots"),
        image_path=image_path,
    )
    dprint(f"[Retriever] search_scope={search_scope} geo_retry_count={retry_count}")

    # TRIP_PLANNING: itinerary 기반 검색만 실행 (일반 검색 노이즈 제외).
    # 결과가 0이면(itinerary 없거나 검색 실패) 일반 검색으로 fallback.
    _trip_planning_fallback = False
    if primary_intent == IntentType.TRIP_PLANNING:
        candidate_pool = await _search_for_trip_planning(
            state,
            emotional_text=emotional_text,
            candidate_k=candidate_k,
            rerank_max_k=rerank_max_k,
        )
        dprint(f"[Retriever] trip_candidates={len(candidate_pool)}")
        if not candidate_pool:
            dprint("[Retriever] trip search returned 0, fallback to general search")
            _trip_planning_fallback = True
            candidate_pool = await _search_for_general(
                state,
                emotional_text=emotional_text,
                candidate_k=candidate_k,
                rerank_max_k=rerank_max_k,
                search_scope=search_scope,
                geo_retry_count=retry_count,
            )
            dprint(f"[Retriever] fallback general_pool={len(candidate_pool)}")
    else:
        candidate_pool = await _search_for_general(
            state,
            emotional_text=emotional_text,
            candidate_k=candidate_k,
            rerank_max_k=rerank_max_k,
            search_scope=search_scope,
            geo_retry_count=retry_count,
        )
        dprint(f"[Retriever] general_pool={len(candidate_pool)}")

    # pinned_places(auto_start 선택 장소) 강제 inject
    # 각 pinned place를 이름으로 직접 검색해서 candidate_pool에 추가
    pinned_places = state.get("pinned_places") or []
    if pinned_places and primary_intent == IntentType.TRIP_PLANNING:
        retriever_instance = PlaceRetriever.get_instance()
        itinerary = state.get("itinerary") or []
        existing_ids = {get_place_id(c) for c in candidate_pool}

        for pp in pinned_places:
            pp_name = (pp.get("name") or "").strip()
            if not pp_name:
                continue
            try:
                pinned_results = await retriever_instance.search_hybrid(
                    query=pp_name,
                    limit=3,
                    candidate_k=3,
                    search_scope="place_only",
                    enable_rerank=False,
                )
                if not pinned_results:
                    dprint(f"[Retriever] pinned place not found: {pp_name!r}")
                    continue

                best = pinned_results[0]
                best_id = get_place_id(best)

                # 이미 pool에 있으면 스킵
                if best_id and best_id in existing_ids:
                    dprint(f"[Retriever] pinned place already in pool: {pp_name!r}")
                    continue

                # itinerary에서 해당 장소와 매칭되는 항목 찾기 (search_query에 장소명 포함)
                matched_item = next(
                    (item for item in itinerary if pp_name in item.get("search_query", "")),
                    None,
                )
                # 매칭된 itinerary 항목이 없으면 첫 번째 항목에 배치
                if not matched_item and itinerary:
                    matched_item = itinerary[0]

                if matched_item:
                    item_idx = itinerary.index(matched_item) if matched_item in itinerary else 0
                    best["itinerary_day"] = matched_item.get("day", 1)
                    best["itinerary_time_slot"] = matched_item.get("time_slot", "")
                    best["itinerary_item_idx"] = item_idx
                    best["itinerary_activity"] = matched_item.get("activity", pp_name)
                    best["pinned"] = True

                candidate_pool.append(best)
                if best_id:
                    existing_ids.add(best_id)
                dprint(f"[Retriever] pinned place injected: {pp_name!r} (id={best_id})")

            except Exception as e:
                dprint(f"[Retriever] pinned place inject error for {pp_name!r}: {e}")

    dprint(f"[Retriever] candidate_pool total={len(candidate_pool)}")

    # pool 기준 dedup + 점수 정렬
    candidate_dict: Dict[str, Dict[str, Any]] = {}
    name_dedup_dict: Dict[str, Dict[str, Any]] = {}
    skipped = 0
    for c in candidate_pool:
        cid = get_contenttypeid(c)
        if not cid:
            skipped += 1
            payload = c.get("payload", {}) if isinstance(c, dict) else {}
            dprint(
                f"[Retriever] SKIP candidate with empty place_id: "
                f"point_id={get_candidate_point_id(c)!r} payload.contentid={(payload.get('contentid') if isinstance(payload, dict) else None)!r}"
            )
            continue
        if cid not in candidate_dict or _candidate_score(c) > _candidate_score(candidate_dict[cid]):
            candidate_dict[cid] = c
        name_signature = _candidate_name_signature(c)
        if name_signature and (
            name_signature not in name_dedup_dict
            or _candidate_score(c) > _candidate_score(name_dedup_dict[name_signature])
        ):
            name_dedup_dict[name_signature] = c

    deduped_candidates = list(name_dedup_dict.values()) if name_dedup_dict else list(candidate_dict.values())
    dprint(
        f"[Retriever] dedup: pool={len(candidate_pool)} skipped={skipped} "
        f"unique_id={len(candidate_dict)} unique_name={len(name_dedup_dict)}"
    )
    candidates = sorted(deduped_candidates, key=_candidate_score, reverse=True)[:candidate_k]

    # CANDIDATE_THRESHOLD 미만 후보 제거
    # 단, 모두 탈락해도 최소 final_k개는 점수순으로 유지 (web_search fallback 방지)
    above = [c for c in candidates if _candidate_score(c) >= CANDIDATE_THRESHOLD]
    dprint(
        f"[Retriever] threshold={CANDIDATE_THRESHOLD} "
        f"before={len(candidates)} after={len(above)} "
        f"(dropped={len(candidates) - len(above)})"
    )
    if len(above) < final_k and candidates:
        # reranker가 쿼리와 후보 간 관련성을 낮게 평가해 전원 탈락했더라도
        # 점수순 상위 final_k개는 무조건 유지 → 빈 결과로 web_search로 빠지는 현상 방지
        above = candidates[:max(final_k, len(above))]
        dprint(
            f"[Retriever] threshold dropped all → keeping top {len(above)} by score (min_k={final_k})"
        )
    candidates = above

    # 이미 노출된 장소 제거 (fallback 없음 — final_k 미달이어도 허용)
    shown_place_ids: list[str] = list(state.get("shown_place_ids") or [])
    if shown_place_ids:
        shown_set = set(shown_place_ids)
        before_exc = len(candidates)
        candidates = [c for c in candidates if get_contenttypeid(c) not in shown_set]
        dprint(
            f"[Retriever] shown_place exclusion: before={before_exc} after={len(candidates)} "
            f"excluded={before_exc - len(candidates)}"
        )

    # exclude_tags / exclude_location 후처리 패널티
    slots = state.get("slots")
    exclude_tags = list(getattr_safe(slots, "exclude_tags") or [])
    exclude_location = str(getattr_safe(slots, "exclude_location") or "").strip()
    if exclude_tags or exclude_location:
        for c in candidates:
            payload = c.get("payload", {}) if isinstance(c, dict) else {}
            desc = (str(payload.get("overview", "")) + str(payload.get("title", ""))).lower()
            addr = str(payload.get("addr", "") or payload.get("road_address", "")).lower()
            for tag in exclude_tags:
                if tag.lower() in desc:
                    c["blended_score"] = c.get("blended_score", 0) * 0.1
                    dprint(f"[Retriever] exclude_tag={tag!r} penalty applied: {payload.get('title', '')!r}")
                    break
            if exclude_location and exclude_location in addr:
                c["blended_score"] = 0.0
                dprint(f"[Retriever] exclude_location={exclude_location!r} zeroed: {payload.get('title', '')!r}")
        # 패널티 후 재정렬 (score=0 항목은 사실상 제외)
        candidates = [c for c in sorted(candidates, key=_candidate_score, reverse=True) if _candidate_score(c) > 0.0]

    if primary_intent == IntentType.TRIP_PLANNING and not _trip_planning_fallback:
        # 항목(item_idx)별 top-1 선택: global final_k 제한 없이 itinerary 항목당 1개
        exposed_candidates = _pick_candidates_for_trip_planning(candidate_pool)
        dprint(f"[Retriever] trip_planning item-based selection: {len(exposed_candidates)} candidates")
    else:
        exposed_candidates = _pick_candidates(
            candidates,
            final_k=final_k,
            top_pool=min(candidate_k, 30),
            selection_mode=selection_mode,
            seed=selection_seed,
        )

    diagnostics = _build_retrieval_diagnostics(candidate_pool)

    # location diagnostics 보강
    slots = state.get("slots")
    location_obj = getattr_safe(slots, "location") if slots else None
    norm_location = location_obj.name if location_obj else None
    canonical_matched = norm_location in LANDMARK_DICTIONARY if norm_location else False
    diagnostics["normalized_location"] = norm_location
    diagnostics["location_canonical_matched"] = canonical_matched
    diagnostics["location_geo_filter_applied"] = canonical_matched  # anchor 전달 여부와 동치

    dprint(f"[TIMING] retriever_node DONE  total={time.perf_counter()-_node_start:.3f}s  exposed={len(exposed_candidates)}")
    return {
        "candidate_pool": candidate_pool,
        "candidates": exposed_candidates,
        "retrieval_diagnostics": diagnostics,
        "selection_mode": selection_mode,
        # route_after_retriever 가 이 값을 보고 재시도 여부를 결정한다.
        # 매 실행마다 1씩 증가: 0→1(초회 완료), 1→2(재시도 완료)
        "retriever_retry_count": retry_count + 1,
    }
