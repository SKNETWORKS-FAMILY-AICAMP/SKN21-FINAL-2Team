# 벡터 DB 적재를 위한 전처리 계획

> 코멘트 작성법: 각 섹션 아래 `<!-- 코멘트: 내용 -->` 형식으로 달아주세요.

---

## 현재 데이터 현황

| 소스 | 파일 | 건수 | 상태 |
|---|---|---|---|
| Visit Seoul | `raw/contents_detail_all.json` | 2,936 | 원본 API 키 |
| Visit Korea | `add(image,info)/12_관광지.jsonl` | 1,298 | 정제된 스키마 |
| Visit Korea | `add(image,info)/39_음식점.jsonl` | 1,491 | 정제된 스키마 |
| Visit Korea | `add(image,info)/32_숙박.jsonl` | 343 | 정제된 스키마 |
| Visit Korea | `add(image,info)/99_투어.jsonl` | 88 | 정제된 스키마 |

<!-- 코멘트: -->

---

## Phase 1. Visit Seoul 데이터 정제

### 1-1. 필터링

아래 조건 중 하나라도 해당하면 제거:

- `cate_depth`에 `축제/공연/행사` 포함 (약 757건)
- `post_sj` (title)이 비어있는 항목
- `schdul_info_endde` 필드가 **존재하면서** 비어있거나 오늘 이전인 항목
  - 단, `schdul_info_endde` 자체가 없는 항목(일반 장소)은 유지

<!-- 코멘트: -->

### 1-2. 스키마 변환

**기준: Visit Korea 스키마에 맞추되, Visit Korea에 없는 키는 Visit Seoul 키/값 그대로 유지**

| 원본 키 | 정제 키 | 처리 방식 | Visit Korea 대응 여부 |
|---|---|---|---|
| `post_sj` | `title` | strip | ✅ |
| `cate_depth` | `category_depth` | strip (원본 한글 보존) | ❌ (Visit Seoul 전용) |
| `com_ctgry_sn` | `category_code` | - | ❌ (Visit Seoul 전용) |
| `relate_img[0]` | `image` | 첫 번째만 | ✅ |
| `main_img` | **제거** | - | - |
| `post_desc` | `description` | HTML 태그 제거 | ❌ (Visit Seoul 전용) |
| `traffic.new_adres` | `addr` | strip | ✅ |
| `traffic.map_position_y` | `mapy` | float 변환 | ✅ |
| `traffic.map_position_x` | `mapx` | float 변환 | ✅ |
| `traffic.subway_info` | `subway_info` | strip | ❌ (Visit Seoul 전용) |
| `extra.cmmn_telno` | `tel` | strip | ✅ |
| `extra.cmmn_use_time` | `usetime` | strip | ✅ |
| `extra.cmmn_hmpg_url` | `website` | strip | ❌ (Visit Seoul 전용) |
| `extra.closed_days` | `restdate` | strip | ✅ |
| `extra.usage_fee` | `fee` | strip | ✅ |
| `tag` | `tags` | list 그대로 | ❌ (Visit Seoul 전용) |
| `updt_dt_text` | `updated_at` | - | ❌ (Visit Seoul 전용) |
| `sumry` | `summary` | strip | ❌ (Visit Seoul 전용) |
| `restaurant.*` | `restaurant_type`, `menu` 등 | food 카테고리만 | ❌ (Visit Seoul 전용) |
| `accommodation.*` | `room_type`, `checkin_time` 등 | accommodation 카테고리만 | ❌ (Visit Seoul 전용) |
| - | `source` | 고정값 `"visitseoul"` | ✅ |
| - | `contenttypeid` | 카테고리 기반 역매핑 (아래 참고) | ✅ |

<!-- 코멘트: -->

### 1-3. 카테고리 분류

#### 최상위 카테고리 (`category`)

`cate_depth` 기준으로 아래와 같이 분류. **한글명 사용.**

| cate_depth | category | contenttypeid |
|---|---|---|
| 문화관광 | 관광지 | 12 |
| 역사관광 | 관광지 | 12 |
| 자연관광 | 관광지 | 12 |
| 체험관광 | 관광지 | 12 |
| 쇼핑 | 투어 | 99 |
| 음식 | 음식점 | 39 |
| 숙박 | 숙박 | 32 |

#### 콘텐츠 카테고리 예외 처리

`관광지`로 분류된 항목 중, `cate_depth` 하위에 공연·행사성 키워드가 포함된 경우 → `category`를 **콘텐츠**로 변경.

해당 `cate_depth` 값 (예시):
- `문화관광 > 공연시설`
- `문화관광 > 행사시설`
- 기타 하위 키워드에 `공연`, `행사`, `축제` 포함

#### 하위 카테고리 처리 (`category_depth`)

`cate_depth` 원본값을 `category_depth` 필드에 그대로 보존.
- 표시(UI)용으로 활용
- Qdrant 페이로드에 포함, 필터링보다는 검색 결과 표시에 사용

