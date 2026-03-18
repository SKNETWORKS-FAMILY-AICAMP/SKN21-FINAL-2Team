import asyncio
import math

from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.state import TravelState
from app.agents.models.place import PlaceInfo
from app.utils.geocoder import GeoCoder
from app.utils.common import getattr_safe, build_naver_map_url

_SEOUL_BBOX = {"lat_min": 37.413, "lat_max": 37.701, "lon_min": 126.734, "lon_max": 127.269}


def _in_seoul_bbox(lat: float, lon: float) -> bool:
    return (
        _SEOUL_BBOX["lat_min"] <= lat <= _SEOUL_BBOX["lat_max"]
        and _SEOUL_BBOX["lon_min"] <= lon <= _SEOUL_BBOX["lon_max"]
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def web_search_node(state: TravelState):
    """웹 검색 fallback Agent (Naver Local Search).

    Qdrant 검색 결과(candidates)가 0개일 때 호출된다.
    Naver Local Search로 장소를 찾아 PlaceInfo 목록과 컨텍스트 텍스트를 state에 저장한다.
    """
    print("--- Web Search Agent ---")
    await adispatch_custom_event("pipeline_step", {"node": "web_search", "status": "start"})

    input_tags = state.get("input_tags") or []
    slots = state.get("slots")
    input_lat = state.get("input_lat")
    input_lon = state.get("input_lon")

    location = getattr_safe(slots, "location") if slots else None
    loc_name = location.name if location else None
    tags = " ".join(input_tags) if input_tags else ""
    categories_list = getattr_safe(slots, "categories") if slots else None
    categories = " ".join(categories_list) if categories_list else ""

    print(f"[WebSearch] loc_name={loc_name!r} tags={tags!r} categories={categories!r}")

    # 검색 키워드 조합
    search_keywords: list[str] = []
    if loc_name and categories:
        category = categories[:1]
        search_keywords.append(f"{loc_name} {category}")
    if tags:
        search_keywords.append(tags)
    if not search_keywords:
        search_keywords.append(f"서울 {loc_name}" if loc_name else "서울 여행 추천")

    print(f"[WebSearch] keywords: {search_keywords}")

    async def _naver_for_keyword(keyword: str) -> list[dict]:
        try:
            return await GeoCoder.get_instance().search_places(keyword, limit=5)
        except Exception as e:
            print(f"[WebSearch] Naver search for '{keyword}' failed: {e}")
            return []

    naver_results_lists = await asyncio.gather(*[_naver_for_keyword(kw) for kw in search_keywords])

    # 중복 제거 + 서울 bbox 필터
    seen_names: set[str] = set()
    if loc_name:
        seen_names.add(loc_name.lower().replace(" ", ""))

    web_context_lines = ["## 웹 검색 결과"]
    naver_places: list[PlaceInfo] = []

    for items in naver_results_lists:
        for item in items:
            name = (item.get("name") or "").strip()
            address = (item.get("road_address") or item.get("jibun_address") or "").strip()
            lat = float(item.get("lat") or 0.0)
            lon = float(item.get("lon") or 0.0)
            if not name or not address or not lat or not lon:
                continue
            if not _in_seoul_bbox(lat, lon):
                continue
            norm = name.lower().replace(" ", "")
            if norm in seen_names:
                continue
            seen_names.add(norm)
            
            map_url = build_naver_map_url(name, lat, lon)
            
            naver_places.append(PlaceInfo(
                contenttypeid="",
                name=name,
                address=address,
                image_path="",
                map_url=map_url,
                longitude=lon,
                latitude=lat,
            ))
            
            # 컨텍스트 텍스트 구성
            category = (item.get("category") or "")
            description = (item.get("description") or "")
            block = [f"### {len(naver_places)}. {name}"]
            if category:
                block.append(f"- 업종: {category}")
            if address:
                block.append(f"- 주소: {address}")
            if description:
                block.append(f"- 설명: {description}")
            if map_url:
                block.append(f"- 지도: {map_url}")
                
            web_context_lines.append("\n".join(block))

    web_context = "\n\n".join(web_context_lines) if naver_places else ""
    print(f"[WebSearch] Done: {len(naver_places)} places found")

    return {
        "web_search_places": naver_places,
        "web_search_context": web_context,
    }
