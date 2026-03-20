# Backend 디렉토리 구조 분석

> FastAPI + LangGraph 기반 백엔드 구조와 현재 점검 시 유의사항을 정리한 문서

---

## 1. 전체 구조

```text
backend/
├── app/
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
  - 패키지 레벨 엔트리 포인트
- `Dockerfile`
  - 백엔드 컨테이너 빌드/실행 설정
- `pyproject.toml`
  - `uv` 기반 파이썬 프로젝트 설정
- `requirements.txt`
  - 도커/런타임 의존성 설치 기준
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
├── services/
└── utils/
```

---

## 4. `app/main.py`

현재 백엔드 진입점은 다음 역할을 수행한다.

- FastAPI 앱 생성
- lifespan에서 `PlaceRetriever`, `LLMFactory` 워밍업
- 전역 예외 핸들러 등록
- CORS 허용 origin 구성
- `/static`, `/api/static` 업로드 정적 경로 마운트
- 라우터 등록
  - `auth`
  - `users`
  - `chat`
  - `prefer`
  - `common`
  - `explore`
  - `reservations`
  - `diaries`
- 요청 로깅 미들웨어 적용
- 헬스체크 엔드포인트 제공
  - `GET /api/healthz`

---

## 5. `app/api/`

주요 API 모듈은 다음과 같다.

- `auth.py`
  - Google OAuth 콜백, 토큰 refresh, 로그아웃, verify
- `users.py`
  - 내 정보 조회/수정, 프로필 이미지 초기화, 회원 비활성화
- `chat.py`
  - 채팅방 목록/생성/상세
  - 일반 응답
  - SSE 스트리밍 응답
  - 자동시작 스트리밍
  - 북마크 및 오늘 추천
- `prefer.py`
  - 선호도 조회/수정
- `explore.py`
  - 랜덤 장소, 핫플, 음식점, 관광지, 카테고리 기반 탐색
- `reservations.py`
  - 예약 CRUD
- `diaries.py`
  - 여행 기록 CRUD
  - 장소 검색
  - 역지오코딩
- `common.py`
  - 공통 응답 및 보조 API

---

## 6. `app/agents/`

LangGraph 기반 대화 플로우 영역이다.

- `graph.py`
  - 워크플로우 정의
- `grapy_route.py`
  - 노드 라우팅
- `intent.py`
  - 의도 분석, 슬롯 추출, 대화 요약
- `planner.py`
  - 여행 일정 초안 및 후속 질문 생성
- `retriever.py`
  - 후보 검색 및 후보군 정리
- `executor.py`
  - 최종 응답 생성
  - 선택된 장소 정보 구성
- `models/`
  - `output.py`: intent/planner 출력 스키마
  - `state.py`: 그래프 상태
  - `place.py`: `PlaceInfo`
  - `tavily_search.py`: Tavily 추출 스키마
- `prompts/`
  - `prompts.py`
  - `executor_prompt.py`
  - `auto_start_prompt.py`

---

## 7. `app/core/`

공통 실행 코어 계층이다.

- `llm_factory.py`
  - LLM 인스턴스 캐시/재사용
- `llm_streaming.py`
  - 토큰 스트리밍 조립
  - visible delta 계산
- `retrieval/place.py`
  - Qdrant 기반 장소 검색
  - 텍스트/이미지/위치 기반 검색
- `retrieval/place_score.py`
  - 후보 점수 계산 관련 로직
- `retrieval/tavily_search.py`
  - 웹 검색 기반 보조 장소 추출 경로
- `utils/geocoder.py`
  - 네이버 geocode / reverse geocode / local search 공통 클라이언트
  - `httpx.AsyncClient` 기반 비동기 호출 사용

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
- `ensure_database.py`
  - MySQL 기동 대기 후 DB 존재 보장
  - 필요 시 애플리케이션 DB와 권한 생성
- `entrypoint.sh`
  - 컨테이너 시작 전 DB 보장 및 Alembic 마이그레이션 수행

---

## 9. `app/models/` / `app/schemas/`

### `app/models/`

- SQLAlchemy ORM 모델 정의
- 사용자, 채팅, 예약, 국가, 핫플레이스, 다이어리 포함

### `app/schemas/`

- Pydantic 요청/응답 스키마
- 사용자, 채팅, 예약, 다이어리, 선호도 등 API 입출력 정의

---

## 10. `app/scripts/`

데이터 수집/전처리/보강 스크립트 영역이다.

- 관광지/음식점/숙박 데이터 정리
- 팝업스토어 수집
- LLM/Tavily 기반 보강
- Qdrant 적재
- 네이버 장소 검증 스크립트

---

## 11. `evaluation/`

평가 파이프라인이 별도 폴더로 분리되어 있다.

- `evaluate_prepare_enriched.py`
- `evaluate_retrieval.py`
- `evaluate_recommendation.py`
- `evaluate_generation.py`
- `evaluate_all.py`
- 평가 입력 CSV 및 결과 요약 파일

---

## 12. `tests/`

현재 테스트는 다음 범주를 포함한다.

- API/헬스체크
- 채팅 및 스트리밍
- intent/retrieval/executor 회귀
- place id / image url / address 토큰 유틸
- evaluation 계열 스크립트

실행 결과나 현재 실패 항목은 [PROJECT_ANALYSIS.md](/Users/kim/SKN21-FINAL-2Team/docs/PROJECT_ANALYSIS.md)에서만 관리한다.

---

## 13. 문서 관리 메모

- 구조 변경 시 `agents/models`, `core/retrieval`, `api` 라우터 목록부터 우선 갱신
- 테스트 문서와 구조 문서를 분리해 관리
- 실행 상태 요약은 `docs/PROJECT_ANALYSIS.md`를 기준으로 최신화
