"""
쇼핑 매장 통합 수집 스크립트 (다이소 / 무신사 / 올리브영)
=======================================================
Playwright + Naver Image Search API를 사용하여
각 브랜드별 매장 정보를 수집하고 JSON으로 저장합니다.

사용법:
    python data/scripts/scrape_all.py              # 전체
    python data/scripts/scrape_all.py daiso         # 다이소만
    python data/scripts/scrape_all.py musinsa       # 무신사만
    python data/scripts/scrape_all.py oliveyoung    # 올리브영만
"""

import asyncio
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# ── 경로 / 설정 ──
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

NAVER_CLIENT_ID = os.getenv("NAVER_SEARCH_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET", "")

MAX_PER_AREA = 5

# =====================================================================
# 공통 유틸
# =====================================================================

def search_naver_image(query: str) -> str:
    """네이버 이미지 검색 API (filter=large)"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return ""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    encoded = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/image?query={encoded}&display=1&sort=sim&filter=large"
    req = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    })
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
            items = data.get("items", [])
            if items:
                return items[0].get("link", "")
    except Exception as e:
        print(f"    이미지 검색 실패: {e}")
    return ""


# =====================================================================
# 다이소
# =====================================================================

DAISO_TARGET_GUGUNS = {
    "강남구": "강남", "서초구": "강남",
    "송파구": "잠실", "마포구": "홍대",
    "성동구": "성수", "중구": "명동",
}


def _daiso_fmt_time(raw: str) -> str:
    if not raw or len(raw) < 4:
        return ""
    return f"{raw[:2]}:{raw[2:]}"



async def _daiso_collect_stores(page, gugun):
    """Playwright로 특정 구의 다이소 매장 수집"""
    stores = await page.evaluate("""
        (gugun) => {
            return new Promise((resolve) => {
                const tabs = $('#tabSearchMethod a');
                if (tabs.length >= 2) tabs.eq(1).trigger('click');
                $('select[name="sido"]').val('서울').trigger('change');
                setTimeout(() => {
                    $('select[name="gugun"]').val(gugun);
                    $('[name="name_address"]').val('');
                    var param = $('[name="searchForm"]').serializeArray();
                    $.ajax({
                        url: "./ajax/shop_search", data: param,
                        success: function(result) {
                            var $result = $(result);
                            var storeEls = $result.find('[data-lat]');
                            if (storeEls.length === 0) storeEls = $(result).filter('[data-lat]');
                            var stores = [];
                            storeEls.each(function() {
                                var el = $(this);
                                var info = {};
                                try { info = JSON.parse(el.attr('data-info') || '{}'); } catch(e) {}
                                stores.push({
                                    name: el.find('.place').text().trim(),
                                    addr: el.find('.addr').text().trim(),
                                    tel: el.find('.phone').text().trim().replace('T.', '').trim(),
                                    lat: parseFloat(el.attr('data-lat') || 0),
                                    lng: parseFloat(el.attr('data-lng') || 0),
                                    start: el.attr('data-start') || '',
                                    end: el.attr('data-end') || '',
                                    parking: info['shp_pak'] === 'Y',
                                });
                            });
                            resolve(stores);
                        },
                        error: function() { resolve([]); }
                    });
                }, 2000);
            });
        }
    """, gugun)
    return stores


async def scrape_daiso():
    """다이소 매장 수집 → daiso_투어.json"""
    print("\n" + "=" * 50)
    print("▶ 다이소 매장 수집")
    print("=" * 50)

    area_counts = {a: 0 for a in set(DAISO_TARGET_GUGUNS.values())}
    collected = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent="Mozilla/5.0")
        page = await ctx.new_page()

        for gugun, area in DAISO_TARGET_GUGUNS.items():
            if area_counts[area] >= MAX_PER_AREA:
                continue
            print(f"\n  [{area}] {gugun} 검색...")
            await page.goto("https://www.daiso.co.kr/cs/shop", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            stores = await _daiso_collect_stores(page, gugun)
            print(f"    발견: {len(stores)}개")

            for s in stores:
                if area_counts[area] >= MAX_PER_AREA:
                    break
                if gugun not in s["addr"]:
                    continue
                area_counts[area] += 1
                s["area"] = area
                collected.append(s)
                print(f"    ✓ {s['name']}")

        await browser.close()

    # 이미지 검색
    print("\n  이미지 검색...")
    for s in collected:
        img = search_naver_image(f"다이소 {s['name']}")
        if not img:
            img = search_naver_image(f"다이소 {s['area']} 매장")
        s["image"] = img
        time.sleep(0.3)

    # JSON 구성
    results = []
    for idx, s in enumerate(collected, 1):
        title = f"다이소 {s['name']}"
        start = _daiso_fmt_time(s["start"])
        end = _daiso_fmt_time(s["end"])
        usetime = f"{start}~{end}" if start and end else ""
        tags = ["다이소", "생활용품", "쇼핑", s["area"], "가성비"]

        entry = {
            "contentid": f"DAISO_{idx:03d}",
            "title": title,
            "contenttypeid": "투어",
            "contenttypeid_code": 99,
            "image": s.get("image", ""),
            "usetime": usetime or None,
            "addr": s["addr"],
            "mapy": s["lat"],
            "mapx": s["lng"],
            "tel": s["tel"] or None,
            "category_depth": "쇼핑 > 생활용품",
            "website": "https://www.daiso.co.kr",
            "tags": tags,
        }
        # null/빈값 제거
        entry = {k: v for k, v in entry.items() if v is not None and v != ""}
        results.append(entry)

    out = DATA_DIR / "daiso_투어.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 다이소 완료: {len(results)}개 → {out}")
    return results


# =====================================================================
# 무신사
# =====================================================================

MUSINSA_AREAS = {
    "강남": ["강남", "압구정", "서초구"],
    "잠실": ["잠실", "롯데월드몰", "롯데백화점 잠실", "송파구"],
    "홍대": ["홍대", "마포구"],
    "성수": ["성수", "성동구"],
    "명동": ["명동", "중구"],
}


def _musinsa_classify(name, addr):
    for area, kws in MUSINSA_AREAS.items():
        for kw in kws:
            if kw in name or kw in addr:
                return area
    return None


async def _musinsa_extract(page):
    all_text = await page.inner_text("body")
    store_name = ""
    for h2 in await page.query_selector_all("h2"):
        t = (await h2.text_content() or "").strip()
        if 5 < len(t) < 60 and any(kw in t for kw in ["무신사", "킥스", "뷰티 스페이스"]):
            store_name = t
            break
    if not store_name:
        return None

    addr = ""
    for line in all_text.split("\n"):
        line = line.strip()
        if line.startswith("서울") and len(line) > 10:
            addr = line
            break
    if not addr:
        return None

    img_url = ""
    for img in await page.query_selector_all("img[alt]"):
        if "스토어 사진" in ((await img.get_attribute("alt")) or ""):
            img_url = (await img.get_attribute("src")) or ""
            break

    hours = ""
    ko = re.search(r"매일\s*[:：]?\s*(\d{1,2}:\d{2}\s*[~\-]\s*\d{1,2}:\d{2})", all_text)
    en = re.search(r"Every\s*day\s*[:：]?\s*(\d{1,2}:\d{2}\s*[~\-]\s*\d{1,2}:\d{2})", all_text)
    if ko:
        hours = f"매일 {ko.group(1)}"
    elif en:
        hours = f"매일 {en.group(1)}"

    tel = ""
    m = re.search(r"(\d{2,4}-\d{3,4}-\d{4})", all_text)
    if m:
        tel = m.group(1)

    return {"name": store_name, "addr": addr, "img": img_url, "hours": hours, "tel": tel}


def _musinsa_geocode(addr):
    clean = re.sub(r"\(.*?\)", "", addr)
    clean = re.sub(r"B?\d+F.*", "", clean).strip()
    for query in [clean, " ".join(clean.split()[:4]), " ".join(clean.split()[:3])]:
        encoded = urllib.parse.quote(query)
        api_url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"
        req = urllib.request.Request(api_url, headers={"User-Agent": "MusinsaCollector/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            pass
        time.sleep(1.1)
    return 0.0, 0.0


async def scrape_musinsa():
    """무신사 매장 수집 → musinsa_투어.json"""
    print("\n" + "=" * 50)
    print("▶ 무신사 매장 수집")
    print("=" * 50)

    area_counts = {a: 0 for a in MUSINSA_AREAS}
    store_map = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent="Mozilla/5.0")
        page = await ctx.new_page()

        print("  ID 1~100 스캔...")
        for sid in range(1, 101):
            if all(c >= MAX_PER_AREA for c in area_counts.values()):
                break
            try:
                await page.goto(f"https://www.musinsa.com/offline/{sid}", wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)
            except Exception:
                continue

            info = await _musinsa_extract(page)
            if not info:
                continue

            area = _musinsa_classify(info["name"], info["addr"])
            if area is None or area_counts[area] >= MAX_PER_AREA:
                continue

            area_counts[area] += 1
            info["area"] = area
            store_map[sid] = info
            print(f"  ✓ [{sid:>2}] [{area}] {info['name']}")

        await browser.close()

    # 좌표 변환
    print("\n  좌표 변환...")
    for sid, info in store_map.items():
        lat, lon = _musinsa_geocode(info["addr"])
        info["lat"], info["lon"] = lat, lon

    # JSON 구성
    results = []
    for sid, info in store_map.items():
        entry = {
            "contentid": f"MUSINSA_{sid:03d}",
            "title": " ".join(info["name"].split()),
            "contenttypeid": "투어",
            "contenttypeid_code": 99,
            "image": info["img"],
            "usetime": info["hours"] or None,
            "fee": "무료 입장",
            "addr": info["addr"],
            "mapy": info["lat"],
            "mapx": info["lon"],
            "tel": info["tel"] or None,
            "category_depth": "쇼핑 > 패션",
            "website": f"https://www.musinsa.com/offline/{sid}",
            "tags": ["무신사", "패션", "쇼핑", info["area"], "오프라인매장"],
        }
        entry = {k: v for k, v in entry.items() if v is not None and v != ""}
        results.append(entry)

    out = DATA_DIR / "musinsa_투어.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 무신사 완료: {len(results)}개 → {out}")
    return results


# =====================================================================
# 올리브영
# =====================================================================

OY_SEARCH_AREAS = {
    "종로": "JR", "홍대": "HD", "강남": "GN",
    "잠실": "JS", "성수": "SS", "명동": "MD",
}

OY_EXTRACT_JS = """
() => {
    const IMAGE_BASE = "https://image.oliveyoung.co.kr/cfimages/oystore/";
    const lis = document.querySelectorAll("li");
    const stores = [];
    lis.forEach((li) => {
        const nameEl = li.querySelector("strong");
        const addrEl = li.querySelector('[class*="addr"], [class*="Addr"], [class*="address"]');
        const timeEl = li.querySelector('[class*="time"], [class*="Time"], [class*="hour"]');
        const idEl = li.querySelector("[id]");
        if (!nameEl || !addrEl) return;
        const name = nameEl.innerText.trim();
        const addr = addrEl.innerText.trim();
        const time = timeEl?.innerText?.trim() || "";
        const code = idEl?.id && idEl.id.length <= 6 ? idEl.id : "";
        stores.push({
            name, addr, time, code,
            image: code ? IMAGE_BASE + code + "_1.jpg" : null,
        });
    });
    return stores;
}
"""


async def scrape_oliveyoung():
    """올리브영 매장 수집 → oliveyoung_투어.json"""
    print("\n" + "=" * 50)
    print("▶ 올리브영 매장 수집")
    print("=" * 50)

    all_stores = []  # (area_code, area_name, raw_store)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent="Mozilla/5.0")
        page = await ctx.new_page()

        for area_name, area_code in OY_SEARCH_AREAS.items():
            keyword = urllib.parse.quote(area_name)
            url = f"https://m.oliveyoung.co.kr/m/mtn/store/search/result/store?searchKeyword={keyword}&sort=01"
            print(f"\n  [{area_name}] 검색...")

            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"    접속 실패: {e}")
                continue

            stores = await page.evaluate(OY_EXTRACT_JS)
            # 서울 매장만 필터링
            stores = [s for s in stores if "서울" in s.get("addr", "")]
            print(f"    발견: {len(stores)}개 (서울)")

            for s in stores[:MAX_PER_AREA * 2]:  # 지역당 넉넉히 수집
                s["area_code"] = area_code
                s["area_name"] = area_name
                all_stores.append(s)
                print(f"    ✓ {s['name']}")

        await browser.close()

    # JSON 구성
    results = []
    area_counters = {code: 0 for code in OY_SEARCH_AREAS.values()}

    for s in all_stores:
        area_code = s["area_code"]
        area_name = s["area_name"]
        area_counters[area_code] += 1
        idx = area_counters[area_code]

        name = s["name"]
        title = name if any(kw in name for kw in ["올리브영", "올리브베러", "트렌드팟"]) else f"올리브영 {name}"

        time_str = s.get("time", "")
        if time_str.startswith("월 "):
            time_str = time_str[2:]

        entry = {
            "contentid": f"OY_{area_code}_{idx:03d}",
            "title": title,
            "contenttypeid": "투어",
            "image": s.get("image"),
            "usetime": time_str or None,
            "restdate": "연중무휴",
            "addr": s["addr"],
            "mapy": 0.0,
            "mapx": 0.0,
            "category_depth": "쇼핑 > 뷰티",
            "summary": f"{area_name} 지역에 위치한 올리브영 매장으로, K-뷰티 쇼핑을 즐길 수 있습니다.",
            "description": f"{title}은 {s['addr']}에 위치한 뷰티 전문 매장입니다. K-뷰티 인기 브랜드부터 스킨케어, 메이크업 등 다양한 뷰티 제품을 갖추고 있습니다.",
            "website": "https://www.oliveyoung.co.kr",
            "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", area_name],
        }
        entry = {k: v for k, v in entry.items() if v is not None and v != ""}
        results.append(entry)

    out = DATA_DIR / "oliveyoung_투어.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 올리브영 완료: {len(results)}개 → {out}")
    print("  ⚠️  좌표/llm_text는 preprocess_shopping.py로 보강하세요.")
    return results



# =====================================================================
# 메인
# =====================================================================

async def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["daiso", "musinsa", "oliveyoung"]

    for t in targets:
        t = t.lower()
        if t == "daiso":
            await scrape_daiso()
        elif t == "musinsa":
            await scrape_musinsa()
        elif t == "oliveyoung":
            await scrape_oliveyoung()
        else:
            print(f"  [SKIP] 알 수 없는 대상: {t}")


if __name__ == "__main__":
    asyncio.run(main())
