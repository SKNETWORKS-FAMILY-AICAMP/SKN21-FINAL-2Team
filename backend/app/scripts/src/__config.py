from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

TYPE_LABELS: Dict[int, str] = {
    12: "관광지",
    14: "문화시설",
    15: "축제공연행사",
    25: "여행코스",
    28: "레포츠",
    32: "숙박",
    39: "음식점",
}

@dataclass
class Settings:
    project_root: Path
    data_dir: Path
    checkpoints_dir: Path

    tour_api_key: str
    tour_base_url: str
    tour_mobile_os: str
    tour_mobile_app: str
    tour_api_type: str

    tour_api_area_based_url: str
    tour_api_detail_intro_url: str
    tour_api_detail_info_url: str

    kakao_rest_api_key: str

    naver_client_id: str
    naver_client_secret: str


def load_settings() -> Settings:
    this = Path(__file__).resolve()
    project_root = this.parents[4]

    env_path = project_root / "backend" / "app" / "scripts" / "src" / ".env"
    load_dotenv(env_path)

    data_dir = project_root / "backend" / "data"
    checkpoints_dir = data_dir / "checkpoints"
    data_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    base = os.getenv("TOURAPI_BASE_URL", "https://apis.data.go.kr/B551011/KorService2").strip().rstrip("/")

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        checkpoints_dir=checkpoints_dir,

        tour_api_key=os.getenv("TOURAPI_KEY", "").strip(),
        tour_base_url=base,
        tour_mobile_os=os.getenv("TOURAPI_MOBILE_OS", "ETC").strip(),
        tour_mobile_app=os.getenv("TOURAPI_MOBILE_APP", "polarisK").strip(),
        tour_api_type=os.getenv("TOURAPI_TYPE", "json").strip(),

        tour_api_area_based_url=f"{base}/areaBasedList2",
        tour_api_detail_intro_url=f"{base}/detailIntro2",
        tour_api_detail_info_url=f"{base}/detailInfo2",

        kakao_rest_api_key=os.getenv("KAKAO_REST_API_KEY", "").strip(),

        naver_client_id=os.getenv("NAVER_CLIENT_ID", "").strip(),
        naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", "").strip(),
    )


def places_jsonl_path(settings: Settings, ct: int) -> Path:
    return settings.data_dir / f"{ct}_{TYPE_LABELS.get(ct, str(ct))}.jsonl"


def places_test_jsonl_path(settings: Settings, ct: int) -> Path:
    return settings.data_dir / f"{ct}_{TYPE_LABELS.get(ct, str(ct))}_TEST1.jsonl"


def geocode_cache_path(settings: Settings) -> Path:
    return settings.data_dir / "geocode_cache.json"


def checkpoint_path(settings: Settings, ct: int):
    return settings.checkpoints_dir / f"ct_{ct}_progress.json"


def legacy_progress_path(settings: Settings, ct: int) -> Path:
    return settings.checkpoints_dir / f"ct_{ct}_progress.json"
