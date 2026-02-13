from __future__ import annotations

from src.collectors.area_collector import collect_category_dataset
from src.config import (
    TOURAPI_BASE_URL,
    TOURAPI_KEY,
    TOURAPI_MOBILE_OS,
    TOURAPI_MOBILE_APP,
    TOURAPI_TYPE,
    OUTPUT_DIR,
    SEOUL_AREA_CODE,
    DEFAULT_NUM_ROWS,
    DEFAULT_THROTTLE_S,
    DEFAULT_BATCH_SIZE,
    DEFAULT_BATCH_SLEEP_S,
)

if __name__ == "__main__":
    if not TOURAPI_KEY:
        raise ValueError("TOURAPI_KEY가 비어있음. .env 확인 필요")

    collect_category_dataset(
        base_url=TOURAPI_BASE_URL,
        service_key=TOURAPI_KEY,
        mobile_os=TOURAPI_MOBILE_OS,
        mobile_app=TOURAPI_MOBILE_APP,
        resp_type=TOURAPI_TYPE,
        outdir=OUTPUT_DIR,
        content_type_id=12,
        label="관광지",
        area_code=SEOUL_AREA_CODE,
        num_rows=DEFAULT_NUM_ROWS,
        throttle_s=DEFAULT_THROTTLE_S,
        batch_size=DEFAULT_BATCH_SIZE,        # 50
        batch_sleep_s=DEFAULT_BATCH_SLEEP_S,  # 30
    )
