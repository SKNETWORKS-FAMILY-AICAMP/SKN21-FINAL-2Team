import os
from typing import Any, Dict, Optional

import requests


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
