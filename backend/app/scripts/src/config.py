from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent            # .../backend/app/scripts/src
APP_DIR = SRC_DIR.parents[2]                         # .../backend/app

# .env 로드: src/.env 우선
load_dotenv(SRC_DIR / ".env")
load_dotenv()

TOURAPI_KEY = os.getenv("TOURAPI_KEY", "").strip()
TOURAPI_MOBILE_OS = os.getenv("TOURAPI_MOBILE_OS", "ETC").strip()
TOURAPI_MOBILE_APP = os.getenv("TOURAPI_MOBILE_APP", "tour_all").strip()
TOURAPI_BASE_URL = os.getenv("TOURAPI_BASE_URL", "https://apis.data.go.kr/B551011/KorService2").strip()
TOURAPI_TYPE = os.getenv("TOURAPI_TYPE", "json").strip()

SEOUL_AREA_CODE = int(os.getenv("SEOUL_AREA_CODE", "1"))
DEFAULT_NUM_ROWS = int(os.getenv("DEFAULT_NUM_ROWS", "1000"))
DEFAULT_THROTTLE_S = float(os.getenv("DEFAULT_THROTTLE_S", "0.2"))

OUTPUT_DIR = APP_DIR / "data"
