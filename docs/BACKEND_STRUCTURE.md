# Backend 디렉토리 구조 분석

> FastAPI 기반 한국 여행 추천 챗봇 백엔드 서버

---

## 1) 전체 구조

```text
backend/
├── main.py
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── README.md
├── app/
├── data/
├── evaluation/
└── tests/
```

---

## 2) 루트 파일

- `main.py`: 패키지 레벨 엔트리 포인트
- `Dockerfile`: 백엔드 컨테이너 빌드/실행 설정
- `requirements.txt`: 런타임/평가/테스트 의존성 목록
- `pyproject.toml`: `uv` 기반 프로젝트 메타데이터
- `README.md`: 백엔드 실행/설정 가이드

---

## 3) `app/` 구조

```text
app/
├── main.py
├── api/
├── agents/
├── database/
├── models/
├── schemas/
├── services/
├── retrieval/
├── scripts/
└── utils/
```

### 3-1. `app/main.py`

- FastAPI 앱 생성
- lifespan에서 검색기/LLM/Tavily 워밍업
- 전역 예외 핸들러 등록
- CORS 설정
- 업로드 파일 정적 경로 마운트
- 라우터 등록(`auth`, `users`, `chat`, `prefer`, `common`, `explore`, `attractions`, `restaurants`, `reservations`, `hot_place`)
- HTTP 요청 단위 로깅 미들웨어 적용

### 3-2. `app/api/`

- `auth.py`: Google OAuth 로그인, 토큰 갱신, 로그아웃
- `users.py`: 내 정보 조회/수정
- `chat.py`: 채팅방/메시지/북마크/스트리밍/SSE/자동시작/오늘 추천
- `explore.py`: 여행지 탐색 API
- `prefer.py`: 취향 데이터 API
- `hot_place.py`: 인기 장소 API
- `attractions.py`: 관광지 검색 API
- `restaurants.py`: 음식점 검색 API
- `reservations.py`: 예약 API
- `common.py`: 공통 응답/유틸 API

#### 채팅 API 핵심 엔드포인트

- `GET /api/chat/rooms`: 채팅방 목록
- `POST /api/chat/rooms`: 채팅방 생성
- `GET /api/chat/rooms/{room_id}`: 채팅방 상세
- `POST /api/chat/rooms/{room_id}/ask`: 일반 응답
- `POST /api/chat/rooms/{room_id}/ask/stream`: SSE 스트리밍 응답
- `POST /api/chat/rooms/{room_id}/autostart/stream`: 자동 시작 스트리밍
- `GET /api/chat/recommendations/today`: 최근 대화 기반 추천 프롬프트 목록

#### 채팅방 제목 정책

- 자동 생성 제목(`새 채팅`, `새로운 여행 계획` 등)인 경우에만 덮어쓰기 가능
- 현재는 방 메시지 수가 `20`개 이하일 때까지 LLM이 생성한 `summary_title`로 제목 갱신 가능
- 제목 길이가 DB 제한을 넘으면 `_make_room_title()`로 축약 저장

### 3-3. `app/agents/` (LangGraph)

- `graph.py`: 워크플로우 그래프 정의
- `intent.py`: 의도 분석 + 대화 요약
- `planner.py`: 일정 초안 및 후속 질문 생성
- `retriever.py`: RAG 후보 검색 및 검색 스코프 선택
- `executor.py`: 최종 답변 생성, 네이버 지도 링크 포함, 후보가 없을 때 Tavily fallback 수행
- `grapy_route.py`: 노드 라우팅
- `models/state.py`: 그래프 상태 정의
- `models/output.py`: intent/planner 출력 스키마 정의

### 3-4. `app/database/`

- `connection.py`: SQLAlchemy engine/session 관리
- `checkpointer.py`: LangGraph 체크포인터 연결
- `create_db.py`: 초기 스키마 생성
- `insert_db.py`: 초기 데이터 삽입

### 3-5. `app/models/`

- `user.py`: 사용자/선호/소셜 필드
- `chat.py`: `ChatRoom`, `ChatMessage`, `ChatPlace`
- `reservation.py`, `hot_place.py`, `country.py`
- `enums.py`: 공통 Enum (`human`, `ai` 등)
- `orm.py`: 베이스 모델

