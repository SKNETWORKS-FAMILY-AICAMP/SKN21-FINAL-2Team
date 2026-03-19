import os
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

# canonical key = 표준 장소명. aliases = 사용자 입력 변형 목록.
LANDMARK_DICTIONARY: Dict[str, Dict[str, Any]] = {
    "고대": {
        "canonical_name": "고대",
        "aliases": ["고려대", "고려대학교", "고대입구", "고대앞"],
        "lat": 37.5895, "lon": 127.0325, "radius_m": 1500,
        "description": "고려대학교 중심 안암동 일대",
    },
    "홍대": {
        "canonical_name": "홍대",
        "aliases": ["홍대입구", "홍대거리", "홍익대", "홍익대학교", "홍대앞"],
        "lat": 37.5575, "lon": 126.9245, "radius_m": 1500,
        "description": "홍대입구역 중심 서교동/연남동 일대",
    },
    "건대": {
        "canonical_name": "건대",
        "aliases": ["건국대", "건국대학교", "건대입구", "화양동"],
        "lat": 37.5404, "lon": 127.0692, "radius_m": 1000,
        "description": "건대입구역 중심 화양동 일대",
    },
    "가로수길": {
        "canonical_name": "가로수길",
        "aliases": ["신사동가로수길", "신사동 가로수길", "신사가로수길"],
        "lat": 37.5203, "lon": 127.0231, "radius_m": 800,
        "description": "신사동 가로수길 메인 로드 주변",
    },
    "샤로수길": {
        "canonical_name": "샤로수길",
        "aliases": ["서울대입구", "서울대입구역", "관악로", "샤로수길카페거리", "서울대 샤로수길", "관악 카페거리"],
        "lat": 37.4791, "lon": 126.9535, "radius_m": 600,
        "description": "서울대입구역 인근 관악로 일대",
    },
    "송리단길": {
        "canonical_name": "송리단길",
        "aliases": ["석촌호수 맛집", "송파동 카페거리", "방이동 먹자골목"],
        "lat": 37.5098, "lon": 127.1068, "radius_m": 800,
        "description": "석촌호수 동호 남측, 송파동 일대의 카페 및 맛집 밀집 지역"
    },
    "서촌": {
        "canonical_name": "서촌",
        "aliases": ["세종마을", "통의동", "옥인동", "체부동", "경복궁 서측"],
        "lat": 37.5800, "lon": 126.9690, "radius_m": 900,
        "description": "경복궁 서쪽 효자동, 통의동 일대 한옥과 갤러리가 많은 동네"
    },
    "북촌": {
        "canonical_name": "북촌",
        "aliases": ["북촌한옥마을", "가회동", "삼청동", "계동"],
        "lat": 37.5828, "lon": 126.9835, "radius_m": 1000,
        "description": "경복궁과 창덕궁 사이 한옥 보존 지구 및 관광 명소"
    },
    "성수동 카페거리": {
        "canonical_name": "성수동",
        "aliases": ["성수동", "성수", "연무장길", "성수핫플", "서울숲 카페거리", "성수역", "뚝섬"],
        "lat": 37.5445, "lon": 127.0560, "radius_m": 1500,
        "description": "폐공장을 개조한 카페와 브랜드 팝업스토어가 밀집한 성수역~서울숲 일대"
    },
    "망리단길": {
        "canonical_name": "망리단길",
        "aliases": ["망원시장", "망원동 카페거리", "희우정로"],
        "lat": 37.5560, "lon": 126.9015, "radius_m": 800,
        "description": "망원시장 인근 포은로를 중심으로 형성된 개성 있는 상권"
    },
    "힙지로": {
        "canonical_name": "을지로",
        "aliases": ["을지로", "을지로 노가리골목", "을지로3가", "을지로4가", "을지로입구", "힙지로카페"],
        "lat": 37.5661, "lon": 126.9916, "radius_m": 1000,
        "description": "오래된 인쇄소와 철공소 사이 감각적인 바와 카페가 들어선 을지로 일대"
    },
    "경리단길": {
        "canonical_name": "경리단길",
        "aliases": ["이태원 경리단", "회나무로"],
        "lat": 37.5385, "lon": 126.9870, "radius_m": 700,
        "description": "이태원동 국군재정관리단부터 남산 하얏트 호텔까지의 언덕 상권"
    },
    "해방촌": {
        "canonical_name": "해방촌",
        "aliases": ["HBC", "용산동2가", "신흥시장"],
        "lat": 37.5420, "lon": 126.9840, "radius_m": 700,
        "description": "남산 아래 첫 동네로 이국적인 루프탑과 카페가 많은 용산동 일대"
    },
}


