# 프로젝트 분석 및 실행 점검

> 2026-03-17 기준 전체 프로젝트 구조, 실행 검증 결과, 개선 포인트를 정리한 문서

---

## 1. 프로젝트 요약

현재 저장소는 다음 3개 축으로 구성되어 있다.

1. `backend/`
   - FastAPI 기반 API 서버
   - LangGraph 기반 챗봇 흐름
   - Qdrant/MySQL 연계 검색 및 저장
2. `frontend/`
   - Next.js App Router 기반 사용자 인터페이스
   - 채팅, 탐색, 북마크, 마이페이지, 여행 기록 기능 포함
3. `nginx/`, `docker-compose*.yml`
   - 프록시 및 로컬/통합 실행 환경

---

## 2. 이번 분석에서 확인한 주요 변경 흐름

코드 상태를 기준으로 볼 때 최근 변경은 아래 방향으로 집중되어 있다.

### 백엔드

- 챗봇 상태 모델 정리
  - `PlaceInfo`와 Tavily 관련 모델이 `backend/app/agents/models/`로 분리됨
- 검색 확장
  - `backend/app/core/retrieval/tavily_search.py` 추가
- 스트리밍 응답 및 채팅 저장 로직 보강
  - `backend/app/core/llm_streaming.py`
  - `backend/app/api/chat.py`: **SSE 스트리밍 파이프라인 복구 (custom_event 'token' 처리 추가)**
- CORS 및 정적 파일 노출 경로 정리
  - `backend/app/main.py`

### 프론트엔드

- `src/features/chat/` 중심으로 채팅 기능 모듈화
- `/moments` 페이지 추가로 여행 기록 기능 확장
- `/api` rewrite 기반 백엔드 연결 정책 유지
- 로그인 이후 이동 경로와 자동시작 플로우 로직 보강

---

## 3. 실행 검증 결과

### 3.1 백엔드

실행/검증 명령:

- `uv run python -m compileall app`
- `uv run pytest tests/test_healthz.py tests/test_intent.py -q`
- `uv run pytest tests -q`
- `uv run pytest -q`

검증 결과:

- `compileall`: 성공
- 핵심 로딩 테스트 2건: 성공
  - `2 passed`
- `tests/` 기준 전체 백엔드 테스트: 부분 실패
  - `59 passed, 4 failed`
- 루트 기준 전체 `pytest` 수집: 실패
  - `backend/tmp/test_intent.py`와 `backend/tests/test_intent.py` 이름 충돌

이번 점검 중 즉시 복구한 회귀:

1. `backend/app/agents/models/state.py`
   - `PlaceInfo` import 경로를 `output.py`에서 `place.py`로 수정
2. `backend/app/core/llm_factory.py`
   - 정의되지 않은 `TavilySearchResults` 타입 주석 제거
3. `frontend/src/hooks/common/useSpeechRecognition.ts`: SSR 환경에서 localStorage 접근 시 발생하는 ReferenceError 수정 (window 체크 추가)

### 3.2 프론트엔드

실행/검증 명령:

- `npm test -- --runInBand`
- `npm run build`

검증 결과:

- 테스트: 성공
  - `6 passed`, `12 tests passed`
- 프로덕션 빌드: 실패
  - `lightningcss.darwin-arm64.node` 누락

---

## 4. 현재 확인된 문제 목록

### 4.1 런타임 리스크

1. Pydantic V2 경고 다수
   - `class Config` 기반 스키마가 여러 곳에 남아 있음
   - 지금 당장 치명적이진 않지만 V3 전환 시 정리 필요

2. 테스트 중 `AsyncMock` 미대기 경고
   - 일부 비동기 mocking 패턴 정리 필요

---

## 5. 개선 우선순위

### 1순위

- 백엔드 실패 테스트 4건 복구
- `tmp/` 테스트 수집 제외 처리
- Tavily 검색 경로의 async/import 문제 정리

### 2순위

- 프론트 의존성 재설치 절차 정리
- 도커 기준 빌드/실행 절차를 README 또는 별도 운영 문서에 명확히 정리

### 3순위

- Pydantic V2 `ConfigDict` 전환
- `datetime.utcnow()` 제거
- 테스트 경고 정리

---

## 6. 실행 상태 결론

2026-03-14 기준으로 이 저장소는 다음 상태로 판단된다.

- 프론트 테스트는 통과한다.
- 백엔드는 핵심 로딩은 복구되었지만 전체 테스트는 아직 실패한다.
- 프론트 프로덕션 빌드는 현재 로컬 의존성 문제로 바로 통과하지 않는다.
- 따라서 "완전한 실행 안정 상태"라고 보기 어렵고, 최소한 백엔드 실패 테스트와 프론트 빌드 환경 문제를 먼저 정리해야 한다.

---

## 7. 권장 후속 작업

1. 백엔드 실패 테스트 4건을 우선 복구
2. `backend/tmp/`를 pytest 수집 대상에서 제외
3. 프론트 `node_modules` 재설치 또는 도커 빌드 기준 재검증
4. Tavily 검색 경로를 실제 호출 시나리오 기준으로 통합 테스트 추가
