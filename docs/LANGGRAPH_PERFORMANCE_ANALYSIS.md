# LangGraph 파이프라인 성능·레이턴시 분석

> `backend/app/agents/graph.py` 및 관련 노드(intent, planner, retriever, executor)를 기준으로 성능 병목과 레이턴시 개선 포인트를 정리한 문서입니다.

---

## 1. 전체 흐름 요약

- **그래프**: `intent` → (라우팅) → `planner` / `retriever` / `executor_general` → (planner 분기) → `retriever` / `executor_missing` → `retriever` → `executor` → END
- **특징**: 모든 노드가 **순차 실행**이며, LLM 호출이 intent → planner(선택) → retriever(선택) → executor 계열 순으로 이어짐.
- **스트리밍**: executor 계열 노드에서만 토큰 스트리밍; intent/planner는 `ainvoke`로 한 번에 완료 후 다음 노드로 진행.

---

## 2. 성능·레이턴시 병목 요약

| 구분 | 위치 | 원인 | 영향 |
|------|------|------|------|
| **Executor** | `_build_candidate_place_pairs()` | 후보 N명에 대해 GeoCoder 호출을 **순차** 수행 | N × (지오코딩 레이턴시) |
| **Executor** | `_build_location_context()` | 사용자/슬롯 위치마다 `get_address` 순차 2회 | 고정 2회 외부 API |
| **GeoCoder** | 전역 | 주소/좌표 변환 결과 **캐시 없음** | 동일 주소 반복 요청 시 매번 API |
| **Retriever** | TRIP_PLANNING | itinerary 항목별 검색은 Semaphore(3)로 병렬이지만, **일반 검색 전 reverse_geocoder + anchor 검색**이 순차 | 위치 해석 구간 지연 |
| **Tavily Fallback** | `tavily_search_for_places` | `web_search()`가 **동기** 호출 → 이벤트 루프 블로킹 | 최대 10초 블로킹 가능 |
| **Tavily Fallback** | `extract_placeinfos()` | 추출된 각 장소마다 `GeoCoder.get_coordinates()` **순차** | M × 지오코딩 |
| **Chat API** | `get_graph_app()` | 매 요청마다 **비동기 락** + checkpointer 비교 | 동시 요청 시 직렬화 대기 |
| **PlaceRetriever** | `search_hybrid` | `asyncio.to_thread`로 블로킹 회피하지만, **임베딩/rerank 등 CPU 작업**이 스레드 풀 점유 | 동시 검색 많을 때 지연 |
| **메시지/컨텍스트** | intent/planner/executor | 매 노드 `messages[-10:]` 등으로 **풀 컨텍스트** 전달 | 토큰 수·비용·지연 증가 |

---

## 3. 상세 분석 및 개선 제안

### 3.1 Executor: `_build_candidate_place_pairs` (가장 큰 병목)

**위치**: `backend/app/agents/executor.py` 51–84행

**문제**  
- 후보(candidates) 리스트를 한 번에 순회하면서, 주소만 있고 좌표가 없으면 `await GeoCoder.get_coordinates(address)`, 좌표만 있으면 `await GeoCoder.get_address(lat, lng)`를 **한 건씩 순차** 호출.
- 후보 5~10명이면 5~10회 연속 외부 API 호출로, 첫 토큰 전에 수 초가 소요될 수 있음.

**개선**  
- 동일 후보에 대해 `get_coordinates` / `get_address`를 **병렬**로 처리 (예: `asyncio.gather`).
- 가능하면 주소/좌표 쌍을 **한 번에** 가져오는 배치 API나, 같은 주소/좌표는 한 번만 호출하도록 루프 밖에서 중복 제거 후 병렬 호출.

```python
# 개선 예시: 병렬 처리
async def _build_candidate_place_pairs(...):
    tasks = []
    for c in candidates:
        # 좌표/주소 보강이 필요한 경우만 태스크로 수집
        tasks.append(_resolve_place_geo(c))
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
```

---

### 3.2 GeoCoder 캐시 부재

**위치**: `backend/app/utils/geocoder.py`  
- `get_coordinates(address)`, `get_address(lat, lng)` 모두 **캐시 없이** 매번 NCP/Naver API 호출.

**문제**  
- 같은 장소가 여러 후보/여러 턴에 반복되면 동일 주소·좌표에 대해 반복 호출.
- Executor뿐 아니라 Retriever(위치 보강), Tavily 추출 단계에서도 사용되므로, 캐시 효과가 큼.

**개선**  
- 프로세스 내 in-memory 캐시 (TTL 또는 최대 크기 제한):
  - `address → (lat, lng)` 캐시
  - `(lat, lng) → address` 캐시 (반올림 키로 저장해 근사 매칭 가능)
