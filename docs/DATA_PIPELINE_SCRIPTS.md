# 데이터 파이프라인 스크립트 상세 분석

데이터 수집부터 Qdrant 업로드까지의 전체 파이프라인 스크립트를 분석한 문서입니다.

> 경로 기준: `backend/app/scripts/`
> scheduler 폴더는 별도 문서에서 다룹니다.

---

## 파이프라인 흐름

```
collect/     →     preprocess/     →     enrich/     →     qdrant_upsert.py
(수집)             (전처리)               (LLM 보강)        (벡터 DB 업로드)

data/raw/    →     data/preprocessed/  →  data/enrich/  →  Qdrant
*.jsonl            *.json                *_enrich.json     places / photos
```

---

## 1. 수집 스크립트 (`collect/`)

### 1-1. `collect/config.py` (공통 설정)

수집 스크립트들이 공유하는 설정값과 API 키를 정의합니다.

**API 키** (`.env`에서 로드)

| 환경변수 | 용도 |
|---------|------|
| `TOURAPI_KEY` | 한국관광공사 TourAPI |
| `VISITSEOUL_API_KEY` | VisitSeoul API |
| `KAKAO_REST_API_KEY` | 카카오 지오코딩 |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 네이버 지도/검색 |
| `SEOUL_OPENDATA_KEY` | 서울 열린데이터광장 |

**공통 상수**

| 상수 | 값 | 설명 |
|------|---|------|
| `DATA_DIR` | `backend/data` | 데이터 루트 |
| `RAW_DIR` | `backend/data/raw` | 수집 원본 저장 |
| `REQUEST_TIMEOUT` | 15초 | HTTP 요청 타임아웃 |
| `REQUEST_DELAY` | 0.3초 | API 요청 간 대기 |
| `MAX_RETRIES` | 3 | 재시도 횟수 |

**API 엔드포인트**

| 상수 | 값 |
|------|---|
| `TOURAPI_BASE` | `https://apis.data.go.kr/B551011/KorService2` |
| `VISITSEOUL_BASE` | `https://api-call.visitseoul.net` |
| `SEOUL_CULTURE_BASE` | `http://openAPI.seoul.go.kr:8088` |

**TourAPI 콘텐츠 타입**

| ID | 카테고리 |
|----|---------|
| 12 | 관광지 |
| 14 | 문화시설 |
| 28 | 레포츠 |
| 32 | 숙박 |
| 39 | 음식점 |

---

### 1-2. `collect/tourapi.py` (한국관광공사 API)

TourAPI에서 서울 지역 장소 데이터를 수집합니다.

**수집 흐름**

```
1. areaBasedList2 (areaCode=1, 서울)  →  contentId 목록 수집 (페이징)
2. detailCommon2 (contentId)          →  기본 정보 (title, addr, mapx/y, image, overview)
3. detailIntro2 (contentId, contentTypeId) →  상세 정보 (usetime, restdate, parking 등)
4. common + intro 합쳐서 raw/tourapi_{카테고리}.jsonl 저장
```

**주요 함수**

| 함수 | 설명 |
|------|------|
| `_get(endpoint, params)` | API 호출 + 재시도 |
| `_parse_items(body)` | response.body.items.item 추출 |
| `_fetch_list(content_type_id, page, size)` | 목록 조회 (areaBasedList2) |
| `_fetch_detail(content_id, content_type_id)` | 상세 조회 (detailCommon2 + detailIntro2 합침) |
| `collect(content_type_id)` | 메인 수집. 카테고리별 또는 전체 |

**출력**: `data/raw/tourapi_관광지.jsonl`, `tourapi_문화시설.jsonl`, `tourapi_레포츠.jsonl`, `tourapi_숙박.jsonl`, `tourapi_음식점.jsonl`

**참고**: `detailCommon2`의 YN 옵션 파라미터(`defaultYN`, `addrinfoYN` 등)는 TourAPI 업데이트로 폐기됨. `contentId`만 넣으면 전체 필드 반환.

---

### 1-3. `collect/visitseoul.py` (VisitSeoul API)

