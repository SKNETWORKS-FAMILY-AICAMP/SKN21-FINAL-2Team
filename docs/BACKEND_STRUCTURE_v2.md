# Backend 디렉토리 구조 분석 (v2)

> FastAPI 기반 한국 여행 추천 챗봇 백엔드 서버

---

## 📁 전체 디렉토리 구조

```
backend/
├── main.py                  # 패키지 진입점 (placeholder)
├── Dockerfile               # Docker 이미지 빌드 설정
├── requirements.txt         # pip 의존성 목록
├── pyproject.toml           # 프로젝트 메타데이터 (uv/PEP 517)
├── .env                     # 환경 변수 설정 파일 (DB, API Key 등)
├── .dockerignore            # Docker 빌드 제외 파일 목록
├── .python-version          # Python 버전 고정 파일
├── README.md                # 프로젝트 설명
│
├── app/                     # 실제 FastAPI 애플리케이션 패키지
│   ├── main.py              # FastAPI 앱 생성 및 라우터 등록
│   ├── api/                 # HTTP 엔드포인트 (라우터)
│   ├── agents/              # LangGraph 기반 에이전트 워크플로우
│   ├── core/                # 설정 및 보안 유틸리티
│   ├── database/            # DB 연결, 스키마 초기화 및 체크포인터
│   ├── models/              # SQLAlchemy ORM 모델
│   ├── schemas/             # Pydantic 요청/응답 스키마
│   ├── services/            # LLM 호출 및 프롬프트 관리
│   ├── retrieval/           # Qdrant 벡터 검색 로직
│   ├── scripts/             # 데이터 전처리 및 Qdrant 초기 적재 스크립트
│   └── utils/               # 공통 유틸리티 (에러 핸들러, 지오코더 등)
│
├── data/                    # 원본 데이터 스토리지
│   └── visitkorea_data.json # 한국관광공사 관광지 원본 데이터
│
├── tests/                   # pytest 테스트 코드
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_chat.py
│   ├── test_chat_stream.py
│   └── test_users.py
│
└── uploads/                 # 업로드된 파일 저장 디렉토리
```

---

## 🗂️ 루트 파일

### `main.py`
패키지 레벨의 진입점 placeholder 파일입니다. 실제 서버 실행은 `app/main.py`를 통해 이루어집니다.

### `Dockerfile`
Docker 컨테이너 이미지를 빌드하는 설정 파일입니다. Python 3.11-slim 베이스 이미지를 사용하며, 8000 포트에서 Uvicorn 서버를 실행합니다.

### `requirements.txt`
pip로 설치되는 의존성 목록입니다. FastAPI, SQLAlchemy, OpenAI, Qdrant Client, LangGraph 등 핵심 라이브러리가 포함되어 있습니다.

### `.env`
데이터베이스 접속 정보(MySQL, Qdrant) 및 외부 API 키(OpenAI, Google OAuth, Naver Geocode) 등 보안이 필요한 설정을 관리합니다.

---

## 📦 `app/` — FastAPI 애플리케이션

### `app/main.py`
FastAPI 앱의 핵심 진입점입니다.
- **라우터 등록**: `auth`, `users`, `chat`, `explore`, `prefer`, `hot_place` 등의 라우터를 통합합니다.
- **미들웨어**: CORS 설정 및 HTTP 요청/응답 로깅을 처리합니다.
- **생명주기 이벤트**: 시작 시 DB 연결 확인 등 초기화 작업을 수행합니다.

---

## 📁 `app/agents/` — LangGraph 에이전트

사용자의 질문을 분석하고 적절한 도구를 사용하여 응답을 생성하는 지능형 에이전트 로직이 위치합니다.

