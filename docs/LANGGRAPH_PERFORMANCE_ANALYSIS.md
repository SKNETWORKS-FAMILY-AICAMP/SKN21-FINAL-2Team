# LangGraph 파이프라인 성능·레이턴시 분석

> 현재 `backend/app/agents/graph.py` 기준으로 성능 병목과 개선 포인트를 정리한 문서

---

## 1. 전체 흐름 요약

- 그래프:
  - `intent`
  - `planner` 또는 `geocoder` 또는 `executor_general`
  - `geocoder`
  - `retriever`
  - 결과 없으면 `retriever` 재시도
  - 재시도 후에도 없으면 `web_search`
  - 최종 `executor`
- 특징:
  - 노드 간 실행은 순차적이다.
  - 토큰 스트리밍은 executor 계열 노드에서만 발생한다.
  - 현재 기본 fallback은 Tavily가 아니라 `web_search_node.py`의 Naver Local Search다.

---

## 2. 병목 요약

| 구분 | 위치 | 원인 | 영향 |
|------|------|------|------|
| Executor | `_build_location_context()` | 좌표→주소 변환이 순차적 | 첫 토큰 전 고정 지연 |
| GeoCoder | `app/utils/geocoder.py` | 주소/좌표 변환 캐시 부재 | 반복 요청 시 외부 API 재호출 |
| Retriever | TRIP_PLANNING 검색 | itinerary 항목별 검색 후 일반 검색 fallback이 추가로 발생 가능 | 일정형 요청 지연 증가 |
| Retriever | `search_hybrid` | 임베딩/rerank가 `to_thread` 기반 CPU 작업 | 동시 검색 시 스레드 풀/CPU 점유 |
| Web Search | `web_search_node.py` | fallback 키워드별 Naver Local Search 호출 | 검색 실패 케이스 지연 증가 |
| Chat API | `get_graph_app()` | 전역 락 + 그래프 앱 재사용 판단 | 동시 요청 시 직렬화 대기 |
| Prompt 크기 | intent/planner/executor | messages/context 전달량 증가 | 토큰 비용·응답 지연 증가 |

---

## 3. 상세 분석

### 3.1 GeoCoder 캐시 부재

위치:

- `backend/app/utils/geocoder.py`

문제:

- 같은 주소/좌표에 대한 변환이 반복되어도 캐시가 없다.
- geocoder, executor, fallback 검색이 모두 같은 변환 계층을 공유한다.

개선:

- `address -> (lat, lon)` 캐시
- `(lat, lon) -> address` 캐시
- 동일 키 동시 요청 coalescing

---

### 3.2 Executor 위치 컨텍스트 구성

위치:

- `backend/app/agents/executor.py`

문제:

- 사용자 GPS 주소와 `slots.location` 주소를 각각 조회할 때 순차 호출이 발생할 수 있다.
- 이 구간은 토큰 스트리밍 시작 전에 실행되므로 체감 지연에 직접 영향이 있다.

개선:

- `asyncio.gather` 기반 병렬 조회
- GeoCoder 캐시 도입과 함께 적용

---

### 3.3 Retriever의 일정형 fallback 비용

위치:

- `backend/app/agents/retriever.py`

문제:

- `TRIP_PLANNING`은 itinerary 항목별 검색을 먼저 수행한다.
- 결과가 부족하거나 0건이면 일반 검색 fallback이 추가로 수행된다.
- 즉 일정형 요청은 기본적으로 일반 검색보다 검색 횟수가 더 많다.

개선:

- fallback 발생률이 높으면 planner 쿼리 품질을 먼저 개선
- fallback 시 재사용 가능한 anchor/쿼리 구성 정보는 캐시
- 항목별 `candidate_k`, `rerank_top_k`를 과도하게 키우지 않기

---

### 3.4 Web Search fallback

위치:

- `backend/app/agents/web_search_node.py`

문제:

- retriever 2회 실패 시에만 진입하므로, 실패 케이스의 tail latency를 크게 늘릴 수 있다.
- 키워드별 Naver Local Search를 병렬 호출하지만, 외부 API RTT 자체는 남는다.

개선:

- fallback 키워드 수를 제한해 불필요한 외부 호출을 줄이기
- 결과 중복 제거 규칙은 유지하되, 검색어 조합 우선순위를 더 엄격히 관리
- fallback 결과 품질/성공률을 `retrieval_diagnostics`에 함께 남겨 운영 지표화

---

### 3.5 그래프 앱 초기화 락

위치:

- `backend/app/api/chat.py`

문제:

- 요청마다 그래프 앱 재사용 여부를 확인하는 과정에서 락 대기가 생길 수 있다.

개선:

- 앱 재컴파일 조건을 더 엄격히 줄이기
- checkpointer 교체와 앱 생성 경로를 분리할 수 있는지 검토

---

### 3.6 `search_hybrid`의 CPU 비용

위치:

- `backend/app/core/retrieval/place.py`

문제:

- 텍스트 임베딩, 이미지 임베딩, sparse 검색, reranker가 한 요청 안에 묶인다.
- 이벤트 루프 블로킹은 피하고 있지만, CPU와 스레드 풀은 계속 사용한다.

개선:

- `candidate_k`, `rerank_top_k`, `final_k`를 트래픽 기준으로 조정
- 높은 동시성 상황에서는 retriever 진입 레벨의 세마포어도 검토

---

### 3.7 프롬프트/컨텍스트 크기

위치:

- `intent.py`
- `planner.py`
- `executor.py`

문제:

- 최근 메시지, 선호도, itinerary, place context가 함께 쌓이면 토큰 사용량이 빠르게 커진다.

개선:

- 오래된 대화는 요약 필드 중심으로 축약
- place context에서 실제 생성에 필요 없는 필드 제거

---

## 4. 우선순위

| 우선순위 | 항목 | 예상 효과 | 난이도 |
|----------|------|-----------|--------|
| 1 | GeoCoder 캐시 도입 | 외부 API 호출·지연 전반 감소 | 중간 |
| 2 | Executor 위치 컨텍스트 병렬화 | 첫 토큰 전 지연 감소 | 낮음 |
| 3 | Retriever 파라미터 튜닝 | 일정형/복합 검색 비용 절감 | 낮음 |
| 4 | Web Search fallback 키워드 최적화 | 실패 케이스 tail latency 감소 | 낮음 |
| 5 | 그래프 앱 초기화 경량화 | 동시 요청 대기 감소 | 중간 |
| 6 | 메시지/컨텍스트 축약 | 비용·응답 지연 감소 | 중간 |

---

## 5. 참고 파일

- 그래프 정의: `backend/app/agents/graph.py`
- 라우팅: `backend/app/agents/grapy_route.py`
- 검색: `backend/app/agents/retriever.py`
- fallback 검색: `backend/app/agents/web_search_node.py`
- 실행: `backend/app/agents/executor.py`
- 지오코딩: `backend/app/utils/geocoder.py`
- 검색 코어: `backend/app/core/retrieval/place.py`