# ---------------------------------------------------------------------------
# 정규화 결과 타입
# ---------------------------------------------------------------------------

@dataclass
class NormalizedLocationResult:
    raw: Optional[str]
    normalized_location: Optional[str]  # 표준명 or 원문 or None
    canonical_matched: bool             # LANDMARK_DICTIONARY 매칭 여부
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_m: Optional[float] = None


class NormalizedLocation:
    def __init__(self, name: str, lat: float, lon: float, radius_m: float):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.radius_m = radius_m

    # ---------------------------------------------------------------------------
    # 내부 헬퍼
    # ---------------------------------------------------------------------------

    def _strip_suffix(text: str) -> str:
        """괄호 제거 + 기본 접미어(입구역, 역, 거리) 제거."""
        text = re.sub(r"\(.*?\)", "", text).strip()
        for suffix in ("입구역", "역", "거리"):
            if text.endswith(suffix) and len(text) > len(suffix):
                return text[: -len(suffix)].strip()
        return text


    def _collapse_spaces(text: str) -> str:
        """모든 공백 제거 — step 5 공백 정규화 후 exact match 용."""
        return re.sub(r"\s+", "", text).strip()


    def _lookup_landmark(text: str) -> Optional[NormalizedLocationResult]:
        """canonical key / alias 순서로 LANDMARK_DICTIONARY 검색."""
        # Step 3: canonical exact match
        if text in LANDMARK_DICTIONARY:
            entry = LANDMARK_DICTIONARY[text]
            return NormalizedLocationResult(
                raw=None,  # 호출자가 채움
                normalized_location=text,
                canonical_matched=True,
                lat=entry["lat"],
                lon=entry["lon"],
                radius_m=entry["radius_m"],
            )
        # Step 4: alias exact match
        for canonical, entry in LANDMARK_DICTIONARY.items():
            if text in entry.get("aliases", []):
                return NormalizedLocationResult(
                    raw=None,
                    normalized_location=canonical,
                    canonical_matched=True,
                    lat=entry["lat"],
                    lon=entry["lon"],
                    radius_m=entry["radius_m"],
                )
        return None


    # ---------------------------------------------------------------------------
    # 공개 API
    # ---------------------------------------------------------------------------
    @classmethod
    def normalize_location(cls, raw: Optional[str]) -> NormalizedLocationResult:
        """
        표준 장소 정규화 순수 함수.

        순서:
        1. 빈값/None → normalized_location=None
        2. 공백/괄호/기본 접미어 정리
        3. canonical exact match
        4. alias exact match
        5. 공백 제거 후 exact match (압구정 로데오 → 압구정로데오)
        6. 매칭 실패 → 원문 유지 (canonical_matched=False)
        """
        # Step 1
        if not raw or not raw.strip():
            return NormalizedLocationResult(raw=raw, normalized_location=None, canonical_matched=False)

        cleaned = raw.strip()

        # Step 2
        step2 = cls._strip_suffix(cleaned)

        # Step 3 + 4 (cleaned 먼저, step2 다음)
        for candidate in (cleaned, step2):
            hit = cls._lookup_landmark(candidate)
            if hit:
                hit.raw = raw
                return hit

        # Step 5: 공백 제거 후 재시도
        collapsed = cls._collapse_spaces(step2)
        if collapsed != step2:
            hit = cls._lookup_landmark(collapsed)
            if hit:
                hit.raw = raw
                return hit

        # Step 6: 매칭 실패 → 원문 유지
        return NormalizedLocationResult(raw=raw, normalized_location=cleaned, canonical_matched=False)


# ---------------------------------------------------------------------------
# GeoCoder (외부 API)
# ---------------------------------------------------------------------------