VisitSeoul API에서 서울 관광 콘텐츠를 수집합니다.

**수집 흐름**

```
1. /api/v1/contents/list (POST, 페이징)  →  CID 목록 수집
2. /api/v1/contents/info (POST, cid)     →  상세 정보
3. raw/visitseoul.jsonl 저장 (전체 카테고리 하나의 파일)
```

**주요 함수**

| 함수 | 설명 |
|------|------|
| `_post(path, body)` | POST 요청 + 재시도 |
| `_get(path)` | GET 요청 + 재시도 |
| `_fetch_all_cids()` | 전체 CID 수집 (페이징) |
| `_fetch_info(cid)` | 단건 상세 조회 |
| `collect()` | 메인 수집 |

**제외 카테고리**: `축제/공연/행사` (`EXCLUDE_CATE`)

**출력**: `data/raw/visitseoul.jsonl`

---

### 1-4. `collect/popply.py` (Popply 팝업스토어 크롤링)

Selenium으로 Popply 웹사이트를 크롤링하여 서울 지역 팝업스토어 데이터를 수집합니다.

**수집 흐름**

```
1. 목록 페이지 접속 (?fromDate=...&toDate=...&address1=서울)
2. 무한 스크롤로 전체 링크 수집 (/popup/{id})
3. exclude_ids에 있는 contentid는 스킵 (스케줄러 중복 방지)
4. 상세 페이지에서 JSON-LD + amenity 아이콘 파싱
5. raw/popply.jsonl 저장
```

**주요 함수**

| 함수 | 설명 |
|------|------|
| `_create_driver(headless)` | Chrome WebDriver 생성 |
| `_get_popup_links(driver, date_from, date_to)` | 목록에서 링크 수집 |
| `_parse_json_ld(soup)` | JSON-LD에서 Event/LocalBusiness 파싱 |
| `_parse_amenities(soup)` | amenity 아이콘 영역에서 편의시설 파싱 |
| `_parse_detail(driver, url)` | 상세 페이지 파싱 (JSON-LD + amenity 합침) |
| `_extract_id_from_url(url)` | URL에서 contentid 추출 (`/popup/4640` → `4640`) |
| `get_links(headless)` | 목록만 크롤링 (상세 페이지 안 열음) |
| `collect(headless, exclude_ids)` | 메인 수집. exclude_ids로 기존 데이터 스킵 가능 |

**amenity 매핑**

| 키워드 | 필드 | 값 |
|--------|------|---|
| 주차가능 | parking | 주차 가능 |
| 입장료 무료 | fee | 무료 |
| 반려동물 | pet | 반려동물 동반 가능 |
| 웰컴 키즈존 | kids | 웰컴 키즈존 |
| 와이파이 가능 | wifi | 와이파이 가능 |
| 사진촬영 가능 | photo | 사진촬영 가능 |
| 사전예약 | reservation | 사전예약 |

**출력**: `data/raw/popply.jsonl`

---

### 1-5. `collect/seoul_culture.py` (서울 열린데이터광장)

서울시 문화행사 정보 API(OA-15486)를 호출하여 문화행사 데이터를 수집합니다.

**수집 흐름**

```
1. culturalEventInfo API 페이징 호출 (1000건씩)
2. EXCLUDE_CODES 카테고리 제외 (교육/체험, 독주/독창회)
3. END_DATE가 오늘 이전이면 스킵
4. raw/seoul_culture.jsonl 저장
```

**주요 함수**

| 함수 | 설명 |
|------|------|
| `_fetch_page(start, end)` | 범위 조회 + 재시도 |
| `_load_existing_ids(path)` | 기존 수집된 cultcode 로드 (중복 방지) |
| `collect()` | 메인 수집 |

**제외 카테고리**: `교육/체험`, `독주/독창회`

**출력**: `data/raw/seoul_culture.jsonl`

---

### 1-6. `collect/shopping.py` (다이소/무신사/올리브영)

Playwright를 사용하여 다이소, 무신사, 올리브영 매장 정보를 수집합니다.

**수집 대상**

