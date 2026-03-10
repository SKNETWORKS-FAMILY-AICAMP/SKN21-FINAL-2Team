import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

# canonical key = 표준 장소명. aliases = 사용자 입력 변형 목록.
LANDMARK_DICTIONARY: Dict[str, Dict[str, Any]] = {
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
        "aliases": ["서울대입구", "서울대입구역", "관악로"],
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
        "aliases": ["연무장길", "성수핫플", "서울숲 카페거리"],
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
        "aliases": ["을지로 노가리골목", "을지로3가", "을지로4가"],
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

def normalize_location(raw: Optional[str]) -> NormalizedLocationResult:
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
    step2 = _strip_suffix(cleaned)

    # Step 3 + 4 (cleaned 먼저, step2 다음)
    for candidate in (cleaned, step2):
        hit = _lookup_landmark(candidate)
        if hit:
            hit.raw = raw
            return hit

    # Step 5: 공백 제거 후 재시도
    collapsed = _collapse_spaces(step2)
    if collapsed != step2:
        hit = _lookup_landmark(collapsed)
        if hit:
            hit.raw = raw
            return hit

    # Step 6: 매칭 실패 → 원문 유지
    return NormalizedLocationResult(raw=raw, normalized_location=cleaned, canonical_matched=False)


def _build_landmark_desc() -> str:
    """Intent 프롬프트에 주입할 compact 표준 장소 목록 문자열 생성. 모듈 로드 시 1회 실행."""
    lines = []
    for canonical, entry in LANDMARK_DICTIONARY.items():
        aliases = entry.get("aliases", [])
        alias_str = ", ".join(aliases)
        lines.append(f"{canonical}: {alias_str}" if alias_str else canonical)
    return "\n".join(lines)


# 모듈 로드 시 1회 생성 후 상수로 캐싱
LANDMARK_DESC: str = _build_landmark_desc()


# ---------------------------------------------------------------------------
# GeoCoder (외부 API)
# ---------------------------------------------------------------------------

class GeoCoder:
    def __init__(self) -> None:
        self.client_id = os.getenv("NAVER_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET")
        self.geocode_endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
        self.reverse_geocode_endpoint = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-NCP-APIGW-API-KEY-ID": self.client_id or "",
            "X-NCP-APIGW-API-KEY": self.client_secret or "",
        }

    def geocoder(self, location: str) -> Optional[Dict[str, Any]]:
        params = {"query": location}
        try:
            response = requests.get(self.geocode_endpoint, headers=self._headers(), params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("addresses"):
                target = data["addresses"][0]
                return {
                    "lat": float(target["y"]),
                    "lng": float(target["x"]),
                    "road_address": target.get("roadAddress"),
                    "jibun_address": target.get("jibunAddress"),
                }

            print(f"검색 결과가 없습니다: {location}")
            return None
        except Exception as e:
            print(f"API 요청 중 오류 발생: {e}")
            return None

    # Keep requested name for compatibility with existing callers if needed.
    def eocoder(self, location: str) -> Optional[Dict[str, Any]]:
        return self.geocoder(location)

    def reverse_geocoder(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        params = {
            "coords": f"{longitude},{latitude}",
            "orders": "roadaddr,addr",
            "output": "json",
        }

        try:
            response = requests.get(self.reverse_geocode_endpoint, headers=self._headers(), params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                print(f"검색 결과가 없습니다: lat={latitude}, lng={longitude}")
                return None

            # Prefer roadaddr result if present.
            target = None
            for result in data["results"]:
                if result.get("name") == "roadaddr":
                    target = result
                    break
            if target is None:
                target = data["results"][0]

            address = self._build_address_dict(target)
            return {
                "lat": latitude,
                "lng": longitude,
                "road_address": address.get("road_address"),
                "jibun_address": address.get("jibun_address"),
            }
        except Exception as e:
            print(f"API 요청 중 오류 발생: {e}")
            return None

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
