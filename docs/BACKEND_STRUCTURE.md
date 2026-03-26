# Backend 디렉토리 구조 분석

> FastAPI + LangGraph 기반 백엔드 구조를 현재 코드 기준으로 정리한 문서

---

## 1. 전체 구조

```text
backend/
├── app/
├── alembic/
├── evaluation/
├── tests/
├── data/
├── main.py
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 2. 루트 파일 역할

- `main.py`
  - 패키지 레벨 실행 엔트리 포인트
- `Dockerfile`
  - 백엔드 컨테이너 빌드/실행 설정
- `pyproject.toml`
  - `uv` 기반 개발 설정
- `requirements.txt`
  - CI/Docker 설치 기준 의존성
- `alembic/`
  - DB 마이그레이션 스크립트
- `README.md`
  - 백엔드 실행 가이드

---

## 3. `app/` 구조

```text
app/
├── main.py
├── api/
├── agents/
├── core/
├── database/
├── models/
├── schemas/
├── scripts/
└── utils/
```

주의:

- 현재 `app/services/` 디렉토리는 없다.
- API/에이전트/검색/유틸 계층으로 분리되어 있으며, 서비스 계층 문서는 구버전 기준이다.

---

## 4. `app/main.py`

현재 백엔드 진입점은 다음 역할을 수행한다.

- FastAPI 앱 생성
- lifespan에서 `PlaceRetriever`, `LLMFactory` 워밍업
- 전역 예외 핸들러 등록
- CORS 허용 origin 및 optional regex 구성
- 업로드 정적 경로 마운트
  - `/static`
  - `/api/static`
- 라우터 등록
  - `auth`
  - `users`
  - `chat`
  - `prefer`
  - `common`
  - `explore`
  - `reservations`
  - `diaries`
  - `stt`
- ASGI 기반 요청 로깅 미들웨어 적용
- 헬스체크 엔드포인트 제공
  - `GET /api/healthz`

미등록 참고:

- `app/api/attractions.py`
- `app/api/restaurants.py`
- `app/api/hot_place.py`

위 파일은 저장소에 존재하지만 현재 `app/main.py`에서 `include_router()`로 등록되지는 않는다.

---

## 5. `app/api/`

현재 라우터 기준 주요 API 모듈은 다음과 같다.

- `auth.py`
  - Google OAuth 콜백, 토큰 refresh, 로그아웃, verify
- `users.py`
  - 내 정보 조회/수정, 프로필 이미지 초기화, 회원 비활성화
- `chat.py`
  - 채팅방 목록/생성/상세/삭제
  - 일반 응답
  - SSE 스트리밍 응답
  - 자동시작 스트리밍
  - 채팅방 북마크
  - 장소 북마크
  - 오늘 추천
  - trip context 업데이트
- `prefer.py`
  - 선호도 조회/수정
- `common.py`
  - 이미지 업로드
- `explore.py`
  - 랜덤 장소, 핫플, 음식점, 관광지, 카테고리 기반 탐색
- `reservations.py`
  - OCR 보조 + 예약 CRUD
- `diaries.py`
  - 여행 기록 CRUD
  - 장소 검색
  - 역지오코딩
- `stt.py`
  - STT 보정

---

## 6. `app/agents/`

LangGraph 기반 대화 플로우 영역이다.

- `graph.py`
  - 워크플로우 정의
  - `intent → planner/geocoder/executor_general`
  - `geocoder → retriever/executor`
  - `retriever → executor/retriever(web retry)/web_search`
- `grapy_route.py`
  - 의도/누락 정보/지오코딩 이후/검색 이후 라우팅
- `intent.py`
  - 의도 분석, 슬롯 추출, 입력 태그/요약 생성, 위치/날씨 초기 보강
- `planner.py`
  - 여행 일정 초안 생성, 누락 슬롯 판정
- `geocoder_node.py`
  - GPS 우선 anchor 결정
  - landmark 정규화
  - `pinned_places` 좌표 보강
- `retriever.py`
  - 일반 검색 / 일정형 검색
  - 후보 병합, 중복 제거, 다양성 선택
  - 재검색 카운트 관리
- `web_search_node.py`
  - 검색 결과 0건일 때 Naver Local Search 기반 fallback
- `executor.py`
  - 최종 답변 생성
  - 일반 대화 응답
  - 누락 정보 재질문 응답
  - 장소 본문-결과 정합성 검증
- `models/`
  - `state.py`: `TravelState`
  - `output.py`: intent/planner 출력 스키마
  - `place.py`: `PlaceInfo`
- `prompts/`
  - `prompts.py`
  - `executor_prompt.py`
  - `auto_start_prompt.py`

---

## 7. `app/core/`

공통 실행 코어 계층이다.

- `llm_factory.py`
  - OpenAI/HuggingFace LLM 인스턴스 캐시
- `llm_streaming.py`
  - 토큰 스트리밍 조립
  - visible delta 계산
- `retrieval/place.py`
  - Qdrant 기반 장소 검색
  - 텍스트/이미지/위치 기반 hybrid retrieval
  - 최종 거리 재검증
- `retrieval/place_score.py`
  - RRF, boost, reranker 점수 계산
- `retrieval/tavily_search.py`
  - 저장소에는 남아 있으나 현재 LangGraph 기본 fallback 경로는 아님

---

## 8. `app/database/`

- `connection.py`
  - SQLAlchemy engine/session 관리
- `checkpointer.py`
  - LangGraph 체크포인터 연결
- `create_db.py`
  - 초기 스키마 생성
- `insert_db.py`
  - 초기 데이터 적재
- `entrypoint.sh`
  - 컨테이너 시작 보조 스크립트

---

## 9. `app/models/` / `app/schemas/`

### `app/models/`

- SQLAlchemy ORM 모델 정의
- 사용자, 채팅, 예약, 다이어리, 핫플레이스 등 저장 구조 포함

### `app/schemas/`

- Pydantic 요청/응답 스키마
- 사용자, 채팅, 예약, 다이어리, 선호도, STT 응답 등 API 입출력 정의

---

## 10. `app/scripts/`

데이터 수집/전처리/보강 스크립트 영역이다.

```text
app/scripts/
├── collect/
├── preprocess/
├── enrich/
├── scheduler/
├── preprocess_data.py
└── qdrant_upsert.py
```

주요 역할:

- 원천 데이터 수집
  - `collect/visitseoul.py`
  - `collect/tourapi.py`
  - `collect/seoul_culture.py`
  - `collect/popply.py`
  - `collect/shopping.py`
- 전처리/병합
  - `preprocess/*.py`
  - `preprocess/merge.py`
  - `preprocess_data.py`
- LLM 보강
  - `enrich/generate_llm_text.py`
  - `enrich/generate_content_llm_text.py`
- 벡터 적재
  - `qdrant_upsert.py`

### `app/scripts/scheduler/`

```text
app/scripts/scheduler/
├── __init__.py
├── weekly_scheduler_job.py
├── cleanup_closed_places.py
├── cleanup_expired_contents.py
├── check_places_with_naver.py
└── sync_new_contents.py
```

현재 스케줄러 계층은 폐업/만료 콘텐츠 정리, 네이버 검증, 신규 콘텐츠 동기화를 주간 잡으로 묶는 구조다.

---

## 11. `evaluation/`

평가 스크립트와 공용 리포팅 모듈이 위치한다.

- `evaluate_retrieval.py`
- `evaluate_generation.py`
- `evaluate_recommendation.py`
- `evaluate_all.py`
- `evaluate_prepare_enriched.py`
- `evaluate_ragas.py`
- `common/`

문서 참조:

- 평가 절차: [EVALUATION.md](/Users/kim/SKN21-FINAL-2Team/docs/EVALUATION.md)

---

## 12. 문서 관리 메모

- 라우터 등록 변경 시 이 문서와 [agent_sequence_diagrams.md](/Users/kim/SKN21-FINAL-2Team/docs/agent_sequence_diagrams.md)를 함께 갱신
- 검색 fallback 경로가 바뀌면 [RETRIEVAL_PLACE.md](/Users/kim/SKN21-FINAL-2Team/docs/RETRIEVAL_PLACE.md), [llm_model_software.md](/Users/kim/SKN21-FINAL-2Team/docs/llm_model_software.md)도 같이 수정