| 파일             | 설명                                                  |
| ---------------- | ----------------------------------------------------- |
| `graph.py`       | 에이전트의 워크플로우(상태, 노드, 엣지) 정의          |
| `intent.py`      | 사용자 의도 파악 및 쿼리 정제                         |
| `planner.py`     | 검색된 정보를 기반으로 답변 전략 수립                 |
| `retriever.py`   | RAG(Qdrant) 및 위치 기반 정보 검색 실행               |
| `executor.py`    | 최종 답변 생성 및 후처리                              |
| `grapy_route.py` | API와 LangGraph 간의 인터페이스 및 라우팅             |

---

## 📁 `app/api/` — HTTP 엔드포인트

| 파일           | 설명                                                                 |
| -------------- | -------------------------------------------------------------------- |
| `auth.py`      | Google OAuth 로그인, 토큰 갱신, 로그아웃                             |
| `chat.py`      | 채팅방 관리 및 메시지 전송 (스트리밍 포함)                           |
| `users.py`     | 내 정보 조회 및 선호도 수정                                          |
| `explore.py`   | 한국 여행지 탐색 및 추천 API                                         |
| `prefer.py`    | 사용자 취향(배우, 영화 등) 데이터 조회                               |
| `hot_place.py` | 실시간 인기 장소 정보 제공                                           |
| `common.py`    | 공통 응답 처리 및 유틸리티 API                                       |

---

## 📁 `app/utils/` — 공통 유틸리티

시스템 전반에서 사용되는 헬퍼 함수 및 설정 모듈입니다.

| 파일               | 설명                                              |
| ------------------ | ------------------------------------------------- |
| `config.py`        | Pydantic Settings를 활용한 전역 설정 로딩         |
| `security.py`      | JWT 발급/검증 및 암호화 관련 로직                 |
| `error_handler.py` | 커스텀 예외 정의 및 글로벌 에러 처리              |
| `geocoder.py`      | Naver API 등을 이용한 주소-좌표 변환              |
| `llm_factory.py`   | OpenAI 모델 인스턴스 생성 및 설정 관리            |

---

## 📁 `app/models/` — DB ORM 모델

| 파일             | 설명                                          |
| ---------------- | --------------------------------------------- |
| `user.py`        | 사용자 정보, 소셜 로그인 정보, 개인 취향 필드 |
| `chat.py`        | 채팅방(`ChatRoom`) 및 메시지(`ChatMessage`)   |
| `reservation.py` | 여행지 예약 관련 정보 (예정)                  |
| `hot_place.py`   | 인기 여행지 데이터 모델                       |
| `country.py`     | 국가 코드 정보                                |
| `enums.py`       | 성별, 역할 등 공통 Enum 정의                  |

---

## 📁 `app/database/` — 데이터베이스 연동

- `connection.py`: SQLAlchemy 엔진 생성 및 세션 관리(`get_db`)
- `create_db.py`: DBML/SQL 파일을 읽어 초기 테이블 스키마 생성
- `insert_db.py`: 기초 마스터 데이터(선호도 목록 등) 삽입
- `checkpointer.py`: LangGraph 에이전트의 대화 상태 보존을 위한 체크포인터 (MySQL 연동)

---

## 📁 `app/services/` — 비즈니스 로직 및 LLM

- `llm.py`: GPT 모델 직접 호출 및 토큰 관리
- `vision.py`: 멀티모달(이미지 분석) 기능 처리
- `prompts.py`: 페르소나와 작업별 시스템 프롬프트 관리

---

## 📁 `app/retrieval/` — 벡터 검색 (RAG)

- `place.py`: QdrantClient를 이용한 하이브리드(텍스트+이미지), 위치 기반(Geo) 검색 모듈

---

## 📁 `app/scripts/` — 데이터 인프라

- `qdrant_setup.py`: Qdrant 컬렉션 생성 및 인덱스 설정 스크립트
- `preprocess_data.py`: 원본 데이터 클렌징 및 임베딩 준비
- `enrich_llm.py` / `enrich_with_tavily.py`: LLM 및 검색 서비스를 활용한 데이터 보강

---

## 📁 `uploads/`
사용자가 챗봇에 전송한 이미지 또는 시스템에서 생성한 임시 파일들이 저장되는 경로입니다.
