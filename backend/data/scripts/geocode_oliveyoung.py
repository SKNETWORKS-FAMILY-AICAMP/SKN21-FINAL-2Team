"""
올리브영 매장 데이터에 좌표(mapy/mapx) 추가 스크립트
=====================================================
입력: data/oliveyoung_투어.json
출력: data/oliveyoung_투어.json (좌표 추가된 버전)

사용법:
    cd backend
    python data/scripts/geocode_oliveyoung.py
"""

import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.utils.geocoder import GeoCoder


async def main():
    data_path = BACKEND_DIR / "data" / "oliveyoung_투어.json"

    with open(data_path, encoding="utf-8") as f:
        stores = json.load(f)

    geo = GeoCoder()
    updated = 0
    failed = []

    for store in stores:
        if store.get("mapy") and store.get("mapx"):
            continue

        addr = store.get("addr")
        if not addr:
            continue

        result = await geo.geocoder(addr)
        if result:
            store["mapy"] = result["lat"]
            store["mapx"] = result["lon"]
            updated += 1
            print(f"  OK: {store['title']} → ({result['lat']}, {result['lon']})")
        else:
            failed.append(store["title"])
            print(f"  FAIL: {store['title']} ({addr})")

        await asyncio.sleep(0.1)  # rate limit

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {updated}건 업데이트, {len(failed)}건 실패")
    if failed:
        print(f"실패 목록: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
