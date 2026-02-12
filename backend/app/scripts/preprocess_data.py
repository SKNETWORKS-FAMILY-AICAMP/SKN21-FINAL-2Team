import os
import requests
import io
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv(override=True)

import base64

# download image from URL or Base64
def download_image(url: str, timeout: int = 10) -> Image.Image | None:
    try:
        # 1. Base64 Handling
        if url.startswith("data:image"):
            # Format: "data:image/png;base64,iVBORw0KGgo..."
            header, encoded = url.split(",", 1)
            data = base64.b64decode(encoded)
            return Image.open(io.BytesIO(data)).convert("RGB")
            
        # 2. URL Handling
        if url.startswith("http"):
            r = requests.get(url, timeout=timeout, stream=True)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content)).convert("RGB")
            
        print(f"[WARN] Invalid image path/url: {url[:50]}...")
        return None

    except Exception as e:
        print(f"[WARN] download/decode failed: {url[:50]}... err={e}")
        return None


def location_to_latlng(location: str) -> tuple[float, float] | None:
    """
    네이버 Geocoding API를 사용하여 주소를 좌표(위도, 경도)로 변환합니다.
    """
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    
    headers = {
        "Content-Type": "application/json",
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
    }
    
    params = {
        "query": location
    }
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status() # 에러 발생 시 예외 발생
        data = response.json()
        
        if data['status'] == 'OK' and data['addresses']:
            # 가장 검색 결과가 높은 첫 번째 주소 정보 가져오기
            target = data['addresses'][0]
            lat = float(target['y']) # 위도
            lng = float(target['x']) # 경도
            
            # 주소 정보와 함께 반환 (디버깅 용이)
            return {
                "lat": lat,
                "lng": lng,
                "road_address": target.get('roadAddress'),
                "jibun_address": target.get('jibunAddress')
            }
        else:
            print(f"검색 결과가 없습니다: {location}")
            return None
            
    except Exception as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None