
import time
import json
import re
import pandas as pd
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

class PopplyCrawler:
    def __init__(self, headless: bool = False):
        self.base_url = "https://www.popply.co.kr"
        self.driver = self._init_driver(headless)


    def _init_driver(self, headless: bool = True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Initializing driver
        # Removed ChromeDriverManager().install() to avoid hangs on network prompts 
        # Assumes chromedriver is in PATH (like the user's existing crawler)
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        return driver

    def get_popup_links(self, date_from: str, date_to: str, location_filter: str = "서울") -> List[str]:
        url = f"{self.base_url}/popup?fromDate={date_from}&toDate={date_to}&address1={location_filter}"
        print(f"📍 Accessing List Page: {url}")
        self.driver.get(url)

        wait = WebDriverWait(self.driver, 20)

        # 진입 시 나타나는 모달(페르소나 테스트 등) 닫기
        try:
            close_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.modal-close, button[class*='close'], .popup-close")
            ))
            close_btn.click()
            time.sleep(1)
            print("   모달 닫기 완료")
        except Exception:
            pass  # 모달이 없으면 그냥 진행

        # 팝업 목록 컨테이너 대기 (실제 클래스: calendar-popup-list)
        try:
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".calendar-popup-list, .popuplist-board")
            ))
        except Exception as e:
            print(f"⚠️ List loading timeout or error: {e}")

        # 무한 스크롤 처리
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 링크 추출
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = str(a['href'])
            if re.search(r'/popup/\d+', href) and href not in links:
                full_link = self.base_url + href if href.startswith('/') else href
                links.append(full_link)

        # 중복 제거
        links = list(dict.fromkeys(links))  # 순서 유지하며 중복 제거
        print(f"✅ Found {len(links)} popup links.")
        return links

    def parse_detail_page(self, url: str) -> Dict:
        print(f"📄 Crawling: {url}")
        try:
            self.driver.get(url)
            time.sleep(3) # Wait for hydration
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            result = {
                'url': url,
                'name': '',
                'schedule': '',
                'location': '',
                'hours': '',
                'introduction': '',
                'thumbnail': '',
                'parking': 'Unknown',
                'fee': 'Unknown', 
                'pet': 'Unknown',
                'kids': 'Unknown',
                'food_ban': 'Unknown',
                'adult_only': 'Unknown',
                'wifi': 'Unknown',
                'photo': 'Unknown'
            }

            # 1. Extract from JSON-LD (Most reliable)
            json_ld_script = soup.find('script', id='json-ld')
            if json_ld_script:
                try:
                    data = json.loads(json_ld_script.string)
                    # Data might be a list of objects (Event, LocalBusiness)
                    if isinstance(data, list):
                        event_data = next((item for item in data if item.get('@type') == 'Event'), {})
                        biz_data = next((item for item in data if item.get('@type') == 'LocalBusiness'), {})
                        data = {**biz_data, **event_data} # Merge

                    result['name'] = data.get('name', '')
                    result['introduction'] = data.get('description', '')
                    
                    # Schedule
                    start_date = data.get('startDate', '')
                    end_date = data.get('endDate', '')
                    result['schedule'] = f"{start_date} ~ {end_date}"
                    
                    # Location
                    location = data.get('location', {}) or data.get('address', {})
                    if isinstance(location, dict):
                         address = location.get('address', {})
                         if isinstance(address, dict):
                             result['location'] = f"{address.get('addressRegion', '')} {address.get('addressLocality', '')} {address.get('streetAddress', '')}"
                         else:
                             result['location'] = data.get('address', {}).get('streetAddress', '') # Fallback

                    # Hours (Formatting from OpeningHoursSpecification)
                    hours_spec = data.get('openingHoursSpecification', [])
                    if hours_spec:
                        # Just take the first one as representative or join unique ones
                        opens = hours_spec[0].get('opens', '')
                        closes = hours_spec[0].get('closes', '')
                        result['hours'] = f"{opens} ~ {closes}"
                        
                    # Image
                    images = data.get('image', [])
                    if images:
                        result['thumbnail'] = images[0]

                except json.JSONDecodeError:
                    print("⚠️ Failed to decode JSON-LD")

            # 2. Extract Amenities / Icons (Using User-Identified Selectors)
            # User provided structure: <div class="popupdetail-icon-area"><ul>...</ul></div>
            # Items with class="false" are inactive.
            
            amenity_container = soup.select_one('.popupdetail-icon-area')
            if amenity_container:
                # print("   Found amenity container, parsing icons...") # Optional debug
                items = amenity_container.select('li')
                for item in items:
                    # Check class for 'false'
                    classes = item.get('class', [])
                    if 'false' in classes:
                        continue
                        
                    text = item.get_text(strip=True)
                    
                    # Precise Mappings based on user provided HTML
                    # Storing full descriptive strings as requested
                    if '주차가능' in text: 
                        result['parking'] = '주차 가능'
                    elif '주차불가' in text: 
                        result['parking'] = '주차 불가'
                    elif '입장료 유료' in text: 
                        result['fee'] = '유료'
                    elif '입장료 무료' in text: 
                        result['fee'] = '무료'
                    elif '반려동물' in text: 
                        result['pet'] = '반려동물 동반 가능'
                    elif '웰컴 키즈존' in text: 
                        result['kids'] = '웰컴 키즈존'
                    elif '노키즈존' in text: 
                        result['kids'] = '노키즈존'
                    elif '식음료 반입 금지' in text: 
                        result['food_ban'] = '식음료 반입 금지'
                    elif '19세 이상' in text: 
                        result['adult_only'] = '19세 이상'
                    elif '와이파이 가능' in text: 
                        result['wifi'] = '와이파이 가능'
                    elif '사진촬영 가능' in text: 
                        result['photo'] = '사진촬영 가능'
                        
            else:
                # Fallback to text search if container not found
                print("   Amenity container not found, falling back to text search...")
                page_text = soup.get_text()
                
                def check_keyword(keywords, text):
                    return any(k in text for k in keywords)

                if check_keyword(['주차 가능', '주차가능'], page_text): result['parking'] = '가능'
                elif check_keyword(['주차 불가', '주차불가'], page_text): result['parking'] = '불가'
                
                if check_keyword(['웰컴 키즈존', '키즈존', '예스키즈'], page_text): result['kids'] = '키즈존'
                elif check_keyword(['노키즈존'], page_text): result['kids'] = '노키즈존'
                
                if check_keyword(['반려동물'], page_text): result['pet'] = '가능'
                
                if check_keyword(['입장료 무료'], page_text): result['fee'] = '무료'
                elif check_keyword(['입장료 유료'], page_text): result['fee'] = '유료'
            
            # 3. Fallback for Hours (HTML scraping if JSON-LD failed)
            # User provided structure: <div class="popupdetail-time"><header><h3 class="info-tit">운영 시간</h3>...
            if not result['hours']:
                time_section = soup.select_one('.popupdetail-time')
                if time_section:
                    # Extract text, removing the "운영 시간" header title to be clean
                    full_text = time_section.get_text(strip=True)
                    # Simple cleanup: remove the header text if it exists
                    result['hours'] = full_text.replace("운영 시간", "").strip()
                    
            return result
            
        except Exception as e:
            print(f"❌ Error parsing {url}: {e}")
            return None

    def close(self):
        self.driver.quit()

def main():
    import os
    from datetime import date

    crawler = PopplyCrawler(headless=False)
    try:
        # 1. Get Links
        # 오늘 날짜 기준 진행 중/예정 팝업
        today = date.today().strftime("%Y-%m-%d")
        end_date = "2026-12-31"
        links = crawler.get_popup_links(today, end_date)

        # 2. Parse Each
        results = []
        for i, link in enumerate(links):
            print(f"[{i+1}/{len(links)}] processing...")
            data = crawler.parse_detail_page(link)
            if data:
                results.append(data)

        # 3. Save
        if results:
            # 기존 데이터 파일 덮어쓰기
            output_path = os.path.join(
                os.path.dirname(__file__),
                "../../data/99_팝업스토어.json"
            )
            output_path = os.path.abspath(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"💾 {len(results)}개 항목을 {output_path} 에 저장했습니다.")

    finally:
        crawler.close()

if __name__ == "__main__":
    main()