### 3-6. `app/schemas/`

- API 요청/응답용 Pydantic 스키마
- 채팅/사용자/북마크/자동시작/예약 모델 포함

### 3-7. `app/services/`

- `prompts.py`: intent/planner/이미지 분석 프롬프트
- `executor_prompt.py`: executor 전용 프롬프트
- `auto_start_prompt.py`: 자동시작 메시지 렌더링
- `vision.py`: 이미지 처리 관련 서비스

### 3-8. `app/retrieval/`

- `place.py`: Qdrant 기반 텍스트/이미지/위치 검색
- 검색 스코프 정책
  - `place_only`: `places` 컬렉션만 검색
  - `photo_only`: `photos` 컬렉션만 검색
  - `auto`: 기존 하이브리드 전체 채널
- 성능 최적화 정책
  - BM25 입력 텍스트는 경량 포맷 사용
  - rerank 대상 수는 Retrieval 프로파일에서 상한 관리
  - BM25는 벡터 1차 후보 풀 내부에서만 계산
  - 벡터 점수가 충분하면 BM25를 조건부 스킵

### 3-9. `app/scripts/`

- 데이터 전처리, 팝업스토어 수집, LLM 보강, Qdrant 적재 스크립트 제공
- 대표 스크립트: `preprocess_data.py`, `preprocess_popup.py`, `enrich_llm.py`, `enrich_with_tavily.py`, `qdrant_setup.py`

### 3-10. `app/utils/`

- `config.py`: 전역 설정/프로파일
- `security.py`: JWT/OAuth 인증
- `error_handler.py`: 공통 예외 처리
- `geocoder.py`: 주소/좌표 변환
- `llm_factory.py`: LLM/Tavily 인스턴스 관리
- `common.py`: 공통 유틸

---

## 4) `data/` 구조

```text
data/
├── emotional/
├── llm_result/
├── preprocess_steps/
├── uploads/
└── 원천 json/jsonl 데이터
```

- 관광지/숙박/음식점/팝업스토어 원천 데이터와 전처리 산출물 관리
- `uploads/`에는 사용자 프로필/예약 이미지/핫플레이스 이미지 등 서비스 자산 저장

---

## 5) `evaluation/` 구조

- `evaluate_ragas.py`: 합성 데이터 생성 및 enriched CSV 생성
- `evaluate_prepare_enriched.py`: 평가용 enriched 컬럼 준비
- `evaluate_retrieval.py`: Retrieval/Rerank 평가
- `evaluate_recommendation.py`: Recommendation 평가
- `evaluate_generation.py`: Generation 평가
- `evaluate_all.py`: 단계별 평가 통합 실행
- `common/`: 입출력/지표/리포팅 공통 모듈
- `result/`: 단계별 리포트 및 요약 JSON/TXT 저장

---

## 6) `tests/` 구조

```text
tests/
├── conftest.py
├── test_auth.py
├── test_chat.py
├── test_chat_stream.py
├── test_graph_routing.py
├── test_retriever_selection.py
├── test_retriever_regression.py
├── test_place_rerank_fallback.py
├── test_executor_selected_id_validation.py
├── test_retrieval_profile_config.py
├── test_image_url_utils.py
├── test_evaluation_*.py
└── 보조 점검 스크립트(check_qdrant.py, debug_search.py)
```

- 인증/채팅/스트리밍/그래프 라우팅/검색 회귀/평가 스크립트까지 pytest 기반으로 검증

---

## 7) 실행 가이드

### Docker 우선

- `docker compose ps`
- `docker compose run --rm backend pytest -q`

### 로컬(`uv`) 실행

- `cd backend`
- `uv sync`
- `uv run uvicorn app.main:app --reload`
- `uv run pytest`

---

## 8) 문서 관리 원칙

- 백엔드 구조 변경은 `docs/BACKEND_STRUCTURE.md`에 반영
- 평가 절차/해석 기준은 `docs/EVALUATION.md`에서 단일 관리
- 채팅 플로우, 제목 정책, API 추가/삭제가 있으면 구조 문서 우선 갱신
