# 장소 검색(Retrieval) 동작 원리

> 관련 파일: `backend/app/core/retrieval/place.py`, `backend/app/core/retrieval/place_score.py`, `backend/app/agents/retriever.py`, `backend/app/agents/geocoder_node.py`, `backend/app/agents/web_search_node.py`

---

## 개요

사용자가 "홍대 분위기 좋은 카페"라고 입력하거나 사진을 첨부하면, 시스템은 단순 키워드 매칭이 아니라 **여러 채널로 후보를 모은 뒤 점수와 규칙을 함께 반영**해 장소를 찾는다.

현재 파이프라인은 크게 아래 순서로 진행된다.

```text
1단계: geocoder가 위치 anchor를 확정
        ↓
2단계: retriever가 텍스트/이미지/Qdrant 채널로 후보 수집
        ↓
3단계: 점수 보정 + reranker로 재정렬
        ↓
4단계: 결과가 없으면 retriever 재시도
        ↓
5단계: 여전히 없으면 Naver Local Search fallback
```

---

## 검색 유형: 일반 검색 vs 여행 일정 계획

시스템은 의도를 먼저 파악한 뒤, 검색 방식을 나눈다.

### 일반 검색

"홍대 감성 카페 추천해줘"처럼 특정 장소를 찾는 경우다.

```text
사용자 입력
  → geocoder로 위치 anchor 확인
  → hybrid 검색 1회
  → 후보 풀 생성
```

### 여행 일정 계획 (`TRIP_PLANNING`)

"2박 3일 서울 여행 일정 짜줘"처럼 여행 계획을 요청하는 경우다.

```text
Planner가 itinerary 생성
  → itinerary 항목별 개별 검색 (Semaphore=3 병렬)
  → item별 후보 취합
  → 일정별 대표 후보 선택
  → 결과가 0개일 때만 일반 검색 fallback
```

핵심 차이:

- 일반 검색은 단일 질의 중심이다.
- 일정형 검색은 itinerary 항목별 검색이 기본이며, 전체 실패 시에만 일반 검색을 추가 시도한다.

---

## 검색 범위 결정 (`search_scope`)

Retriever는 입력 유형과 의도에 따라 검색 범위를 먼저 정한다.

| 값 | 의미 | 사용 상황 |
| --- | --- | --- |
| `place_only` | 장소 컬렉션만 검색 | `TRIP_PLANNING` |
| `photo_only` | 사진 컬렉션만 검색 | `IMAGE_SIMILAR`, 이미지 전용 입력 |
| `auto` | 장소 + 사진 컬렉션 동시 사용 | 일반 텍스트, 텍스트+이미지 복합 입력 |

---

## 입력 유형별 검색 채널

### 케이스 1. 텍스트만 입력한 경우

```text
"홍대 감성 카페 추천"
  ├─ Dense text 검색 (BGE-M3)
  ├─ Sparse text 검색 (Qdrant sparse)
  └─ CLIP text→image 검색
```

### 케이스 2. 이미지만 입력한 경우

```text
사진 첨부
  ├─ CLIP vision 검색
  └─ describe_image()로 생성한 감성 설명 기반 text 검색
```

### 케이스 3. 텍스트 + 이미지 동시 입력

```text
"이런 분위기 카페 홍대에서 찾아줘" + 사진
  ├─ Dense text 검색
  ├─ Sparse text 검색
  ├─ CLIP text→image 검색
  ├─ CLIP vision 검색
  └─ 이미지 설명 기반 text 검색
```

### 조건부 보조 채널

- BM25 계열 sparse 검색은 텍스트 입력이 있을 때 보조 채널로 동작한다.
- 세부 활성화 여부는 `backend/app/utils/config.py`의 retrieval 설정을 따른다.

---

## 위치 해석과 Geo Filter

검색 전 단계에서 `geocoder_node.py`가 위치 기준점을 만든다.

우선순위:

1. 사용자 GPS가 서울 안이면 GPS를 anchor로 사용
2. `slots.location`이 랜드마크 사전에 있으면 해당 좌표 사용
3. 정규화 location 또는 Naver 검색으로 anchor 확보
4. `input_tags` 안의 지역 키워드로 anchor 재시도

이후 Qdrant 검색에서는 아래 값이 geo filter에 활용된다.

- `location_anchor_lat`
- `location_anchor_lon`
- `location_anchor_radius_m`

특징:

- 장소 컬렉션에는 geo filter가 적용된다.
- 사진 컬렉션에는 geo 필드가 없으므로 위치 필터가 직접 적용되지 않는다.
- 첫 검색 결과가 없으면 retriever가 반경을 확장해 한 번 더 재시도한다.

