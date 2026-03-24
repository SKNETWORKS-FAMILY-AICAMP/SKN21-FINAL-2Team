"""Popply 팝업스토어 수집 (Selenium 크롤링)

popply.co.kr 목록에서 링크를 수집한 뒤,
각 상세 페이지의 JSON-LD + amenity 아이콘을 파싱하여 저장한다.
"""

import json
import logging
import re
import time
from datetime import date

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import RAW_DIR

log = logging.getLogger(__name__)

BASE_URL = "https://www.popply.co.kr"

AMENITY_MAP = [
    ("주차가능", "parking", "주차 가능"),
    ("주차불가", "parking", "주차 불가"),
    ("입장료 유료", "fee", "유료"),
    ("입장료 무료", "fee", "무료"),
    ("반려동물", "pet", "반려동물 동반 가능"),
    ("웰컴 키즈존", "kids", "웰컴 키즈존"),
    ("노키즈존", "kids", "노키즈존"),
    ("식음료 반입 금지", "food_ban", "식음료 반입 금지"),
    ("19세 이상", "adult_only", "19세 이상"),
    ("와이파이 가능", "wifi", "와이파이 가능"),
    ("사진촬영 가능", "photo", "사진촬영 가능"),
    ("사전예약", "reservation", "사전예약"),
]


def _create_driver(headless: bool = True) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    return driver


def _get_popup_links(driver, date_from: str, date_to: str) -> list[str]:
    """목록 페이지에서 /popup/{id} 링크 수집."""
    url = f"{BASE_URL}/popup?fromDate={date_from}&toDate={date_to}&address1=서울"
    log.info("  목록 페이지: %s", url)
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    # 모달 닫기
    try:
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.modal-close, button[class*='close'], .popup-close")
        )).click()
        time.sleep(1)
    except Exception:
        pass

    # 목록 대기
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".calendar-popup-list, .popuplist-board")
        ))
    except Exception:
        log.warning("  목록 로딩 타임아웃")

    # 무한 스크롤
    for _ in range(5):
        prev = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        if driver.execute_script("return document.body.scrollHeight") == prev:
            break

    # 링크 추출 (중복 제거, 순서 유지)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    seen = set()
    links = []
    for a in soup.find_all("a", href=re.compile(r"/popup/\d+")):
        href = a["href"]
        full = BASE_URL + href if href.startswith("/") else href
        if full not in seen:
            seen.add(full)
            links.append(full)

    log.info("  링크 %d건 발견", len(links))
    return links


def _parse_json_ld(soup) -> dict:
    """JSON-LD에서 Event/LocalBusiness 데이터 추출."""
    tag = soup.find("script", id="json-ld")
    if not tag:
        return {}

    try:
        data = json.loads(tag.string)
    except (json.JSONDecodeError, TypeError):
        return {}

    if isinstance(data, list):
        event = next((d for d in data if d.get("@type") == "Event"), {})
        biz = next((d for d in data if d.get("@type") == "LocalBusiness"), {})
        data = {**biz, **event}

    result = {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "startDate": data.get("startDate", ""),
        "endDate": data.get("endDate", ""),
        "images": data.get("image", []),
    }

    # 위치
    loc = data.get("location") or {}
    addr = loc.get("address", {}) if isinstance(loc, dict) else {}
    if isinstance(addr, dict):
        parts = [addr.get("addressRegion", ""), addr.get("addressLocality", ""), addr.get("streetAddress", "")]
        result["location"] = " ".join(p for p in parts if p)

    # 운영시간
    hours = data.get("openingHoursSpecification", [])
    if hours:
        result["hours"] = f"{hours[0].get('opens', '')} ~ {hours[0].get('closes', '')}"

    return result


def _parse_amenities(soup) -> dict:
    """amenity 아이콘 영역에서 편의시설 정보 추출."""
    container = soup.select_one(".popupdetail-icon-area")
    if not container:
        return {}

    result = {}
    for li in container.select("li"):
        if "false" in li.get("class", []):
            continue
        text = li.get_text(strip=True)
        for keyword, field, value in AMENITY_MAP:
            if keyword in text:
                result[field] = value
                break
    return result


def _parse_detail(driver, url: str) -> dict | None:
    """상세 페이지 파싱. JSON-LD + amenity를 합쳐 반환."""
    try:
        driver.get(url)
        time.sleep(3)
    except Exception as e:
        log.warning("  %s 접속 실패: %s", url, e)
        return None

    soup = BeautifulSoup(driver.page_source, "html.parser")

    result = {"_source": "popply", "url": url}
    result.update(_parse_json_ld(soup))
    result.update(_parse_amenities(soup))

    # 운영시간 fallback
    if "hours" not in result:
        section = soup.select_one(".popupdetail-time")
        if section:
            result["hours"] = section.get_text(strip=True).replace("운영 시간", "").strip()

    return result


def _load_existing_urls(path) -> set[str]:
    urls: set[str] = set()
    if not path.exists():
        return urls
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                urls.add(json.loads(line).get("url", ""))
            except (json.JSONDecodeError, KeyError):
                pass
    return urls


def collect(headless: bool = True):
    """Popply 팝업스토어 수집."""
    output_path = RAW_DIR / "popply.jsonl"
    existing_urls = _load_existing_urls(output_path)

    driver = _create_driver(headless)
    try:
        today = date.today().strftime("%Y-%m-%d")
        links = _get_popup_links(driver, today, "2026-12-31")
        new_links = [l for l in links if l not in existing_urls]
        log.info("[popply] 전체 %d건, 신규 %d건", len(links), len(new_links))

        collected = 0
        for i, link in enumerate(new_links):
            log.info("  [%d/%d] %s", i + 1, len(new_links), link)
            detail = _parse_detail(driver, link)
            if not detail:
                continue

            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(detail, ensure_ascii=False) + "\n")
            collected += 1

        log.info("[popply] 완료: 신규 %d건 (전체 %d건)", collected, len(existing_urls) + collected)
    finally:
        driver.quit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    collect()
