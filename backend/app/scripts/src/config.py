from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 로드
# 프로젝트 루트/.env 기준
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()  # 보조

# TOUR API
TOURAPI_KEY = os.getenv("TOURAPI_KEY", "").strip()
TOURAPI_MOBILE_OS = os.getenv("TOURAPI_MOBILE_OS", "ETC").strip()
TOURAPI_MOBILE_APP = os.getenv("TOURAPI_MOBILE_APP", "polarisK").strip()
TOURAPI_BASE_URL = os.getenv("TOURAPI_BASE_URL", "https://apis.data.go.kr/B551011/KorService2").strip()
TOURAPI_TYPE = os.getenv("TOURAPI_TYPE", "json").strip()

# 공통 옵션
SEOUL_AREA_CODE = 1
DEFAULT_NUM_ROWS = 1000

# 요청 정책 (요청한 값 반영)
DEFAULT_THROTTLE_S = 2.0
DEFAULT_BATCH_SIZE = 50
DEFAULT_BATCH_SLEEP_S = 30.0

# 수집 대상 카테고리
TARGET_CONTENT_TYPES = {
    12: "관광지",
    14: "문화시설",
    25: "여행코스",
}

# 출력 경로
OUTPUT_DIR = ROOT_DIR / "output"
