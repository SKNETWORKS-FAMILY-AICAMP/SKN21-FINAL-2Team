"""
무신사 오프라인 스토어 이미지 수집 스크립트 (Playwright)
=====================================================
각 매장 페이지(/offline/{id})를 방문하여 스토어 사진 이미지 URL을 수집합니다.

사용법:
    python3 backend/data/scripts/scrape_musinsa_images.py
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BACKEND_DIR / "data" / "musinsa_투어.json"

# 수집 대상 매장명 목록
TARGET_STORES = {
    "무신사 스토어 강남",
    "무신사 스탠다드 강남점",
    "무신사 엠프티 압구정 베이스먼트",
    "무신사 스토어 롯데백화점 잠실점",
    "무신사 스탠다드 롯데월드몰 잠실점",
    "무신사 스탠다드 스포츠 롯데월드몰 잠실점",
    "무신사 스토어 홍대",
    "무신사 킥스 홍대",
    "무신사 스탠다드 홍대점",
    "무신사 스토어 성수",
    "무신사 킥스 성수",
    "무신사 엠프티 성수",
    "무신사 스탠다드 성수점",
    "무신사 뷰티 스페이스 1",
    "무신사 스토어 명동",
    "무신사 스탠다드 명동점",
}


async def main():
    found = {}  # store_name -> image_url

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for store_id in range(1, 100):
            if len(found) >= len(TARGET_STORES):
                break

            url = f"https://www.musinsa.com/offline/{store_id}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception:
                continue

            # 매장명 추출
            store_name = ""
            for sel in ["strong", "h3"]:
                els = await page.query_selector_all(sel)
                for el in els:
                    text = (await el.text_content() or "").strip()
                    if 5 < len(text) < 60 and any(
                        kw in text
                        for kw in ["무신사", "킥스", "뷰티 스페이스"]
                    ):
                        store_name = text
                        break
                if store_name:
                    break

            if not store_name or store_name not in TARGET_STORES:
                continue

            # 이미지 추출
            imgs = await page.query_selector_all("img")
            img_url = ""
            for img in imgs:
                alt = (await img.get_attribute("alt")) or ""
                if "스토어 사진" in alt:
                    img_url = (await img.get_attribute("src")) or ""
                    break

            if img_url:
                found[store_name] = img_url
                print(f"  OK [{store_id}] {store_name} → {img_url[:80]}...")
            else:
                print(f"  WARN [{store_id}] {store_name} → 이미지 없음")

        await browser.close()

    # JSON 업데이트
    with open(DATA_PATH, encoding="utf-8") as f:
        stores = json.load(f)

    updated = 0
    for store in stores:
        title = store.get("title", "")
        if title in found:
            store["image"] = found[title]
            updated += 1

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {updated}/{len(TARGET_STORES)}개 매장 이미지 업데이트")
    not_found = TARGET_STORES - set(found.keys())
    if not_found:
        print(f"미발견: {', '.join(not_found)}")
    print(f"저장: {DATA_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