- 동시 요청 제어가 필요하면 동일 키에 대해 한 번만 API 호출하고 나머지는 대기시키는 패턴 적용.

---

### 3.3 Executor: `_build_location_context`

**위치**: `backend/app/agents/executor.py` 342–363행

**문제**  
- `input_lat/input_long`가 있으면 `get_address(input_lat, input_long)` 1회.
- `slots.location`이 있으면 `get_address(slots.location.lat, slots.location.lon)` 1회.
- 두 호출이 **순차**라서, 두 번의 네트워크 RTT가 연속으로 발생.

**개선**  
- 두 위치가 모두 필요하면 `asyncio.gather`로 한 번에 요청.
- GeoCoder에 캐시를 넣으면, 같은 좌표가 재사용될 때 레이턴시 제거.

---

### 3.4 Tavily Fallback: 동기 `web_search` 및 순차 지오코딩

**위치**: `backend/app/core/retrieval/tavily_search.py`

**문제 1**  
- `tavily_search_for_places`가 내부에서 `tavily.web_search(query)`를 **동기**로 호출.
- `web_search`는 ThreadPoolExecutor로 타임아웃(10초)을 걸었지만, **호출자 코루틴은 `web_search`가 끝날 때까지 대기**하므로, 그 동안 다른 async 작업을 하지 못함. (실제로는 run_in_executor가 아니라 sync 호출이므로 이벤트 루프 블로킹은 아님. 단, web_search 자체가 동기라서 스레드 풀에서 돌려줘야 함.)
- 재확인: `tavily_search_for_places`는 `async`인데 `web_results, web_context = tavily.web_search(query)`는 **동기 함수 호출**이므로, 이 한 줄이 최대 10초 동안 **이벤트 루프를 블로킹**함. → 개선 필요.

**개선**  
- `web_search`를 `asyncio.to_thread(tavily.web_search, query)` 또는 `loop.run_in_executor`로 감싸서 **논블로킹**으로 호출.
- 타임아웃은 `asyncio.wait_for(..., timeout=10)`으로 적용.

**문제 2**  
- `extract_placeinfos` 안에서 `for place in extraction_result.places: await GeoCoder.get_coordinates(place.address)` 로 **순차** 호출.

**개선**  
- `asyncio.gather(*[GeoCoder.get_coordinates(p.address) for p in extraction_result.places])` 로 한 번에 병렬 호출 후, 결과만 매핑.

---

### 3.5 Retriever: TRIP_PLANNING 시 일반 검색 Fallback

**위치**: `backend/app/agents/retriever.py` 421–441행

**문제**  
- TRIP_PLANNING일 때 `_search_for_trip_planning` 결과가 0건이면 `_search_for_general`을 **한 번 더** 호출.
- `_search_for_general` 내부에서 `reverse_geocoder` + (필요 시) `_resolve_seoul_anchor` → Naver 검색 등 **순차** 실행.
- 이미 trip 검색에서 한 번 시간을 쓴 뒤, fallback에서 다시 위치 해석·검색을 하므로 체감 레이턴시가 길어짐.

**개선**  
- Fallback이 자주 발생하면, trip 검색과 병렬로 “일반 검색용 쿼리”만 미리 준비해 두거나, fallback 시 재사용할 수 있는 위치/앵커 정보를 trip 검색 단계에서 같이 계산해 두는 방식 검토.
- 또는 fallback 시 위치 보강을 최소화(예: 사용자 좌표만 사용)하는 옵션을 두어 레이턴시를 줄일 수 있음.

---

### 3.6 그래프 앱 초기화: `get_graph_app()` 락

**위치**: `backend/app/api/chat.py` 46–56행

**문제**  
- 매 스트리밍/비스트리밍 요청마다 `await get_graph_app()`을 호출하고, 내부에서 `async with _graph_app_lock`으로 **전역 락**을 잡음.
- checkpointer가 매번 갱신되는 구조라면, 락 안에서 `get_checkpointer()` + `workflow().compile(checkpointer=...)`가 비교적 무거울 수 있고, 동시 요청이 많을 때 **직렬화**로 대기 시간이 생김.

**개선**  
- 앱이 이미 컴파일되어 있고 checkpointer만 바뀌는 경우, “앱 재사용 + checkpointer만 주입”이 가능한지 LangGraph API 확인.
- 불가능하면 초기화 경로를 최소화(예: 앱 생성은 한 번, checkpointer 갱신만 주기적으로)하거나, 락 범위를 “앱이 None일 때만 컴파일”로 줄여서 동시성 확보.

---

### 3.7 PlaceRetriever: search_hybrid 내부

**위치**: `backend/app/core/retrieval/place.py` 233행 근처

