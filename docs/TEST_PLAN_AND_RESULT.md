# 테스트 계획 및 결과 보고서

이 문서는 실제 측정 결과를 기록하는 결과 문서로만 사용한다.  
평가 단계, 실행 명령, 지표 정의, 결과 파일 구조는 [EVALUATION.md](/Users/kim/SKN21-FINAL-2Team/docs/EVALUATION.md)에만 유지한다.

---

## 1. 문서 역할

- `EVALUATION.md`
  - 평가 방법, 실행 절차, 지표 정의
- `TEST_PLAN_AND_RESULT.md`
  - 실제 실행 일자별 결과 요약과 해석

---

## 2. 현재 상태

현재 문서에는 확정된 측정 결과가 아직 정리되어 있지 않다.  
향후 결과를 기록할 때는 아래 형식만 채워서 사용한다.

### 2026-03-15 비동기 GeoCoder 전환 점검

- 실행 환경:
  - `uv` 가상환경
  - FastAPI 백엔드 로컬 테스트
- 변경 요약:
  - `GeoCoder`를 `requests` 기반 동기 호출에서 `httpx.AsyncClient` 기반 비동기 호출로 전환
  - `intent`, `retriever`, `executor`, `diaries API`, `retrieval_place`, `tavily_search`의 geocoder 호출을 `await` 체인으로 정리
  - 위도/경도 인자 순서 혼동 가능성을 줄이기 위해 `get_address(latitude, longitude)` 시그니처로 통일
- 실행 명령:
  - `uv run python -m compileall app/agents app/api app/core app/utils`
  - `uv run python -m pytest tests/test_intent.py tests/test_cors.py tests/test_healthz.py -q`
- 결과 요약:
  - compileall 통과
  - pytest `27 passed`
- 해석:
  - geocoder 호출로 인해 이벤트 루프를 직접 블로킹하던 경로를 비동기 호출로 교체했다.
  - 핵심 스트리밍 테스트 기준으로 `intent -> retriever -> executor` 파이프라인 이벤트는 유지된다.

### 2026-03-15 executor 스트리밍 토큰 전파 점검

- 실행 환경:
  - Docker Compose 백엔드 테스트
- 변경 요약:
  - `executor`, `executor_missing`, `executor_general` 노드가 `RunnableConfig`를 받도록 수정
  - `collect_streamed_text()`에서 `llm.astream(..., config=config)`로 LangGraph 런타임 설정을 하위 LLM 호출까지 전달
  - custom token event가 그래프 이벤트 트리에 붙도록 `config`를 `adispatch_custom_event()`까지 유지
- 실행 명령:
  - `uv run python -m compileall backend/app/agents backend/app/core backend/tests`
  - `docker compose run --rm backend pytest tests/test_executor_streaming.py tests/test_cors.py -q`
- 결과 요약:
  - compileall 통과
  - pytest `27 passed`
- 해석:
  - `executor` 단계 시작 이벤트만 보이고 실제 토큰이 내려오지 않던 원인은 executor 노드에서 LangGraph `config`를 누락한 것이었다.
  - 수정 후 `executor` 스트리밍 토큰과 기존 SSE 단계 이벤트가 함께 유지된다.

---

## 3. 결과 기록 템플릿

### 실행 정보

- 실행 일시:
- 실행 환경:
- 입력 데이터:
- 사용 명령:

### 결과 요약

| 단계 | 핵심 지표 | 결과 | 비고 |
|------|-----------|------|------|
| Retrieval |  |  |  |
| Recommendation |  |  |  |
| Generation |  |  |  |

### 해석

- 잘된 점:
- 문제점:
- 다음 액션:
