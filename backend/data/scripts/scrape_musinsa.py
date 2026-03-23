"""
무신사 오프라인 스토어 전체 수집 스크립트 (Playwright)
===================================================
1) ID 1~100 순회하며 개별 매장 페이지 방문
2) 매장명, 주소, 이미지, 영업시간, 전화번호 수집
3) 좌표 변환 (Nominatim)
4) 투어 JSON 형식으로 저장
"""

import asyncio
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "musinsa_투어.json"

# 수집 대상: 지역별 최대 5개씩
TARGET_AREAS = {
    "강남": ["강남", "압구정", "서초구"],
    "잠실": ["잠실", "롯데월드몰", "롯데백화점 잠실", "송파구"],
    "홍대": ["홍대", "마포구"],
    "성수": ["성수", "성동구"],
    "명동": ["명동", "중구"],
}
MAX_PER_AREA = 5


def classify_area(store_name: str, addr: str) -> str | None:
    """매장이 어느 지역에 속하는지 판별"""
    for area, keywords in TARGET_AREAS.items():
        for kw in keywords:
            if kw in store_name or kw in addr:
                return area
    return None


async def extract_store(page) -> dict | None:
    """현재 페이지에서 매장 정보를 추출"""
    all_text = await page.inner_text("body")

    # 매장명: h2 태그에서 추출 (디버그 결과 확인)
    store_name = ""
    h2s = await page.query_selector_all("h2")
    for h2 in h2s:
        t = (await h2.text_content() or "").strip()
        if 5 < len(t) < 60 and any(
            kw in t for kw in ["무신사", "킥스", "뷰티 스페이스"]
        ):
            store_name = t
            break

    if not store_name:
        return None

    # 주소: "서울"로 시작하는 줄
    addr = ""
    for line in all_text.split("\n"):
        line = line.strip()
        if line.startswith("서울") and len(line) > 10:
            addr = line
            break

    if not addr:
        return None

    # 이미지: alt에 "스토어 사진" 포함
    img_url = ""
    imgs = await page.query_selector_all("img[alt]")
    for img in imgs:
        alt = (await img.get_attribute("alt")) or ""
        if "스토어 사진" in alt:
            img_url = (await img.get_attribute("src")) or ""
            break

    # 영업시간: "Every day", "매일" 패턴 매칭
    hours = ""
    en_match = re.search(
        r"Every\s*day\s*[:：]?\s*(\d{1,2}:\d{2}\s*[~\-]\s*\d{1,2}:\d{2})",
        all_text,
    )
    ko_match = re.search(
        r"매일\s*[:：]?\s*(\d{1,2}:\d{2}\s*[~\-]\s*\d{1,2}:\d{2})", all_text
    )
    if ko_match:
        hours = f"매일 {ko_match.group(1)}"
    elif en_match:
        hours = f"매일 {en_match.group(1)}"

    # 전화번호
    tel = ""
    tel_match = re.search(r"(\d{2,4}-\d{3,4}-\d{4})", all_text)
    if tel_match:
        tel = tel_match.group(1)

    return {
        "name": store_name,
        "addr": addr,
        "img": img_url,
        "hours": hours,
        "tel": tel,
    }


def geocode(addr: str) -> tuple[float, float]:
    """Nominatim으로 좌표 변환"""
    clean = re.sub(r"\(.*?\)", "", addr)
    clean = re.sub(r"B?\d+F.*", "", clean).strip()

    for query in [clean, " ".join(clean.split()[:4]), " ".join(clean.split()[:3])]:
        encoded = urllib.parse.quote(query)
        api_url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"
        req = urllib.request.Request(
            api_url, headers={"User-Agent": "MusinsaCollector/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            pass
        time.sleep(1.1)

    return 0.0, 0.0


async def main():
    area_counts = {a: 0 for a in TARGET_AREAS}
    store_map = {}  # sid -> info dict

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("▶ 매장 스캔 (ID 1~100)...")
        for sid in range(1, 101):
            # 모든 지역 채웠으면 종료
            if all(c >= MAX_PER_AREA for c in area_counts.values()):
                print("  → 모든 지역 수집 완료, 스캔 종료")
                break

            url = f"https://www.musinsa.com/offline/{sid}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)  # CSR 렌더링 대기
            except Exception:
                continue

            info = await extract_store(page)
            if not info:
                continue

            # 지역 분류
            area = classify_area(info["name"], info["addr"])
            if area is None:
                continue
            if area_counts[area] >= MAX_PER_AREA:
                continue

            area_counts[area] += 1
            info["area"] = area
            store_map[sid] = info
            print(f"  ✓ [{sid:>2}] [{area}] {info['name']}")
            print(f"         주소: {info['addr']}")
            print(f"         이미지: {info['img'][:80] if info['img'] else '(없음)'}")
            print(f"         영업: {info['hours'] or '(미확인)'} | 전화: {info['tel'] or '(미확인)'}")

        await browser.close()

    print(f"\n▶ 수집 결과: {sum(area_counts.values())}개 매장")
    for area, cnt in area_counts.items():
        print(f"   {area}: {cnt}개")

    # ── 좌표 변환 ──
    print("\n▶ 좌표 변환 (Nominatim)...")
    for sid, info in store_map.items():
        lat, lon = geocode(info["addr"])
        info["lat"] = lat
        info["lon"] = lon
        status = "✓" if lat != 0.0 else "✗"
        print(f"  {status} {info['name']}: ({lat}, {lon})")

    # ── JSON 생성 ──
    print("\n▶ JSON 생성...")
    results = []
    for sid, info in store_map.items():
        entry = {
            "contentid": f"MUSINSA_{sid:03d}",
            "title": info["name"],
            "contenttypeid": "투어",
            "contenttypeid_code": 99,
            "image": info["img"],
            "usetime": info["hours"] or None,
            "restdate": None,
            "parking": None,
            "fee": "무료 입장",
            "addr": info["addr"],
            "mapy": info["lat"],
            "mapx": info["lon"],
            "tel": info["tel"] or None,
            "source": "musinsa",
            "category_depth": "쇼핑 > 패션",
            "summary": f"{info['name']}은(는) 무신사의 오프라인 매장으로, 다양한 브랜드의 패션 아이템을 직접 체험하고 구매할 수 있는 공간입니다.",
            "description": f"{info['name']}은(는) {info['addr']}에 위치한 무신사 오프라인 매장입니다. 무신사에서 인기 있는 다양한 브랜드의 의류, 신발, 액세서리 등을 직접 체험하고 구매할 수 있습니다.",
            "subway_info": None,
            "website": f"https://www.musinsa.com/offline/{sid}",
            "tags": ["무신사", "패션", "쇼핑", info["area"], "오프라인매장"],
            "updated_at": "2026.03.23",
        }
        results.append(entry)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료! {len(results)}개 매장 → {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