---

## 점수 합산 방식

1차 후보 점수는 채널별 순위를 기반으로 RRF(Reciprocal Rank Fusion) 방식으로 합산한다.

```text
채널 기여 점수 += 채널_가중치 × (1 / (60 + 해당_채널_순위))
```

이후 점수 보정과 reranker가 이어진다.

---

## 2단계: 점수 보정 (Boost)

1차 후보에 대해 아래 보정이 추가된다.

- 키워드 매칭 보너스
- 지역 텍스트 보너스
- 거리 보너스
- 주소 토큰 보너스

최종 blended score 계산식은 아래 개념을 따른다.

```text
score = first_stage_score + BOOST_WEIGHT × boost 합계
```

세부 상수:

- `BOOST_WEIGHT`
- `GEO_PROXIMITY_RADIUS_KM`
- `ENABLE_ADDR_SPARSE_BOOST`

위 값들은 `backend/app/utils/config.py`에서 관리한다.

---

## 3단계: 최종 순위 결정 (Reranker)

상위 후보군에 대해 CrossEncoder reranker를 적용한다.

- 모델: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- 입력: `query`와 후보 장소 정보의 쌍
- 결과: `rerank_score`

정렬 우선순위:

1. `blended_score`
2. reranker 적용 가능 시 `rerank_score`
3. 최종 거리 재검증

주의:

- query가 비어 있거나 reranker 로드에 실패하면 reranker 없이 점수 순으로 유지된다.

---

## 4단계: 최종 후보 선별

최종 반환 직전에는 다양성과 중복 제거가 한 번 더 적용된다.

### 일반 검색

- 기본: `deterministic`
  - 점수 우선
  - 카테고리 분산 tie-break
  - 동일 장소명 중복 제거
- 선택: `explore`
  - 상위 pool에서 점수 가중 랜덤 선택

### 일정형 검색

- itinerary 항목별 최고 후보 1개를 우선 선택
- 이미 배정된 장소명은 다른 일정 항목에 중복 배치하지 않는다

### 최종 거리 재검증

- anchor가 있으면 `MAX_DISTANCE_KM` 이내 후보만 유지한다
- 모두 탈락하면 기존 결과를 fallback으로 유지한다

---

## 5단계: 검색 결과 0건일 때 fallback

현재 기본 fallback은 **Tavily가 아니라 `web_search_node.py`의 Naver Local Search**다.

동작 순서:

1. retriever 1차 검색
2. 결과 0건이면 반경 확장 후 retriever 재시도
3. 재시도 후에도 0건이면 `web_search` 노드 진입
4. `GeoCoder.search_places()`로 Naver Local Search 수행
5. 서울 bbox 내 결과만 `PlaceInfo`로 변환

즉, 현재 문서에서 Tavily fallback으로 설명하던 부분은 구버전 기준이며, 기본 LangGraph 경로는 Naver Local Search fallback으로 이해해야 한다.

---

## 6단계: 답변 생성과 장소 매핑

Executor는 검색 후보를 바탕으로 답변을 생성하고, 본문에 실제로 언급된 장소만 `place_info_list`에 남긴다.

주요 규칙:

- 후보 → `PlaceInfo` 변환 시 이름/주소/좌표가 모두 있어야 함
- 답변 본문에서 링크명/볼드명으로 장소명을 추출
- 실제 언급된 장소만 추천 결과로 반환
- 후보군 밖 장소명이 섞이면 잘못된 매핑을 차단

이미지 입력이 있으면:

- Executor가 이미지 원본을 base64 data URL로 변환해 LLM에 함께 전달한다

---

## 점수 필드 요약

검색 결과에는 아래 점수 계층이 함께 들어갈 수 있다.

| 필드 | 의미 |
| --- | --- |
| `first_stage_score` | 채널 RRF 합산 |
| `score_boost_total` | boost 합산 |
| `score` | 1차 점수 + boost 반영 |
| `blended_score` | reranker/거리 보정까지 반영된 중간 점수 |
| `rerank_score` | CrossEncoder 최종 관련도 |

실제 사용 시 어떤 필드가 채워지는지는 검색 경로와 설정에 따라 달라질 수 있다.

---

## 문서 관리 메모

- fallback 경로 변경 시 [agent_sequence_diagrams.md](/Users/kim/SKN21-FINAL-2Team/docs/agent_sequence_diagrams.md), [llm_model_software.md](/Users/kim/SKN21-FINAL-2Team/docs/llm_model_software.md)를 함께 수정
- 점수 상수 설명은 코드 상수명과 동일하게 유지하고, 수치는 설정 변경 시 다시 검증 후 갱신
