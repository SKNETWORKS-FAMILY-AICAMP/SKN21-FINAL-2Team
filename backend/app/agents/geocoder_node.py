from app.agents.models.state import TravelState
from app.utils.geocoder import GeoCoder, LANDMARK_DICTIONARY, NormalizedLocation
from app.utils.common import getattr_safe, in_seoul_bbox


async def geocoder_node(state: TravelState):
    """위치 anchor 좌표 확인 Agent.

    slots.location → LANDMARK_DICTIONARY → NormalizedLocation → Naver API 순으로 anchor 좌표를 해석.
    Seoul bbox 밖이면 'name + 서울' 재검색으로 교정.
    결과는 state의 location_anchor_lat / location_anchor_lon / location_anchor_radius_m 에 저장된다.
    """
    print("--- Geocoder Agent ---")

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
                    print(f"[Geocoder] Naver search anchor: '{raw_location}' → ({anchor_lat}, {anchor_lon})")
            except Exception as e:
                print(f"[Geocoder] Naver search anchor failed for '{raw_location}': {e}")

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
                else:
                    print(f"[Geocoder] Seoul re-search still outside bbox — clearing anchor")
                    anchor_lat = anchor_lon = anchor_radius_m = None
        except Exception as e:
            print(f"[Geocoder] Seoul anchor re-search failed for '{raw_location}': {e}")
            anchor_lat = anchor_lon = anchor_radius_m = None

    print(f"[Geocoder] Final anchor: lat={anchor_lat} lon={anchor_lon} r={anchor_radius_m}m")

    return {
        "location_anchor_lat": anchor_lat,
        "location_anchor_lon": anchor_lon,
        "location_anchor_radius_m": anchor_radius_m,
    }
