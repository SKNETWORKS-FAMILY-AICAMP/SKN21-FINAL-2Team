import os
import requests
import io
import json
import re
import hashlib
from collections import Counter
from PIL import Image
from dotenv import load_dotenv

# Do not override runtime/container environment variables.
load_dotenv()

import base64
from app.utils.geocoder import GeoCoder

NONE_VALUES = [None, "", [], {}, 0, 0.0]
ADDR_TOKEN_SUFFIXES = ("시", "군", "구", "동", "읍", "면", "리", "로", "길")
ADDR_TOKEN_STOPWORDS = {"", "대한민국", "한국"}
ADDR_TOKEN_MAX = 24
SPARSE_TOKEN_PATTERN = re.compile(r"\d+-\d+|[0-9]+|[가-힣a-z]+")

# download image from URL or Base64
def download_image(url: str, timeout: int = 600) -> Image.Image | None:
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


def _safe_float(value):
    try:
        if value in (None, ""):
            return None
        parsed = float(value)
        if parsed != parsed:
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def build_addr_tokens(payload: dict) -> list[str]:
    source = (
        str(payload.get("road_address") or "").strip()
        or str(payload.get("old_address") or "").strip()
        or str(payload.get("addr") or "").strip()
    )
    if not source:
        return []

    text = source.lower()
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"(?<!\d)-|-(?!\d)", " ", text)
    text = re.sub(r"[,/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    raw_tokens = re.findall(r"\d+-\d+|[가-힣a-z0-9]+", text)
    tokens: list[str] = []
    for token in raw_tokens:
        if token in ADDR_TOKEN_STOPWORDS:
            continue
        if len(token) == 1 and not token.isdigit():
            continue

        tokens.append(token)
        if len(token) > 1 and token.endswith(ADDR_TOKEN_SUFFIXES):
            stem = token[:-1].strip()
            if stem and stem not in ADDR_TOKEN_STOPWORDS:
                if len(stem) > 1 or stem.isdigit():
                    tokens.append(stem)

    deduped: list[str] = []
    for token in tokens:
        if token not in deduped:
            deduped.append(token)
        if len(deduped) >= ADDR_TOKEN_MAX:
            break
    return deduped


def build_sparse_text(payload: dict) -> str:
    title = str(payload.get("title") or payload.get("name") or "").strip()
    category = str(payload.get("contenttypeid") or payload.get("category") or "").strip()
    address = (
        str(payload.get("road_address") or "").strip()
        or str(payload.get("old_address") or "").strip()
        or str(payload.get("addr") or "").strip()
    )
    addr_tokens = payload.get("addr_tokens") if isinstance(payload.get("addr_tokens"), list) else build_addr_tokens(payload)
    parts = [title, category, address, " ".join(addr_tokens)]
    return " ".join(part for part in parts if part).strip()


def build_sparse_vector(text: str) -> tuple[list[int], list[float]]:
    text = str(text or "").lower().strip()
    if not text:
        return [], []

    tokens = [tok for tok in SPARSE_TOKEN_PATTERN.findall(text) if tok]
    if not tokens:
        return [], []

    counts = Counter(tokens)
    items: list[tuple[int, float]] = []
    for token, freq in counts.items():
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16)
        items.append((idx, float(freq)))

    items.sort(key=lambda x: x[0])
    return [idx for idx, _ in items], [val for _, val in items]


def enrich_payload_geo_and_addr_tokens(payload: dict) -> dict:
    lat = _safe_float(payload.get("mapy"))
    lng = _safe_float(payload.get("mapx"))

    if lat is None:
        lat = _safe_float(payload.get("lat"))
    if lng is None:
        lng = _safe_float(payload.get("lng"))

    if (
        lat is not None
        and lng is not None
        and -90.0 <= lat <= 90.0
        and -180.0 <= lng <= 180.0
        and not (abs(lat) < 1e-9 and abs(lng) < 1e-9)
    ):
        payload["geo"] = {"lat": lat, "long": lng}

    payload["addr_tokens"] = build_addr_tokens(payload)
    return payload


def enrich_payload_llm_text(payload: dict) -> dict:
    title = payload.get("title") or payload.get("name") or ""
    address = (
        payload.get("road_address") or
        payload.get("old_address") or
        payload.get("addr") or ""
    )
    category = payload.get("contenttypeid") or ""
    description = payload.get("llm_text") or payload.get("description") or ""

    # 앵커링: 이름+주소 앞에 붙이고, 자연어 설명 이어붙임
    parts = []
    if title:
        parts.append(f"장소명: {title}")
    if category:
        parts.append(f"카테고리: {category}")
    if address:
        parts.append(f"위치: {address}")
    if description:
        parts.append(description)

    payload["llm_text"] = " | ".join(parts)
    return payload


def ingest_data(data):
    print(f"[INFO] Start ingestion.. total {len(data)} items.")
    
    def remove_empty_values(d):
        if isinstance(d, dict):
            return {
                k: v for k, v in ((k, remove_empty_values(v)) for k, v in d.items())
                if v not in NONE_VALUES
            }
        elif isinstance(d, list):
            return [
                v for v in (remove_empty_values(i) for i in d)
                if v not in NONE_VALUES
            ]
        elif isinstance(d, str):
            # 줄바꿈 및 <br> 태그 제거
            import re
            text = d.replace("\n", " ")
            text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
            # 연속된 공백 제거 및 앞뒤 트림
            return re.sub(r"\s+", " ", text).strip()
        return d

    for item in data:
        # 1. 지오코딩 및 주소 토큰화 준비
        lat = _safe_float(item.get("mapy")) or 0.0
        lng = _safe_float(item.get("mapx")) or 0.0
        address = item.get("addr", "")

        if address:
            result = GeoCoder().eocoder(address)
            if result:
                item['road_address'] = result.get('road_address')
                item['old_address'] = result.get('jibun_address')
                # 좌표가 없으면 지오코딩 결과로 채움
                if lat == 0.0 or lng == 0.0:
                    item['mapy'] = result.get('lat')
                    item['mapx'] = result.get('lng')
        elif lat != 0.0 and lng != 0.0:
            # 주소는 없는데 좌표는 있는 경우 리버스 지오코딩
            latlng = GeoCoder().reverse_geocoder(lat, lng)
            if latlng:
                item['road_address'] = latlng.get('road_address')
                item['old_address'] = latlng.get('jibun_address')
                item['addr'] = item['road_address']

        # 2. 불필요한 필드 제거 및 데이터 정제
        if 'contenttypeid_code' in item:
            del item['contenttypeid_code']
        
        # 정제된 딕셔너리 생성 (최종 Qdrant 필드 생성은 qdrant_setup.py에서 수행)
        clean_payload = remove_empty_values(item)
        
        yield clean_payload


