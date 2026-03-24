from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.state import TravelState
from app.utils.geocoder import GeoCoder, LANDMARK_DICTIONARY, NormalizedLocation
from app.utils.common import getattr_safe, in_seoul_bbox


async def geocoder_node(state: TravelState):
    """위치 anchor 좌표 확인 Agent.

    slots.location → LANDMARK_DICTIONARY → NormalizedLocation → Naver API → slots.location fallback 순으로 anchor 좌표를 해석.
    Seoul bbox 밖이면 'name + 서울' 재검색으로 교정.
    결과는 state의 location_anchor_lat / location_anchor_lon / location_anchor_radius_m 에 저장된다.
    """
    print("--- Geocoder Agent ---")
    await adispatch_custom_event("pipeline_step", {"node": "geocoder", "status": "start"})

    slots = state.get("slots")
    location_obj = getattr_safe(slots, "location") if slots else None
    raw_location = location_obj.name if location_obj else None

    print(f"[Geocoder] raw_location={raw_location!r}")

    anchor_lat = anchor_lon = anchor_radius_m = None

    if raw_location and raw_location in LANDMARK_DICTIONARY:
        entry = LANDMARK_DICTIONARY[raw_location]
        anchor_lat = entry["lat"]
        anchor_lon = entry["lon"]
        anchor_radius_m = entry["radius_m"]
        print(f"[Geocoder] landmark match: {raw_location!r} → lat={anchor_lat} lon={anchor_lon} r={anchor_radius_m}m")

    elif raw_location:
        norm = NormalizedLocation.normalize_location(raw_location)
        if norm.canonical_matched and norm.lat is not None:
            anchor_lat = norm.lat
            anchor_lon = norm.lon
            anchor_radius_m = norm.radius_m
            print(f"[Geocoder] normalized match: {raw_location!r} → {norm.normalized_location!r}")
        else:
            # LANDMARK_DICTIONARY 미매칭 → Naver Search로 서울 내 좌표 직접 검색
            print(f"[Geocoder] '{raw_location}' not in landmark dict — searching Seoul coords via Naver")
            try:
                results = await GeoCoder.get_instance().search_places(f"{raw_location} 서울", 1)
                if results:
                    anchor_lat = results[0].get("lat")
                    anchor_lon = results[0].get("lon")
                    anchor_radius_m = 700
                    print(f"[Geocoder] Naver search anchor: '{raw_location}' → ({anchor_lat}, {anchor_lon}) r=700m")
            except Exception as e:
                print(f"[Geocoder] Naver search anchor failed for '{raw_location}': {e}")

    # slots.location에서 anchor를 못 잡은 경우, input_tags에서 landmark 후보 검색
    # 예: input_tags = ["K-pop", "카페", "홍대"] → "홍대" → LANDMARK_DICTIONARY 매칭
    if not anchor_lat:
        input_tags = state.get("input_tags") or []
        for tag in input_tags:
            if not tag:
                continue
            tag_norm = NormalizedLocation.normalize_location(tag)
            if tag_norm.canonical_matched and tag_norm.lat is not None:
                anchor_lat = tag_norm.lat
                anchor_lon = tag_norm.lon
                anchor_radius_m = tag_norm.radius_m
                print(
                    f"[Geocoder] anchor resolved from input_tags: {tag!r} → "
                    f"lat={anchor_lat} lon={anchor_lon} r={anchor_radius_m}m"
                )
                break

    # Seoul bbox 밖이면 재검색
    if anchor_lat and anchor_lon and not in_seoul_bbox(anchor_lat, anchor_lon):
        print(f"[Geocoder] anchor '{raw_location}' outside Seoul bbox ({anchor_lat}, {anchor_lon}) — retrying")
        try:
            results = await GeoCoder.get_instance().search_places(f"{raw_location} 서울", 1)
            if results:
                new_lat = results[0].get("lat")
                new_lon = results[0].get("lon")
                if new_lat and new_lon and in_seoul_bbox(new_lat, new_lon):
                    print(f"[Geocoder] anchor resolved to Seoul: ({new_lat}, {new_lon})")
                    anchor_lat, anchor_lon = new_lat, new_lon
                    if not anchor_radius_m:
                        anchor_radius_m = 700
                else:
                    print(f"[Geocoder] Seoul re-search still outside bbox — clearing anchor")
                    anchor_lat = anchor_lon = anchor_radius_m = None
        except Exception as e:
            print(f"[Geocoder] Seoul anchor re-search failed for '{raw_location}': {e}")
            anchor_lat = anchor_lon = anchor_radius_m = None

    # 모든 룩업 실패 시 → intent_node에서 정규화된 slots.location 좌표를 fallback으로 사용
    if not anchor_lat and location_obj:
        slots_lat = getattr(location_obj, "lat", None)
        slots_lon = getattr(location_obj, "lon", None)
        if slots_lat and slots_lon and in_seoul_bbox(slots_lat, slots_lon):
            anchor_lat = slots_lat
            anchor_lon = slots_lon
            print(f"[Geocoder] fallback to slots.location coords: lat={anchor_lat} lon={anchor_lon}")

    print(f"[Geocoder] Final anchor: lat={anchor_lat} lon={anchor_lon} r={anchor_radius_m}m")
    await adispatch_custom_event("pipeline_step", {"node": "geocoder", "status": "done"})

    # 사용자 현재 위치 reverse geocoding (한 번만 수행, state에 저장)
    input_address = None
    input_lat = state.get("input_lat")
    input_lon = state.get("input_lon")
    if input_lat and input_lon:
        try:
            geocode_data = await GeoCoder.get_instance().reverse_geocoder(input_lat, input_lon)
            if geocode_data:
                input_address = (geocode_data.get("road_address") or geocode_data.get("jibun_address") or "").strip() or None
                print(f"[Geocoder] reverse geocoded user location: {input_address!r}")
        except Exception as e:
            print(f"[Geocoder] reverse geocoding failed: {e}")

    # pinned_places geo(lat/lon) 추출
    pinned_places = state.get("pinned_places") or []
    updated_pinned_places = []
    for p in pinned_places:
        existing_geo = p.get("geo") or {}
        if existing_geo.get("lat") and existing_geo.get("lon"):
            updated_pinned_places.append(p)
            continue
        name = (p.get("name") or "").strip()
        address = (p.get("address") or "").strip()
        if not name:
            updated_pinned_places.append(p)
            continue
        query = f"{name} {address}".strip() if address else name
        try:
            results = await GeoCoder.get_instance().search_places(query, 1)
            if results and results[0].get("lat") and results[0].get("lon"):
                lat = results[0]["lat"]
                lon = results[0]["lon"]
                p = {**p, "geo": {"lat": lat, "lon": lon}}
                print(f"[Geocoder] pinned_place '{name}' → lat={lat} lon={lon}")
            else:
                print(f"[Geocoder] pinned_place '{name}' geo not found")
        except Exception as e:
            print(f"[Geocoder] pinned_place geocoding failed for '{name}': {e}")
        updated_pinned_places.append(p)

    return {
        "location_anchor_lat": anchor_lat,
        "location_anchor_lon": anchor_lon,
        "location_anchor_radius_m": anchor_radius_m,
        "input_address": input_address,
        "pinned_places": updated_pinned_places,
    }
