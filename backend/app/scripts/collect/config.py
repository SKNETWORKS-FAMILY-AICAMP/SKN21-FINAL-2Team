"""수집 파이프라인 공통 설정"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트 기준 .env 로드
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_PATH)

# ── API 키 ──
TOURAPI_KEY = os.getenv("TOURAPI_KEY", "")
VISITSEOUL_API_KEY = os.getenv("VISITSEOUL_API_KEY", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
SEOUL_OPENDATA_KEY = os.getenv("SEOUL_OPENDATA_KEY", "")

# ── 출력 디렉토리 ──
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── HTTP 공통 설정 ──
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.3  # API 호출 간 대기 (초)
MAX_RETRIES = 3

# ── TourAPI ──
TOURAPI_BASE = "https://apis.data.go.kr/B551011/KorService2"
TOURAPI_PARAMS = {
    "serviceKey": TOURAPI_KEY,
    "MobileOS": "ETC",
    "MobileApp": "polarisK",
    "_type": "json",
}
TOURAPI_CONTENT_TYPES = {
    "12": "관광지",
    "14": "문화시설",
    "28": "레포츠",
    "32": "숙박",
    "39": "음식점",
}

# ── VisitSeoul ──
VISITSEOUL_BASE = "https://api-call.visitseoul.net"
VISITSEOUL_HEADERS = {
    "Accept": "application/json;charset=UTF-8",
    "Content-Type": "application/json;charset=UTF-8",
    "VISITSEOUL-API-KEY": VISITSEOUL_API_KEY,
}

# ── Popply ──
POPPLY_API_URL = "https://api.popply.co.kr/api/store/"
POPPLY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "x-source-param": "boardSearch",
}

# ── 서울 열린데이터광장 (문화행사 정보) ──
SEOUL_CULTURE_BASE = "http://openAPI.seoul.go.kr:8088"
SEOUL_CULTURE_SERVICE = "culturalEventInfo"