| 브랜드 | 수집 방식 | 출력 |
|--------|----------|------|
| 다이소 | 다이소 매장 검색 API 크롤링 | `data/daiso_투어.json` |
| 무신사 | 무신사 스토어 페이지 크롤링 | `data/musinsa_투어.json` |
| 올리브영 | 올리브영 CDN 이미지 + 매장 정보 | `data/oliveyoung_투어.json` |

**주요 함수**

| 함수 | 설명 |
|------|------|
| `scrape_daiso()` | 다이소 매장 수집 (async) |
| `scrape_musinsa()` | 무신사 매장 수집 (async) |
| `scrape_oliveyoung()` | 올리브영 매장 수집 (async) |
| `search_naver_image(query)` | 네이버 이미지 검색 (이미지 없는 매장용) |

---

## 2. 전처리 스크립트 (`preprocess/`)

### 2-1. `preprocess/config.py` (공통 유틸)

전처리 스크립트들이 공유하는 유틸 함수와 설정을 정의합니다.

**경로 설정**

| 상수 | 경로 |
|------|------|
| `DATA_DIR` | `backend/data` |
| `RAW_DIR` | `data/raw` |
| `PREPROCESSED_DIR` | `data/preprocessed` |

**텍스트 정리 함수**

| 함수 | 설명 |
|------|------|
| `strip_html(text)` | HTML 태그, CSS 블록, HTML 엔티티 제거 |
| `first_sentence(text)` | 첫 문장 추출 (마침표/느낌표/물음표 기준) |
| `clean_title(title)` | `[]` 괄호 + 내용 제거 |
| `clean_value(val)` | 빈값(`""`, `None`, `"없음"`, `"-"`) → `None` 반환 |

**지오코딩 함수**

| 함수 | 설명 |
|------|------|
| `_safe_float(value)` | 안전한 float 변환 |
| `build_addr_tokens(addr)` | 주소 문자열 → 토큰 리스트 (검색용). 접미사 분리 (`용산구` → `용산구`, `용산`) |
| `enrich_geo(item)` | `mapy`/`mapx` → `geo` 변환 + `addr_tokens` 생성 + `mapy`/`mapx` 제거. 좌표 없으면 네이버 지오코딩 API 호출 |

**`build_addr_tokens` 상세**

```
입력: "서울특별시 용산구 한남대로20길 21-18 (한남동)"
출력: ["서울특별시", "서울특별", "용산구", "용산", "한남대로20길", "한남동", "21-18"]
```
- 괄호 내용 분리, 접미사(`시`/`구`/`동`/`로`/`길`) 제거한 stem 추가
- 최대 24개 토큰
- 불용어(`대한민국`, `한국`) 제거

**`enrich_geo` 상세**

```
입력: {"mapy": "37.58", "mapx": "126.98", "addr": "서울 용산구 ..."}
출력: {"geo": {"lat": 37.58, "lon": 126.98}, "addr_tokens": [...]}
       (mapy, mapx 필드 제거됨)
```
- 좌표가 없고 주소만 있으면 네이버 Geocoder API로 좌표 생성
- 주소도 좌표도 없으면 `geo` 필드 생성 안 함

**카테고리 매핑**

```python
TOURAPI_TYPE_MAP = {12: "관광지", 14: "문화시설", 28: "레포츠", 32: "숙박", 39: "음식점"}
VISITSEOUL_TYPE_MAP = {"문화관광": "관광지", "역사관광": "관광지", "자연관광": "관광지",
                       "체험관광": "관광지", "쇼핑": "투어", "숙박": "숙박", "음식": "음식점"}
```

---

### 2-2. `preprocess/tourapi.py` (TourAPI 전처리)

TourAPI raw 데이터를 통일 스키마로 변환합니다.

**처리 흐름**

```
1. raw/tourapi_{카테고리}.jsonl 읽기
2. 카테고리별 필드명 매핑 (usetimeculture → usetime 등)
3. category_depth 코드 → 한국어 변환 (categoryCode2 API 호출)
4. HTML 태그 제거, 빈값 정리
5. enrich_geo() 적용 (geo + addr_tokens 생성)
6. preprocessed/tourapi_{카테고리}.json 저장
```