class GeoCoder:
    _timeout = httpx.Timeout(5.0, connect=3.0)
    _async_client: httpx.AsyncClient | None = None
    _instance: Optional["GeoCoder"] = None

    # 인메모리 캐시 (프로세스 공유, 싱글톤)
    # 키: address.strip().lower() → Dict | None
    _geocode_cache: Dict[str, Any] = {}
    # 키: (round(lat, 4), round(lng, 4)) → Dict | None
    _reverse_cache: Dict[tuple, Any] = {}
    # 키: (query.strip().lower(), limit) → list
    _search_cache: Dict[tuple, Any] = {}
    _CACHE_MAX: int = 512

    def __init__(self) -> None:
        self.client_id = os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
        self.search_client_id = os.getenv("NAVER_SEARCH_CLIENT_ID", "")
        self.search_client_secret = os.getenv("NAVER_SEARCH_CLIENT_SECRET", "")
        self.geocode_endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
        self.reverse_geocode_endpoint = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"
        self.local_search_endpoint = "https://openapi.naver.com/v1/search/local"

    @classmethod
    def get_instance(cls) -> "GeoCoder":
        """싱글톤 인스턴스를 반환한다. 프로세스 내 한 번만 로드된다."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-NCP-APIGW-API-KEY-ID": self.client_id or "",
            "X-NCP-APIGW-API-KEY": self.client_secret or "",
        }

    @classmethod
    def _client(cls) -> httpx.AsyncClient:
        if cls._async_client is None:
            cls._async_client = httpx.AsyncClient(timeout=cls._timeout)
        return cls._async_client

    async def _get_json(
        self,
        url: str,
        *,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> Dict[str, Any] | None:
        try:
            response = await self._client().get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API 요청 중 오류 발생: {e}")
            return None

    async def geocoder(self, location: str) -> Optional[Dict[str, Any]]:
        key = location.strip().lower()
        if key in self._geocode_cache:
            return self._geocode_cache[key]

        params = {"query": location}
        data = await self._get_json(self.geocode_endpoint, headers=self._headers(), params=params)

        result: Optional[Dict[str, Any]] = None
        if data and data.get("status") == "OK" and data.get("addresses"):
            target = data["addresses"][0]
            lat = float(target["y"])
            lon = float(target["x"])
            result = {
                "latitude": lat,
                "longitude": lon,
                "lat": lat,
                "lon": lon,
                "road_address": target.get("roadAddress"),
                "jibun_address": target.get("jibunAddress"),
            }
        else:
            print(f"검색 결과가 없습니다: {location}")

        if len(self._geocode_cache) >= self._CACHE_MAX:
            self._geocode_cache.pop(next(iter(self._geocode_cache)))
        self._geocode_cache[key] = result
        return result

    async def geocoder_many(self, location: str, limit: int = 5) -> list[Dict[str, Any]]:
        params = {"query": location}
        data = await self._get_json(self.geocode_endpoint, headers=self._headers(), params=params)
        if not data or data.get("status") != "OK" or not data.get("addresses"):
            return []

        results: list[Dict[str, Any]] = []
        for target in data["addresses"][:limit]:
            results.append(
                {
                    "name": None,
                    "lat": float(target["y"]),
                    "lon": float(target["x"]),
                    "road_address": target.get("roadAddress"),
                    "jibun_address": target.get("jibunAddress"),
                }
            )
        return results

    async def reverse_geocoder(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        key = (round(latitude, 4), round(longitude, 4))
        if key in self._reverse_cache:
            return self._reverse_cache[key]

        params = {
            "coords": f"{longitude},{latitude}",
            "orders": "roadaddr,addr",
            "output": "json",
        }
        data = await self._get_json(self.reverse_geocode_endpoint, headers=self._headers(), params=params)

        result: Optional[Dict[str, Any]] = None
        if not data or data.get("status", {}).get("code") != 0 or not data.get("results"):
            print(f"검색 결과가 없습니다: lat={latitude}, lon={longitude}")
        else:
            target = None
            for r in data["results"]:
                if r.get("name") == "roadaddr":
                    target = r
                    break
            if target is None:
                target = data["results"][0]

            address = self._build_address_dict(target)
            result = {
                "lat": latitude,
                "lon": longitude,
                "road_address": address.get("road_address"),
                "jibun_address": address.get("jibun_address"),
            }

        if len(self._reverse_cache) >= self._CACHE_MAX:
            self._reverse_cache.pop(next(iter(self._reverse_cache)))
        self._reverse_cache[key] = result
        return result

    async def search_places(self, query: str, limit: int = 5) -> list[Dict[str, Any]]:
        key = (query.strip().lower(), limit)
        if key in self._search_cache:
            return self._search_cache[key]

        results: list[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        local_items = await self.local_search_places(query, limit=limit)
        print(f"[Moments] local_search query='{query}' count={len(local_items)}")

        for item in local_items:
            address = item.get("road_address") or item.get("jibun_address")
            if not address:
                continue
            geocoded = await self.geocoder(address)
            if not geocoded:
                continue
            normalized = (
                (item.get("name") or query).strip(),
                (geocoded.get("road_address") or geocoded.get("jibun_address") or address).strip(),
            )
            if normalized in seen:
                continue
            seen.add(normalized)
            results.append(
                {
                    "name": item.get("name") or query,
                    "lat": geocoded.get("lat"),
                    "lon": geocoded.get("lon"),
                    "road_address": geocoded.get("road_address") or address,
                    "jibun_address": geocoded.get("jibun_address") or address,
                    "category": item.get("category"),
                    "description": item.get("description"),
                }
            )
            if len(results) >= limit:
                break

        if not results:
            geocode_items = await self.geocoder_many(query, limit=limit)
            print(f"[Moments] geocode_fallback query='{query}' count={len(geocode_items)}")
        else:
            geocode_items = []

        for item in geocode_items:
            address = item.get("road_address") or item.get("jibun_address") or query
            normalized = ((item.get("name") or query).strip(), address.strip())
            if normalized in seen:
                continue
            seen.add(normalized)
            results.append(item)
            if len(results) >= limit:
                break

        if len(self._search_cache) >= self._CACHE_MAX:
            self._search_cache.pop(next(iter(self._search_cache)))
        self._search_cache[key] = results
        return results

    async def local_search_places(self, query: str, limit: int = 5) -> list[Dict[str, Any]]:
        if not self.search_client_id or not self.search_client_secret:
            print("NAVER_SEARCH_CLIENT_ID / NAVER_SEARCH_CLIENT_SECRET is not configured.")
            return []

        headers = {
            "X-Naver-Client-Id": self.search_client_id or "",
            "X-Naver-Client-Secret": self.search_client_secret or "",
        }
        params = {"query": query, "display": max(1, min(limit, 10)), "sort": "comment"}

        data = await self._get_json(self.local_search_endpoint, headers=headers, params=params)
        if not data:
            return []

        items = data.get("items") or []
        results: list[Dict[str, Any]] = []
        for item in items:
            title = re.sub(r"<[^>]+>", "", item.get("title") or "").strip()
            road_address = (item.get("roadAddress") or "").strip() or None
            jibun_address = (item.get("address") or "").strip() or None
            category = (item.get("category") or "").strip() or None
            description = re.sub(r"<[^>]+>", "", item.get("description") or "").strip() or None
            results.append(
                {
                    "name": title or query,
                    "road_address": road_address,
                    "jibun_address": jibun_address,
                    "category": category,
                    "description": description,
                }
            )
        return results

    def _build_address_dict(self, data: Dict[str, Any]) -> Dict[str, Optional[str]]:
        region = data.get("region", {})
        land = data.get("land", {})

        admin_parts = []
        for i in range(1, 5):
            area = region.get(f"area{i}", {})
            name = area.get("name")
            if name:
                admin_parts.append(name)
        admin = " ".join(admin_parts).strip()

        road_name = land.get("name", "")
        number1 = land.get("number1", "")
        road_address = " ".join(part for part in [admin, road_name, number1] if part).strip()

        land_type = land.get("type", "1")
        number2 = land.get("number2", "")
        jibun_number = number1
        if number2:
            jibun_number = f"{number1}-{number2}"
        if land_type == "2" and jibun_number:
            jibun_number = f"산 {jibun_number}"

        jibun_address = " ".join(part for part in [admin, jibun_number] if part).strip()

        return {
            "road_address": road_address or None,
            "jibun_address": jibun_address or None,
        }
    
    
    # -----------------------------------------------------------------------
    # Naver Directions API
    # -----------------------------------------------------------------------
    _directions_cache: Dict[tuple, Any] = {}

    async def get_directions(
        self,
        coordinates: List[tuple[float, float]],
        option: str = "trafast",
    ) -> Optional[Dict[str, Any]]:
        """
        네이버 Directions 5 API로 경로를 조회한다.

        Args:
            coordinates: [(lng, lat), ...] 최소 2개, 최대 7개 (start + 5 waypoints + goal)
            option: trafast(빠른길) | tracomfort(편한길) | traoptimal(최적) | tradistance(최단)
        Returns:
            { distance, duration, path, toll_fare, fuel_price } 또는 None
        """
        if len(coordinates) < 2:
            return None

        cache_key = (tuple(coordinates), option)
        if cache_key in self._directions_cache:
            return self._directions_cache[cache_key]

        start = f"{coordinates[0][0]},{coordinates[0][1]}"
        goal = f"{coordinates[-1][0]},{coordinates[-1][1]}"

        params: Dict[str, str] = {
            "start": start,
            "goal": goal,
            "option": option,
        }

        if len(coordinates) > 2:
            waypoints = "|".join(
                f"{lng},{lat}" for lng, lat in coordinates[1:-1]
            )
            params["waypoints"] = waypoints

        url = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
        data = await self._get_json(url, headers=self._headers(), params=params)

        if not data or data.get("code") != 0:
            error_msg = data.get("message", "Unknown error") if data else "No response"
            print(f"[Directions] API error: {error_msg}")
            return None

        try:
            route = data["route"][option][0]
            summary = route["summary"]
            result = {
                "distance": summary.get("distance", 0),
                "duration": summary.get("duration", 0),
                "path": route.get("path", []),
                "toll_fare": summary.get("tollFare", 0),
                "fuel_price": summary.get("fuelPrice", 0),
            }
        except (KeyError, IndexError) as e:
            print(f"[Directions] Response parsing error: {e}")
            return None

        if len(self._directions_cache) >= self._CACHE_MAX:
            self._directions_cache.pop(next(iter(self._directions_cache)))
        self._directions_cache[cache_key] = result
        return result

    # -----------------------------------------------------------------------
    # ODsay 대중교통 API
    # -----------------------------------------------------------------------
    _transit_cache: Dict[tuple, Any] = {}

    async def get_transit_directions(
        self,
        start: tuple[float, float],
        goal: tuple[float, float],
    ) -> Optional[Dict[str, Any]]:
        """
        ODsay API로 대중교통 경로를 조회한다 (1구간).

        Args:
            start: (lng, lat)
            goal:  (lng, lat)
        Returns:
            { duration, fare, transfers, segments: [...] } 또는 None
        """
        odsay_key = os.getenv("ODSAY_API_KEY", "")
        if not odsay_key:
            print("[Transit] ODSAY_API_KEY is not configured.")
            return None

        cache_key = (start, goal)
        if cache_key in self._transit_cache:
            return self._transit_cache[cache_key]

        # ODsay API 키에 +, / 등 특수문자가 포함될 수 있어
        # httpx params의 자동 URL 인코딩을 우회하기 위해 직접 요청
        import httpx
        raw_url = (
            f"https://api.odsay.com/v1/api/searchPubTransPathT"
            f"?SX={start[0]}&SY={start[1]}&EX={goal[0]}&EY={goal[1]}"
            f"&apiKey={odsay_key}&output=json"
        )
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(raw_url)
                data = response.json()
        except Exception as e:
            print(f"[Transit] ODsay request error: {e}")
            data = None

        if not data or "result" not in data:
            error_msg = data.get("message", "Unknown error") if data else "No response"
            print(f"[Transit] ODsay API error: {error_msg} | Full response: {data}")
            return None

        try:
            path = data["result"]["path"][0]  # 첫 번째 추천 경로
            info = path["info"]

            segments = []
            for sub in path.get("subPath", []):
                traffic_type = sub.get("trafficType")  # 1=지하철, 2=버스, 3=도보
                segment: Dict[str, Any] = {
                    "traffic_type": traffic_type,
                    "distance": sub.get("distance", 0),
                    "duration": sub.get("sectionTime", 0),
                }

                if traffic_type == 1:  # 지하철
                    lane = sub.get("lane", [{}])
                    segment["lane_name"] = lane[0].get("name", "") if lane else ""
                    segment["start_name"] = sub.get("startName", "")
                    segment["end_name"] = sub.get("endName", "")
                    segment["station_count"] = sub.get("stationCount", 0)
                elif traffic_type == 2:  # 버스
                    lane = sub.get("lane", [{}])
                    segment["bus_no"] = lane[0].get("busNo", "") if lane else ""
                    segment["bus_type"] = lane[0].get("type", 0) if lane else 0
                    segment["start_name"] = sub.get("startName", "")
                    segment["end_name"] = sub.get("endName", "")
                    segment["station_count"] = sub.get("stationCount", 0)
                elif traffic_type == 3:  # 도보
                    segment["start_name"] = sub.get("startName", "")
                    segment["end_name"] = sub.get("endName", "")

                # 구간별 좌표 (폴리라인용)
                pass_stop = sub.get("passStopList", {})
                stations = pass_stop.get("stations", []) if pass_stop else []
                if stations:
                    segment["path"] = [
                        [float(s["x"]), float(s["y"])] for s in stations
                        if s.get("x") and s.get("y")
                    ]

                segments.append(segment)

            result: Dict[str, Any] = {
                "duration": info.get("totalTime", 0),
                "fare": info.get("payment", 0),
                "transfers": info.get("busTransitCount", 0) + info.get("subwayTransitCount", 0),
                "distance": info.get("totalDistance", 0),
                "segments": segments,
            }
        except (KeyError, IndexError) as e:
            print(f"[Transit] Response parsing error: {e}")
            return None

        if len(self._transit_cache) >= self._CACHE_MAX:
            self._transit_cache.pop(next(iter(self._transit_cache)))
        self._transit_cache[cache_key] = result
        return result

    async def get_transit_directions_multi(
        self,
        coordinates: List[tuple[float, float]],
    ) -> Optional[Dict[str, Any]]:
        """
        여러 장소를 구간별로 나눠 대중교통 경로를 조회한다.
        A→B, B→C, ... 를 각각 호출 후 합산.
        """
        if len(coordinates) < 2:
            return None

        cache_key = tuple(coordinates)
        if cache_key in self._transit_cache:
            return self._transit_cache[cache_key]

        all_segments = []
        total_duration = 0
        total_fare = 0
        total_transfers = 0
        total_distance = 0
        legs = []

        for i in range(len(coordinates) - 1):
            leg = await self.get_transit_directions(coordinates[i], coordinates[i + 1])
            if not leg:
                return None
            legs.append(leg)
            total_duration += leg["duration"]
            total_fare += leg["fare"]
            total_transfers += leg["transfers"]
            total_distance += leg["distance"]
            all_segments.extend(leg["segments"])

        result = {
            "duration": total_duration,
            "fare": total_fare,
            "transfers": total_transfers,
            "distance": total_distance,
            "segments": all_segments,
            "legs": legs,
        }

        if len(self._transit_cache) >= self._CACHE_MAX:
            self._transit_cache.pop(next(iter(self._transit_cache)))
        self._transit_cache[cache_key] = result
        return result

    @classmethod
    async def get_coordinates(cls, address: str) -> tuple[float, float]:
        """
        주소를 입력받아 좌표를 반환합니다.
        """
        result = await cls.get_instance().geocoder(address)
        if result:
            return result["lat"], result["lon"]
        return 0.0, 0.0

    @classmethod
    async def get_address(cls, latitude: float, longitude: float) -> str:
        """
        위도, 경도를 입력받아 주소를 반환합니다.
        """
        result = await cls.get_instance().reverse_geocoder(latitude, longitude)
        if result:
            return result.get("road_address") or result.get("jibun_address") or ""
        return ""
