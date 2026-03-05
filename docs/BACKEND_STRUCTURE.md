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
├── .env
├── .dockerignore
├── .python-version
├── README.md
├── app/
├── data/
├── evaluation/
└── tests/
```

---

## 2) 루트 파일

- `main.py`: 패키지 레벨 엔트리(placeholder)
- `Dockerfile`: 백엔드 컨테이너 빌드/실행 설정
- `requirements.txt`: 런타임/테스트 의존성 목록
- `pyproject.toml`: `uv` 기반 프로젝트 메타데이터
- `.env`: DB/API Key 등 환경 변수

---

## 3) `app/` 구조

```text
app/
├── main.py
├── api/
├── agents/
├── core/
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
- 예외 핸들러 등록
- CORS 설정
- 정적 파일 마운트
- 라우터 등록(`auth`, `users`, `chat`, `explore`, `prefer`, `hot_place`, `attractions`, `restaurants`, `common`)
- startup/lifespan에서 모델/DB 초기화

### 3-2. `app/api/`

- `auth.py`: Google OAuth 로그인, 토큰 갱신, 로그아웃
- `users.py`: 내 정보 조회/수정
- `chat.py`: 채팅방/메시지/북마크/스트리밍/SSE/자동시작
- `explore.py`: 여행지 탐색 API
- `prefer.py`: 취향 데이터 API
- `hot_place.py`: 인기 장소 API
- `attractions.py`: 관광지 검색 API
- `restaurants.py`: 음식점 검색 API
- `common.py`: 공통 응답/유틸 API

#### 채팅 API 핵심 엔드포인트

- `GET /api/chat/rooms`: 채팅방 목록
- `POST /api/chat/rooms`: 채팅방 생성
- `GET /api/chat/rooms/{room_id}`: 채팅방 상세
- `POST /api/chat/rooms/{room_id}/ask`: 일반 응답
- `POST /api/chat/rooms/{room_id}/ask/stream`: SSE 스트리밍 응답
- `POST /api/chat/rooms/{room_id}/autostart/stream`: 자동 시작 스트리밍

### 3-3. `app/agents/` (LangGraph)

- `graph.py`: 워크플로우 그래프 정의
- `intent.py`: 의도 분석 + 대화 요약(`summary_message`, `summary_query`)
- `planner.py`: 계획/질문 전략 수립
- `retriever.py`: RAG 후보 검색
- `executor.py`: 최종 답변 생성
- `grapy_route.py`: 노드 라우팅
- `models/`: state/output 타입

### 3-4. `app/database/`

- `connection.py`: SQLAlchemy engine/session (DBManager Singleton 적용)
- `checkpointer.py`: LangGraph 체크포인터
- `create_db.py`: 초기 스키마 생성
- `insert_db.py`: 초기 데이터 삽입

### 3-5. `app/models/`

- `user.py`: 사용자/선호/소셜 필드
- `chat.py`: `ChatRoom`, `ChatMessage`, `ChatPlace`
- `reservation.py`, `hot_place.py`, `country.py`
- `enums.py`: 공통 Enum (`human`, `ai` 등)
- `orm.py`: 베이스 모델

### 3-6. `app/schemas/`

- API 요청/응답 Pydantic 스키마
- 채팅/사용자/북마크/자동시작 모델 포함

### 3-7. `app/services/`

- `prompts.py`: 시스템 프롬프트
- `auto_start_prompt.py`: 자동시작 프롬프트 렌더링
- `vision.py`: 이미지 관련 처리

### 3-8. `app/retrieval/`

- `place.py`: Qdrant 기반 텍스트/이미지/위치 검색

### 3-9. `app/utils/`

- `config.py`: 전역 설정
- `security.py`: JWT/OAuth
- `error_handler.py`: 예외 처리
- `geocoder.py`: 주소/좌표 변환
- `llm_factory.py`: LLM/Tavily 인스턴스 관리

---

## 4) `data/` 구조

```text
data/
├── emotional/
├── llm_result/
├── prefer/
└── uploads/
```

- 원천/전처리/보강 데이터 및 사용자 업로드 저장 경로

---

## 5) `evaluation/` 구조

- `evaluate_rag.py`: end-to-end 평가
- `evaluate_retrieval.py`: 검색 품질 평가
- `evaluate_intent.py`: intent 품질 평가
- `evaluate_planner.py`: planner 품질 평가
- `evaluate_executor.py`: executor 품질 평가
- `evaluate_testdata.py`: 평가 데이터 보강 유틸
- `create_dataset.py`: Ragas TestsetGenerator 기반 합성 데이터셋 생성
- `rag_eval_data.json`: 평가 데이터셋
- `evaluation_report.csv`, `evaluation_summary.txt`: 리포트

---

## 6) `tests/` 구조

```text
tests/
├── conftest.py
├── test_auth.py
├── test_chat.py
├── test_chat_stream.py
└── test_users.py
```

- 인증/사용자/채팅/스트리밍 핵심 시나리오를 pytest로 검증

---

## 7) 실행 가이드

### Docker 우선

- `docker compose ps`
- `docker exec skn21-final-2team-backend-1 pytest tests/test_chat.py tests/test_chat_stream.py -q`

### 로컬(`uv`) 실행

- `uv sync`
- `uv run uvicorn app.main:app --reload`
- `uv run pytest`

---

## 8) 문서 관리 원칙

- 백엔드 구조 문서는 `docs/BACKEND_STRUCTURE.md` 단일 파일을 기준으로 관리
- 구조 변경 시 이 문서만 업데이트
- 평가 관련 운영/실행/해석 기준은 `docs/EVALUATION.md` 단일 파일로 관리