**카테고리별 필드 매핑 (`_FIELD_MAP`)**

같은 의미의 필드가 카테고리마다 이름이 다름:

| 통일 필드 | 관광지(12) | 문화시설(14) | 숙박(32) | 음식점(39) |
|----------|-----------|-------------|---------|-----------|
| tel | infocenter | infocenterculture | infocenterlodging | infocenterfood |
| usetime | usetime | usetimeculture | checkintime | opentimefood |
| restdate | restdate | restdateculture | - | restdatefood |
| parking | parking | parkingculture | parkinglodging | parkingfood |
| fee | - | usefee | - | - |

**카테고리별 고유 필드 (`_EXTRA_KEYS`)**

- 숙박: `checkintime`, `checkouttime`, `roomcount`, `foodplace`, `reservationlodging` 등
- 음식점: `firstmenu`, `treatmenu`, `packing`, `kidsfacility`, `chkcreditcardfood` 등

**category_depth 변환**

```
코드: A02 > A0201 > A02010900
변환: 인문(문화/예술/역사) > 역사관광지 > 종교성지
```

TourAPI `categoryCode2` API를 호출하여 184개 코드 매핑을 로드합니다.

**출력**: `data/preprocessed/tourapi_관광지.json`, `tourapi_문화시설.json`, `tourapi_레포츠.json`, `tourapi_숙박.json`, `tourapi_음식점.json`

---

### 2-3. `preprocess/visitseoul.py` (VisitSeoul 전처리)

VisitSeoul raw 데이터를 `cate_depth` 기준으로 카테고리 분류 후 통일 스키마로 변환합니다.

**처리 흐름**

```
1. raw/visitseoul.jsonl 읽기 (전체 카테고리 혼합)
2. cate_depth 최상위 카테고리로 contenttypeid 매핑
3. 축제/공연/행사 제외
4. 필드명 매핑 (post_sj → title, traffic.* → addr/mapx/mapy 등)
5. fee "N"/"F" → 제거
6. restaurant 필드 평탄화 + menu 가격 제거
7. enrich_geo() 적용
8. 카테고리별 파일로 분리 저장
```

**필드 매핑**

| 통일 필드 | VisitSeoul 원본 |
|----------|----------------|
| contentid | cid |
| title | post_sj |
| image | main_img |
| addr | traffic.new_adres / traffic.adres |
| mapy/mapx | traffic.map_position_y/x |
| tel | extra.cmmn_telno |
| usetime | extra.cmmn_use_time |
| description | post_desc |
| summary | sumry |
| tags | tag |
| subway_info | traffic.subway_info |

**출력**: `data/preprocessed/visitseoul_관광지.json`, `visitseoul_숙박.json`, `visitseoul_음식점.json`, `visitseoul_투어.json`

---

### 2-4. `preprocess/popply.py` (Popply 전처리)

Popply raw 데이터를 전처리합니다.

**처리 흐름**

```
1. raw/popply.jsonl 읽기
2. URL에서 contentid 추출 (/popup/4640 → "4640")
3. 서울 외 지역 필터링 (location에 "서울" 포함 여부)
4. endDate가 오늘 이전이면 제거
5. 이모지 제거 (📍→"장소:", ⏰→"시간:" 등 한국어 치환 후 나머지 제거)
6. HTML 태그 제거
7. 날짜 포맷 정리 (2026-03-18T00:00:00 → 2026-03-18)
8. enrich_geo() 적용 (좌표 없으면 주소 기반 지오코딩)
9. preprocessed/popply_팝업스토어.json 저장
```

**이모지 치환 맵 (`_LABEL_EMOJI_MAP`)**

```python
{"📍": "장소:", "📅": "일정:", "⏰": "시간:", "🎁": "이벤트:", ...}
```

**출력**: `data/preprocessed/popply_팝업스토어.json`

---

### 2-5. `preprocess/seoul_culture.py` (열린데이터광장 전처리)

서울시 문화행사 raw 데이터를 전처리합니다.

**처리 흐름**