**현황**  
- `text_model.encode`, `client.query_points`, reranker 등은 이미 `asyncio.to_thread`로 스레드 풀에 넣어 이벤트 루프 블로킹은 피하고 있음.

**잠재 이슈**  
- 동시에 많은 검색 요청이 들어오면 스레드 풀과 CPU(임베딩/rerank)가 포화되어 지연이 커질 수 있음.
- TRIP_PLANNING에서 itinerary 항목별로 `search_hybrid`를 Semaphore(3)로 제한한 것은 적절함. 다만 `candidate_k`/`rerank_top_k`가 크면 항목당 비용이 커짐.

**개선**  
- 서빙 파라미터(`candidate_k`, `rerank_top_k`)를 트래픽에 맞게 튜닝.
- 필요하면 동시 검색 수를 제한하는 세마포어를 한 단계 위(예: retriever_node 진입 시)에서 적용해 과도한 동시 검색 방지.

---

### 3.8 메시지/컨텍스트 크기

**위치**: intent, planner, executor 계열

**문제**  
- 여러 노드에서 `state.get("messages", [])[-10:]`로 최근 10턴을 그대로 LLM에 전달.
- 프롬프트에 `prefs_info`, `slots_info`, `place_context`, `itinerary_context` 등이 모두 붙어 토큰 수가 커지면 비용과 생성 지연이 증가.

**개선**  
- 이미 요약 필드(`summary_message` 등)가 있으면, 오래된 메시지는 요약만 넣고 최근 2–3턴만 원문 사용하는 방식 검토.
- `place_context`는 최종 노출 후보 수(`final_k`)에 맞춰 이미 제한되어 있으므로, 불필요한 중복 필드는 제거해 토큰만 줄여도 도움됨.

---

## 4. 그래프 구조 자체 (graph.py)

**위치**: `backend/app/agents/graph.py`

**현황**  
- 노드 추가, 엣지, 조건부 라우팅이 명확하고, 불필요한 노드/엣지는 없음.
- **순차 실행**은 LangGraph의 기본 모델이므로, “의도 → 계획/검색 → 실행” 순서를 바꾸지 않는 한 그래프 구조 변경만으로 큰 레이턴시 절감은 어렵고, **각 노드 내부의 I/O·LLM 호출 최적화**가 핵심.

**선택적 개선**  
- Intent에서 “이미지만 있음” 같은 경우 LLM을 타지 않고 바로 IMAGE_SIMILAR로 보내는 것은 이미 구현됨.
- PLACE_INQUIRY 등에서 “단순 키워드만 있고 슬롯이 거의 비어 있음”이면 planner를 스킵하고 바로 retriever로 가는 **단축 경로**를 라우팅에 추가하는 것은 가능하나, 기획과 정확도 영향 검토 후 도입하는 것이 좋음.

---

## 5. 우선순위 정리

| 우선순위 | 항목 | 예상 효과 | 난이도 |
|----------|------|-----------|--------|
| 1 | Executor `_build_candidate_place_pairs` 병렬화 | 첫 토큰 전 레이턴시 수 초 단축 | 낮음 |
| 2 | GeoCoder 주소/좌표 캐시 도입 | 반복 호출 구간 전반 레이턴시·API 비용 감소 | 중간 |
| 3 | Tavily `web_search`를 `run_in_executor`/`to_thread`로 비동기화 | Fallback 시 이벤트 루프 블로킹 제거 | 낮음 |
| 4 | Tavily `extract_placeinfos` 내 GeoCoder 병렬 호출 | Fallback 경로 레이턴시 감소 | 낮음 |
| 5 | `_build_location_context` 두 번의 get_address 병렬화 | 수백 ms 단축 | 낮음 |
| 6 | `get_graph_app()` 락/초기화 범위 최소화 | 동시 요청 시 대기 시간 감소 | 중간 |
| 7 | Retriever TRIP fallback 시 위치 보강 최소화 | Fallback 케이스 레이턴시 감소 | 중간 |
| 8 | 메시지/컨텍스트 토큰 축소 (요약+최근 N턴) | 비용·생성 지연 감소 | 중간 |

---

## 6. 참고 파일

- 그래프 정의: `backend/app/agents/graph.py`
- 라우팅: `backend/app/agents/grapy_route.py`
- 노드: `intent.py`, `planner.py`, `retriever.py`, `executor.py`
- 지오코딩: `backend/app/utils/geocoder.py`
- Tavily: `backend/app/core/retrieval/tavily_search.py`
- 채팅 API: `backend/app/api/chat.py` (`get_graph_app`, 스트리밍 처리)
- 시퀀스/아키텍처: `docs/agent_sequence_diagrams.md`, `CLAUDE.md`
