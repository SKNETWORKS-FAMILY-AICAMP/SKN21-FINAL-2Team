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

geocoder_client = GeoCoder()

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


def ingest_data(data):
    print(f"[INFO] Start ingestion.. total {len(data)} items.")

    for item in data:
        # try:
        # 1. Prepare fields
        place_id = item.get("id")
        name = item.get("name", "")
        address = item.get("주소", "")
        
        # Description generation (combining relevant fields)
        desc_parts = []
        for key, value in item.items():
            if isinstance(value, str) and key not in ["id", "name", "주소"]:
                desc_parts.append(f"{key}: {value}")

        description = " ".join(desc_parts)
        
        # 2) 주소 -> 좌표 변환
        latlng = geocoder_client.eocoder(address)
        if latlng is None:
            print(f"[ERROR] 좌표 변환 실패, 건너뜀: {address}")
            pass
        
        # Region extraction (simple heuristic from address)
        region = address.split(" ")[1] if len(address.split(" ")) > 1 else "기타"
        
        # Category
        category = "관광지" # Fixed for now or extract if available
        
        # Image URLs
        image_urls = item.get("photo_urls", [])
            
        yield {
            "place_id": place_id,
            "description": description,
            "image_urls": image_urls, 
            "region": region,
            "category": category,
            "address": address,
            "title": name,
            "lat": latlng.get("lat") if latlng else 0,
            "lng": latlng.get("lng") if latlng else 0,
        }
            # # 2. Add Place (which handles images internally)
            # self.add_place(
            #     place_id=place_id,
            #     description=description,
            #     image_urls=image_urls,
            #     payload={
            #         "region": region,
            #         "category": category,
            #         "address": address,
            #         "title": name,
            #         "lat": latlng.get("lat") if latlng else 0,
            #         "lng": latlng.get("lng") if latlng else 0,
            #     }
            # )
            
                
        # except Exception as e:
        #     print(f"[ERROR] Failed to ingest item {item.get('name')}: {e}")
            
    # print(f"[INFO] Ingestion finished. Success: {success_count}/{len(data)}")