```
1. raw/seoul_culture.jsonl 읽기
2. HMPG_ADDR에서 contentid(cultcode) 추출
3. 필드 매핑 (TITLE→title, LOT→mapx, LAT→mapy, PLACE→place 등)
4. 날짜 포맷 정리 (2026-08-13 00:00:00.0 → 2026-08-13)
5. title 괄호 제거
6. 불필요 필드 제거 (ORG_NAME, THEMECODE, TICKET, GUNAME)
7. 좌표 기반 역지오코딩으로 addr 생성
8. enrich_geo() 적용
9. preprocessed/seoul_culture_문화행사.json 저장
```

**필드 매핑**

| 통일 필드 | 원본 필드 |
|----------|----------|
| contentid | HMPG_ADDR에서 cultcode 추출 |
| title | TITLE |
| image | MAIN_IMG |
| mapx | LOT |
| mapy | LAT |
| tel | INQUIRY |
| usetime | PRO_TIME |
| fee | USE_FEE |
| website | ORG_LINK 또는 HMPG_ADDR |
| category_depth | CODENAME |
| place | PLACE |
| STRTDATE | STRTDATE (날짜만) |
| END_DATE | END_DATE (날짜만) |
| RGSTDATE | RGSTDATE |
| IS_FREE | IS_FREE |

**출력**: `data/preprocessed/seoul_culture_문화행사.json`

---

### 2-6. `preprocess/shopping.py` (쇼핑 매장 전처리)

다이소/무신사/올리브영 수집 데이터를 전처리합니다.

**처리 흐름**

```
1. data/{brand}_투어.json 읽기
2. 무신사: 하드코딩 좌표 보정 + 이미지 보완 + llm_text 생성
3. 올리브영: 매장별 소개글 생성 (특수 매장은 전용 소개글, 일반 매장은 자동 생성)
4. 다이소: null 정리만 수행 (llm_text는 수집 시 이미 포함)
5. 동일 파일에 덮어쓰기 저장
```

**특징**: 이 스크립트는 수집 데이터에 직접 llm_text를 생성하여 저장합니다. 다른 소스들이 `enrich/` 스크립트로 별도 생성하는 것과 다릅니다.

**출력**: `data/daiso_투어.json`, `data/musinsa_투어.json`, `data/oliveyoung_투어.json` (입력과 동일 파일)

---

### 2-7. `preprocess/merge.py` (카테고리 병합)

여러 소스의 전처리 결과를 최종 카테고리별로 병합합니다.

**병합 규칙 (`MERGE_MAP`)**

| 최종 카테고리 | 소스 |
|-------------|------|
| 관광지 | tourapi_관광지 + tourapi_문화시설 + tourapi_레포츠 + visitseoul_관광지 |
| 숙박 | tourapi_숙박 + visitseoul_숙박 |
| 음식점 | tourapi_음식점 + visitseoul_음식점 |
| 콘텐츠 | seoul_culture_문화행사 |
| 팝업스토어 | popply_팝업스토어 |
| 투어 | visitseoul_투어 + visitseoul_쇼핑 |

**특수 처리**: 관광지에 포함된 "물품보관소" 장소는 투어 카테고리로 이동

**출력**: `data/preprocessed/관광지.json`, `숙박.json`, `음식점.json`, `콘텐츠.json`, `투어.json`

---

## 3. LLM 보강 스크립트 (`enrich/`)

### 3-1. `enrich/generate_llm_text.py` (TourAPI/VisitSeoul용)

전처리된 데이터에 OpenAI GPT-4o-mini로 소개글(llm_text)과 태그(tags)를 생성합니다.

**대상 파일** (`TARGETS`)

```
tourapi_관광지, tourapi_문화시설, tourapi_레포츠, tourapi_숙박, tourapi_음식점
visitseoul_관광지, visitseoul_숙박, visitseoul_음식점, visitseoul_투어
```

**처리 흐름**

