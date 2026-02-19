import os
import requests
import io
import json
from PIL import Image
from dotenv import load_dotenv

# Do not override runtime/container environment variables.
load_dotenv()

import base64
from app.utils.geocoder import GeoCoder

# download image from URL or Base64
def download_image(url: str, timeout: int = 10) -> Image.Image | None:
    try:
        # 1. Base64 Handling
        if url.startswith("data:image"):
            # Format: "data:image/png;base64,iVBORw0KGgo..."
            header, encoded = url.split(",", 1)
            data = base64.b64decode(encoded)
            return Image.open(io.BytesIO(data)).convert("RGB")
            
        # 2. Local Path Handling
        if os.path.exists(url):
            return Image.open(url).convert("RGB")
            
        # 3. URL Handling
        if url.startswith("http"):
            r = requests.get(url, timeout=timeout, stream=True)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content)).convert("RGB")
            
        print(f"[WARN] Invalid image path/url: {url[:50]}...")
        return None

    except Exception as e:
        print(f"[WARN] download/decode failed: {url[:50]}... err={e}")
        return None


def ingest_data(data):
    print(f"[INFO] Start ingestion.. total {len(data)} items.")
    geocoder_client = GeoCoder()

    for item in data:
        # try:
        # 1. Prepare fields
        place_id = item.get("contentid")
        name = item.get("title", "")
        address = item.get("addr1", "") + " " + item.get("addr2", "")
        
        # Description generation — 텍스트 임베딩에 사용될 핵심 정보 포함
        raw_category = item.get("contenttypeid", "")
        
        # 카테고리 ID -> 한글 매핑
        CONTENT_TYPE_MAP = {
            "12": "관광지",
            "14": "문화시설",
            "15": "축제공연행사",
            "28": "레포츠",
            "32": "숙박",
            "39": "음식점"
        }
        category = CONTENT_TYPE_MAP.get(str(raw_category), str(raw_category))

        desc_parts = [name]
        if category:
            desc_parts.append(category)
        if address.strip():
            desc_parts.append(address.strip())
        description = " ".join(desc_parts) + "\n"

        # 부가 정보 추가
        for key, value in item.items():
            if key == "usetime" and value:
                description += f"이용시간: {value}\n"
            elif key == "parking" and value:
                description += f"주차: {value}\n"
            elif key == "restdate" and value:
                description += f"휴일: {value}\n"
    
        # 2) 주소 -> 좌표 변환
        lat = item.get("mapx")
        lng = item.get("mapy")
        if lat is None or lng is None:
            latlng = geocoder_client.eocoder(address)
            if latlng is None:
                print(f"[ERROR] 좌표 변환 실패, 건너뜀: {address}")
                pass
                
        # Category (이미 description 생성부에서 추출됨)
        
        # Image URLs
        first_image_url = item.get("firstimage", "")
        image_urls = item.get("photo_urls", [])
        if first_image_url:
            image_urls.insert(0, first_image_url)
            
        yield {
            "place_id": place_id,
            "description": description,
            "image_urls": image_urls, 
            "category": category,
            "address": address,
            "title": name,
            "lat": lat,
            "lng": lng
        }