<!-- 코멘트: -->

---

## Phase 2. Visit Korea 데이터 정제

Visit Korea 스키마가 기준. Visit Seoul 데이터도 이 스키마에 맞춰 변환.

### Visit Korea 기존 스키마

```
contentid, title, contenttypeid, image, usetime, restdate, parking, fee,
addr, mapy, mapx, tel, llm_text
```

### 카테고리 매핑

| contenttypeid | category |
|---|---|
| 12 | 관광지 |
| 32 | 숙박 |
| 39 | 음식점 |
| 99 | 투어 |

### 정제 방침

- 기존 스키마 유지, 별도 변환 없음
- `source` 필드 추가: `"visitkorea"`
- `llm_text` 재사용 여부는 Phase 3에서 결정

<!-- 코멘트: -->

---

## Phase 3. 중복 제거 및 병합

> **우선순위**: Phase 2 완료 후 진행 (llm_text 생성보다 먼저)

### 중복 판단 기준 (우선순위 순)

1. 장소명 완전 일치 + 좌표 500m 이내
2. 장소명 유사도 90% 이상 + 좌표 200m 이내

### 중복 처리 방침

- **Visit Seoul 데이터 우선 유지** (스키마가 더 풍부하고 품질이 높음)
- Visit Korea 중복 항목은 제거
- Visit Korea에만 있는 항목은 그대로 추가

### 병합 결과

```
data/merged_all.json  ← Visit Seoul (정제) + Visit Korea (중복 제거)
```

<!-- 코멘트: -->

---

## Phase 4. llm_text 생성

> **우선순위 낮음**: 중복 제거 완료 후 진행

리트리버가 임베딩해서 검색할 텍스트. 검색 의도와 매칭되도록 정보 밀도를 높이는 게 핵심.

### 생성 형식 (안)

```
장소명: {title}
카테고리: {category_depth}
태그: {tags}
요약: {summary}
설명: {description}
주소: {addr}
교통: {subway_info}
운영시간: {usetime}
휴무일: {restdate}
이용요금: {fee}
```

- `description`이 너무 길면 앞 500자만 사용 (토큰 제한 고려)
- 빈 필드는 해당 줄 제외
- 음식점의 경우 `menu`, `cuisine_kind` 추가
- 숙박의 경우 `room_type`, `checkin_time` 추가

### 임베딩 모델

- **BGE-M3** (다국어 지원)
- 임베딩 자체는 추후 진행

<!-- 코멘트: -->

---

## Phase 5. Qdrant 페이로드 설계

### 컬렉션 스키마

```json
{
  "vector": [float, ...],
  "payload": {
    "contentid": "KOP000383",
    "source": "visitseoul",
    "title": "장소명",
    "category": "관광지",
    "category_depth": "문화관광 > 전시시설 > 박물관",
    "contenttypeid": 12,
    "image": "https://...",
    "addr": "서울 강남구...",
    "mapy": 37.5,
    "mapx": 127.0,
    "tel": "02-...",
    "usetime": "11:00~22:00",
    "restdate": "월요일",
    "fee": "무료",
    "website": "https://...",
    "subway_info": "2호선 강남역 3번 출구",
    "tags": ["태그1", "태그2"],
    "llm_text": "...",
    "updated_at": "2025.12.02"
  }
}
```

### 필터링에 활용할 필드

| 필드 | 용도 |
|---|---|
| `category` | 카테고리별 필터 (관광지/음식점/숙박/투어/콘텐츠) |
| `source` | 데이터 소스 구분 |
| `mapy` / `mapx` | 위치 기반 검색 (geo filter) |
| `contenttypeid` | Visit Korea 호환 타입 필터 |

<!-- 코멘트: -->

---

## 작업 순서

| 순서 | 스크립트 | 입력 | 출력 | 상태 |
|---|---|---|---|---|
| 1 | `visitseoul_cleaner.py` (수정) | `raw/contents_detail_all.json` | `data/contents_visitseoul.json` | 수정 필요 |
| 2 | `data_merger.py` (신규) | `contents_visitseoul.json` + `add(image,info)/*.jsonl` | `data/merged_all.json` | 미착수 |
| 3 | `llm_text_builder.py` (신규) | `merged_all.json` | `merged_all.json` (llm_text 추가) | 미착수 (나중) |
| 4 | `qdrant_uploader.py` (신규) | `merged_all.json` | Qdrant 컬렉션 | 미착수 (나중) |

<!-- 코멘트: -->

---

## 미결 사항

- [ ] 콘텐츠 카테고리 해당 `cate_depth` 값 목록 확정
- [ ] 중복 제거 유사도 임계값 조율
- [ ] Visit Korea `llm_text` 재사용 여부
- [ ] Qdrant 컬렉션명, 벡터 차원 수 확정
- [ ] 다국어 데이터 수집 및 처리 (우선순위 낮음)

<!-- 코멘트: -->