```
1. preprocessed/{name}.json 읽기
2. 장소 정보로 프롬프트 구성 (title, addr, category_depth, description 등)
3. GPT-4o-mini로 300~500자 소개글 생성 (max_tokens=600)
4. 구조화 텍스트(장소명, 주소, 키워드) + 소개글 = llm_text
5. llm_text에서 키워드 추출 → tags
6. 이모지 제거
7. enrich/{name}_enrich.json 저장
```

**llm_text 구조**

```
- 장소명: 남산서울타워
- 주소: 서울 용산구 남산공원길 105
- 카테고리: 문화관광 > 랜드마크관광
- 주요 키워드: 케이블카, 남산, 전망대, 야경
- 소개: 도심 속 로맨틱 아일랜드로 입지를 굳힌 남산서울타워는...
```

**설정**

| 상수 | 값 |
|------|---|
| `MODEL` | gpt-4o-mini |
| `CONCURRENCY` | 10 (비동기 동시 요청) |
| `max_tokens` | 600 |

**프롬프트 지시사항**
- 300~500자 한국어
- 장소의 특징, 분위기, 경험할 수 있는 것 중심
- 이모지 사용 금지
- 600자 이내에서 완결된 문장으로 끝낼 것

**입력**: `data/preprocessed/{name}.json`
**출력**: `data/enrich/{name}_enrich.json`

---

### 3-2. `enrich/generate_content_llm_text.py` (팝플리/열린데이터광장용)

콘텐츠(팝업스토어, 문화행사) 데이터에 네이버 검색 컨텍스트 + GPT-4o-mini로 llm_text, tags, place를 생성합니다.

**대상 파일** (`TARGETS`)

```
seoul_culture_문화행사, popply_팝업스토어
```

**처리 흐름 (문화행사)**

```
1. 네이버 블로그 검색 (title + place 조합)
2. 검색 결과 중 관련도 높은 블로그 크롤링 → 컨텍스트 수집
3. GPT-4o-mini로 소개글 생성 (컨텍스트 참고)
4. GPT-4o-mini로 place 추출 (원본 PLACE에서 네이버 지도 검색 가능한 장소명)
5. GPT-4o-mini로 tags 추출
6. 이모지 제거
```

**처리 흐름 (팝업스토어)**

```
1. 네이버 웹문서 검색 (브랜드명 + "팝업" 등)
2. 검색 결과 크롤링 → 컨텍스트 수집
3. GPT-4o-mini로 소개글 생성
4. GPT-4o-mini로 place 추출 (description에서 장소명 추출)
5. GPT-4o-mini로 tags 추출
6. 이모지 제거
```

**네이버 검색 관련 함수**

| 함수 | 설명 |
|------|------|
| `_search_naver(query, search_type, display)` | 네이버 검색 API 호출 (blog/webkr) |
| `_to_mobile_blog_url(link)` | 블로그 URL → 모바일 URL 변환 (크롤링 용이) |
| `_crawl_page(url, is_blog, max_chars)` | 웹 페이지 크롤링 (BeautifulSoup) |
| `_score_result(result, title_tokens, addr_tokens)` | 검색 결과 관련도 점수 계산 |

**place 추출**

원본 place 값이 네이버 지도에서 검색 안 되는 경우가 많아서 (예: `코엑스전시장 B홀` → `코엑스`), LLM이 description과 place를 보고 검색 가능한 장소명을 추출합니다.

**설정**

| 상수 | 값 |
|------|---|
| `OPENAI_MODEL` | gpt-4o-mini |
| `max_tokens` | 600 |

**입력**: `data/preprocessed/{name}.json`
**출력**: `data/enrich/{name}_enrich.json`

---

## 4. Qdrant 업로드 스크립트

### 4-1. `qdrant_upsert.py`

enrich 완료된 JSON 파일을 읽어서 Qdrant 벡터 DB에 업로드합니다.

**사용법**

```bash
# 컬렉션 재생성 + 전체 업로드
python -m app.scripts.qdrant_upsert

# 컬렉션 유지 + 특정 파일만 추가
python -m app.scripts.qdrant_upsert --append data/enrich/popply_팝업스토어_enrich.json

# 업로드 + 스냅샷 생성
python -m app.scripts.qdrant_upsert --snapshot
```

**컬렉션 구조**

