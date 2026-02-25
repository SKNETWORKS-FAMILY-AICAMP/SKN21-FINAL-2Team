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

NONE_VALUES = [None, "", [], {}, 0, 0.0]

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
    """
    12_관광지     : ['addr', 'contentid', 'contenttypeid', 'contenttypeid_code', 'image', 'mapx', 'mapy', 'parking', 'pet_raw', 'restdate', 'tel', 'title', 'usetime']
    39_음식점     : ['addr', 'contentid', 'contenttypeid', 'contenttypeid_code', 'image', 'mapx', 'mapy', 'pet_raw', 'tel', 'title']
    15_축제공연행사 : ['addr', 'contentid', 'contenttypeid', 'contenttypeid_code', 'image', 'mapx', 'mapy', 'tel', 'title']
    28_레포츠     : ['addr', 'contentid', 'contenttypeid', 'contenttypeid_code', 'fees', 'image', 'mapx', 'mapy', 'pet_raw', 'tel', 'title']
    32_숙박       : ['addr', 'contentid', 'contenttypeid', 'contenttypeid_code', 'image', 'mapx', 'mapy', 'pet_raw', 'tel', 'title']
    14_문화시설    : ['addr', 'contentid', 'contenttypeid', 'contenttypeid_code', 'image', 'mapx', 'mapy', 'pet_raw', 'tel', 'title']
    """
    print(f"[INFO] Start ingestion.. total {len(data)} items.")
    for item in data:
        def remove_empty_values(data):
            """
            재귀적으로 dict와 list 내부의 빈 값(None, "", [], {}, 0, 0.0)을 제거합니다.
            """
            if isinstance(data, dict):
                # 딕셔너리 컴프리헨션을 사용해 재귀적으로 탐색
                return {
                    k: v for k, v in ((k, remove_empty_values(v)) for k, v in data.items())
                    if v not in NONE_VALUES
                }
            elif isinstance(data, list):
                # 리스트 내부 요소들도 재귀적으로 탐색
                return [
                    v for v in (remove_empty_values(i) for i in data)
                    if v not in NONE_VALUES
                ]
            else:
                # 더 이상 쪼갤 수 없는 값(str, int, bool 등)은 그대로 반환
                return data
            
        new_payload = remove_empty_values(item)
        del(new_payload['contenttypeid_code'])
        
        lat = float(item.get("mapx", "0"))
        lng = float(item.get("mapy", "0"))
        address = item.get("addr", "")
        if len(address) > 0:
            result = GeoCoder().eocoder(address)
            if result:
                new_payload['road_address'] = result['road_address']
                new_payload['old_address'] = result['jibun_address']
                if lat == 0.0 or lng == 0.0:
                    item['mapx'] = result['lat']
                    item['mapy'] = result['lng']
        else:
            # 주소가 비어있는 경우
            if lat != 0.0 and lng != 0.0:
                latlng = GeoCoder().reverse_geocoder(lat, lng)
                if latlng is not None:
                    new_payload['road_address'] = latlng['road_address']
                    new_payload['old_address'] = latlng['jibun_address']
                    new_payload['addr'] = new_payload['road_address']

        yield new_payload
