import asyncio

from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.state import TravelState
from app.agents.models.output import IntentLocation
from app.utils.geocoder import GeoCoder, LANDMARK_DICTIONARY, NormalizedLocation
from app.utils.common import getattr_safe, in_seoul_bbox

_GPS_ANCHOR_RADIUS_M = 1000.0  # GPS 기준 검색 반경(m)


def _extract_area_name_from_address(address: str | None) -> str | None:
    """전체 주소 문자열에서 구+동 수준의 지역명을 추출한다.

    예) '서울특별시 마포구 서교동 360-1' → '마포구 서교동'
        '서울특별시 강남구 테헤란로 123'  → '강남구'
    """
    if not address:
        return None
    parts = address.split()
    gu_part = dong_part = None
    for i, token in enumerate(parts):
        if token.endswith(("구", "군")) and gu_part is None:
            gu_part = token
            if i + 1 < len(parts) and parts[i + 1].endswith(("동", "읍", "면", "가")):
                dong_part = parts[i + 1]
            break
    if gu_part and dong_part:
        return f"{gu_part} {dong_part}"
    if gu_part:
        return gu_part
    # 파싱 실패 시 마지막에서 두 번째 토큰 (번지 제외)
    return parts[-2] if len(parts) >= 2 else address


async def geocoder_node(state: TravelState):
    """위치 anchor 좌표 확인 Agent.

    [우선순위]
    1. 사용자 GPS(input_lat/lon)가 서울 내 좌표 → GPS를 anchor로 사용하고 slots.location도 GPS 파생 위치로 교체.
    2. slots.location → LANDMARK_DICTIONARY → NormalizedLocation → Naver API → slots.location fallback 순.

    Seoul bbox 밖이면 'name + 서울' 재검색으로 교정.
    결과는 state의 location_anchor_lat / location_anchor_lon / location_anchor_radius_m 에 저장된다.
    """
    print("--- Geocoder Agent ---")
    await adispatch_custom_event("pipeline_step", {"node": "geocoder", "status": "start"})

    slots = state.get("slots")
    location_obj = getattr_safe(slots, "location") if slots else None
    raw_location = location_obj.name if location_obj else None

    input_lat = state.get("input_lat")
    input_lon = state.get("input_lon")
    gps_in_seoul = bool(input_lat and input_lon and in_seoul_bbox(input_lat, input_lon))

    anchor_lat = anchor_lon = anchor_radius_m = None
    gps_location_override = False

    # intent_node에서 이미 reverse geocoding 완료 → state 값 재사용 (중복 API 호출 없음)
    input_address: str | None = state.get("input_address")
    gps_outside_seoul: bool = state.get("gps_outside_seoul", False)

    print(f"[Geocoder] raw_location={raw_location!r}  gps_in_seoul={gps_in_seoul}  input_address={input_address!r}")

    # ── 1. GPS 서울 내 → GPS 우선 ──────────────────────────────────────────
    if gps_in_seoul:
        # input_address는 intent_node에서 reverse geocoding된 전체 주소
        # area_name은 구+동 수준 축약명 (slots.location.name 용도)
        area_name = _extract_area_name_from_address(input_address) if input_address else None

        anchor_lat = input_lat
        anchor_lon = input_lon
        anchor_radius_m = _GPS_ANCHOR_RADIUS_M
        gps_location_override = True

        # slots.location을 GPS 파생 위치로 교체
        if slots is not None:
            gps_loc_name = area_name or input_address or f"{input_lat:.4f},{input_lon:.4f}"
            slots.location = IntentLocation(name=gps_loc_name, lat=input_lat, lon=input_lon)
            print(f"[Geocoder] slots.location overridden by GPS: {slots.location.name!r} ({input_lat}, {input_lon})")

    # ── 2. GPS 없거나 서울 밖 → 기존 slots.location 기반 anchor 해석 ────────
    else:
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

    print(f"[Geocoder] Final anchor: lat={anchor_lat} lon={anchor_lon} r={anchor_radius_m}m  gps_override={gps_location_override}")
    await adispatch_custom_event("pipeline_step", {"node": "geocoder", "status": "done"})

    # pinned_places geo(lat/lon) 추출 — 모든 장소를 병렬로 geocoding
    async def _resolve_pinned_geo(p: dict) -> dict:
        existing_geo = p.get("geo") or {}
        if existing_geo.get("lat") and existing_geo.get("lon"):
            return p
        name = (p.get("name") or "").strip()
        address = (p.get("address") or "").strip()
        if not name:
            return p
        query = f"{name} {address}".strip() if address else name
        try:
            results = await GeoCoder.get_instance().search_places(query, 1)
            if results and results[0].get("lat") and results[0].get("lon"):
                lat, lon = results[0]["lat"], results[0]["lon"]
                print(f"[Geocoder] pinned_place '{name}' → lat={lat} lon={lon}")
                return {**p, "geo": {"lat": lat, "lon": lon}}
            else:
                print(f"[Geocoder] pinned_place '{name}' geo not found")
        except Exception as e:
            print(f"[Geocoder] pinned_place geocoding failed for '{name}': {e}")
        return p

    pinned_places = state.get("pinned_places") or []
    if pinned_places:
        updated_pinned_places = list(
            await asyncio.gather(*[_resolve_pinned_geo(p) for p in pinned_places])
        )
        print(f"[Geocoder] pinned_places geo resolved: {len(updated_pinned_places)} items (parallel)")
    else:
        updated_pinned_places = []

    result: dict = {
        "location_anchor_lat": anchor_lat,
        "location_anchor_lon": anchor_lon,
        "location_anchor_radius_m": anchor_radius_m,
        "pinned_places": updated_pinned_places,
        "gps_location_override": gps_location_override,
        # input_address / gps_outside_seoul 은 intent_node에서 이미 state에 기록됨 → 재설정 불필요
    }
    # GPS 우선 모드일 때 변경된 slots도 state에 반영
    if gps_location_override and slots is not None:
        result["slots"] = slots
    return result