**places** (텍스트 검색용)

| 항목 | 설명 |
|------|------|
| 메인 벡터 | BGE-M3 텍스트 임베딩 (1024차원, 코사인) |
| sparse 벡터 | `text_sparse` — 키워드 매칭용 |
| payload | llm_text 제외한 모든 필드 |
| 인덱스 | `contenttypeid` (KEYWORD), `geo` (GEO), `addr_tokens` (KEYWORD) |

**photos** (이미지 검색용)

| 항목 | 설명 |
|------|------|
| 메인 벡터 | CLIP 이미지 임베딩 (768차원, 코사인) |
| payload | places와 동일 |
| 인덱스 | `contenttypeid`, `contentid`, `geo`, `addr_tokens` |

**건별 업로드 흐름 (`_upsert_one`)**

```
1. payload 준비 (llm_text 제외)
2. point_id 생성:
   - contentid가 숫자 → int 변환 ("2733967" → 2733967)
   - 문자열 → hash ("KOP000036" → abs(hash()) % 2^63)
3. places 컬렉션:
   - llm_text → BGE-M3 임베딩 → 메인 벡터
   - title + contenttypeid + addr + addr_tokens → sparse 벡터
   - payload + 벡터 → upsert
4. photos 컬렉션:
   - image URL에서 이미지 다운로드
   - 이미지 → CLIP 임베딩 → 벡터
   - payload + 벡터 → upsert (UUID로 ID 생성)
```

**sparse 벡터 상세**

`_build_sparse_text`: title, contenttypeid, addr, addr_tokens를 하나의 문자열로 합침

`_build_sparse_vector`: 텍스트를 토큰화 → 각 토큰의 MD5 해시 앞 8자리를 정수 인덱스로, 빈도를 값으로 저장. 의미 검색(BGE-M3)과 키워드 검색(sparse)을 조합하는 하이브리드 검색에 사용.

**스냅샷 생성 (`--snapshot`)**

업로드 완료 후 places, photos 컬렉션의 스냅샷을 `data/snapshots/`에 다운로드합니다.

**입력**: `data/enrich/*_enrich.json`
**출력**: Qdrant places/photos 컬렉션 + `data/snapshots/` (선택)

---

## 부록: 전체 파일 요약

| 파일 | 라인 | 함수 | 입력 | 출력 |
|------|------|------|------|------|
| collect/config.py | 64 | - | .env | 설정 상수 |
| collect/tourapi.py | 163 | 6 | TourAPI | raw/tourapi_*.jsonl |
| collect/visitseoul.py | 154 | 6 | VisitSeoul API | raw/visitseoul.jsonl |
| collect/popply.py | 257 | 9 | popply.co.kr | raw/popply.jsonl |
| collect/seoul_culture.py | 116 | 3 | 열린데이터광장 API | raw/seoul_culture.jsonl |
| collect/shopping.py | 541 | 14 | 다이소/무신사/올리브영 | data/*.json |
| preprocess/config.py | 194 | 8 | - | 유틸 함수 |
| preprocess/tourapi.py | 214 | 5 | raw/tourapi_*.jsonl | preprocessed/tourapi_*.json |
| preprocess/visitseoul.py | 146 | 3 | raw/visitseoul.jsonl | preprocessed/visitseoul_*.json |
| preprocess/popply.py | 158 | 4 | raw/popply.jsonl | preprocessed/popply_팝업스토어.json |
| preprocess/seoul_culture.py | 176 | 7 | raw/seoul_culture.jsonl | preprocessed/seoul_culture_문화행사.json |
| preprocess/shopping.py | 257 | 7 | data/*.json | data/*.json |
| preprocess/merge.py | 123 | 2 | preprocessed/*.json | preprocessed/{카테고리}.json |
| enrich/generate_llm_text.py | 267 | 8 | preprocessed/*.json | enrich/*_enrich.json |
| enrich/generate_content_llm_text.py | 582 | 16 | preprocessed/*.json | enrich/*_enrich.json |
| qdrant_upsert.py | 270 | 6 | enrich/*_enrich.json | Qdrant DB |
