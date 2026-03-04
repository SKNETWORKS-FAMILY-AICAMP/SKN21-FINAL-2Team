# Backend 디렉토리 구조 분석

> FastAPI 기반 한국 여행 추천 챗봇 백엔드 서버

---

## 📁 전체 디렉토리 구조

```
backend/
├── main.py                  # 패키지 진입점 (placeholder)
├── Dockerfile               # Docker 이미지 빌드 설정
├── requirements.txt         # pip 의존성 목록
├── pyproject.toml           # 프로젝트 메타데이터 (uv/PEP 517)
├── .dockerignore            # Docker 빌드 제외 파일 목록
├── .python-version          # Python 버전 고정 파일
├── README.md                # 프로젝트 설명
│
├── app/                     # 실제 FastAPI 애플리케이션 패키지
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 생성 및 라우터 등록
│   ├── api/                 # HTTP 엔드포인트 (라우터)
│   ├── core/                # 설정 및 보안 유틸리티
│   ├── database/            # DB 연결 및 스키마 초기화
│   ├── models/              # SQLAlchemy ORM 모델
│   ├── schemas/             # Pydantic 요청/응답 스키마
│   ├── services/            # 프롬프트 관리 및 기타 유틸리티 서비스
│   ├── retrieval/           # Qdrant 벡터 검색 로직
│   └── scripts/             # 데이터 전처리 및 Qdrant 초기 적재 스크립트
│
├── data/
│   └── visitkorea_data.json # 한국관광공사 관광지 원본 데이터
│
└── tests/                   # pytest 테스트 코드
    ├── conftest.py
    ├── test_auth.py
    ├── test_chat.py
    ├── test_chat_stream.py
    └── test_users.py
```

---

## 🗂️ 루트 파일

### `main.py`
패키지 레벨의 진입점 placeholder 파일입니다. 실제 서버 실행은 `app/main.py`를 통해 이루어집니다.

```python
def main():
    print("Hello from backend!")
```

---

### `Dockerfile`
Docker 컨테이너 이미지를 빌드하는 설정 파일입니다.

| 항목          | 내용                                              |
| ------------- | ------------------------------------------------- |
| 베이스 이미지 | `python:3.11-slim`                                |
| 작업 디렉토리 | `/app`                                            |
| 의존성 설치   | `requirements.txt` 기반 pip install               |
| 추가 패키지   | `git` (apt-get)                                   |
| 실행 포트     | `8000`                                            |
| 실행 명령     | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |

---

### `requirements.txt`
pip로 설치되는 의존성 목록입니다.

| 분류          | 라이브러리                                                    |
| ------------- | ------------------------------------------------------------- |
| 웹 프레임워크 | `fastapi`, `uvicorn`, `python-multipart`                      |
| 데이터 검증   | `pydantic`, `pydantic[email]`                                 |
| LLM           | `openai`, `langsmith`                                         |
| DB (MySQL)    | `pymysql`, `sqlalchemy`, `pydbml`                             |
| 인증          | `python-jose[cryptography]`, `passlib[bcrypt]`, `google-auth` |
| 벡터 DB       | `qdrant-client`, `sentence-transformers`                      |
| 이미지 처리   | `pillow`                                                      |
| 테스트        | `pytest`, `httpx`, `pytest-asyncio`                           |
| 기타          | `python-dotenv`, `tqdm`, `requests`                           |

---

### `pyproject.toml`
PEP 517 기반 프로젝트 메타데이터 파일입니다. `uv` 패키지 매니저 사용을 전제로 핵심 의존성을 명시합니다.

- Python 버전: `>=3.13`
- 핵심 의존성: `pillow`, `python-dotenv`, `qdrant-client`, `requests`, `sentence-transformers`

> ⚠️ `requirements.txt`와 일부 중복되나, `pyproject.toml`은 배포용 최소 의존성만 포함합니다.

---

## 📦 `app/` — FastAPI 애플리케이션

### `app/main.py`
FastAPI 앱의 핵심 진입점입니다.

**주요 역할:**
- `FastAPI()` 앱 인스턴스 생성
- **CORS 미들웨어** 설정 (프론트엔드 `localhost:3000` 허용)
- 세 개의 라우터 등록: `auth`, `users`, `chat`
- **HTTP 요청 로깅 미들웨어**: 메서드, 경로, 상태코드, 응답시간(ms) 기록
- `GET /` 헬스체크 엔드포인트

---

## 📁 `app/core/` — 핵심 설정 및 보안

### `app/core/config.py`
전역 설정 상수를 정의합니다.

| 상수                | 설명                                             |
| ------------------- | ------------------------------------------------ |
| `DEVICE`            | 추론 디바이스 자동 감지 (`cuda` → `mps` → `cpu`) |
| `VECTOR_SIZE`       | 임베딩 벡터 차원 수 (`512`)                      |
| `PLACES_COLLECTION` | Qdrant 장소 컬렉션 이름 (`"places"`)             |
| `PHOTOS_COLLECTION` | Qdrant 사진 컬렉션 이름 (`"photos"`)             |

---

### `app/core/security.py`
JWT 인증 및 Google OAuth 처리를 담당합니다.

**JWT 관련:**
| 함수                            | 설명                                                       |
| ------------------------------- | ---------------------------------------------------------- |
| `create_access_token(user_id)`  | 15분 만료 Access Token 생성 (HS256)                        |
| `create_refresh_token(user_id)` | 7일 만료 Refresh Token 생성                                |
| `get_current_user(token, db)`   | Access Token 검증 후 현재 사용자 반환 (FastAPI Dependency) |
| `verify_refresh_token(token)`   | Refresh Token 유효성 검증 후 이메일 반환                   |

**Google OAuth 관련:**
| 함수                            | 설명                                                        |
| ------------------------------- | ----------------------------------------------------------- |
| `verify_google_auth_code(code)` | Google Authorization Code를 토큰으로 교환하고 ID Token 검증 |

- `JWT_SECRET_KEY`: `.env`에서 로드, 없으면 랜덤 생성
- `GOOGLE_REDIRECT_URI`: `"postmessage"` (팝업 방식 OAuth)

---

## 📁 `app/api/` — HTTP 엔드포인트

### `app/api/auth.py`
인증 관련 API 라우터 (`/api/auth`)

| 엔드포인트                  | 메서드 | 설명                                                                                                              |
| --------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| `/api/auth/google/callback` | POST   | Google Auth Code로 로그인. 신규 사용자 자동 생성. Access/Refresh Token 발급. Refresh Token은 HttpOnly 쿠키에 저장 |
| `/api/auth/refresh`         | POST   | Refresh Token으로 새 Access Token 발급                                                                            |
| `/api/auth/logout`          | POST   | `refresh_token` 쿠키 삭제                                                                                         |

---

### `app/api/users.py`
사용자 정보 API 라우터 (`/api/users`)

| 엔드포인트      | 메서드 | 설명                                          |
| --------------- | ------ | --------------------------------------------- |
| `/api/users/me` | GET    | 현재 로그인 사용자 정보 조회                  |
| `/api/users/me` | PATCH  | 현재 사용자 정보 수정 (이름, 성별, 선호도 등) |

---

### `app/api/chat.py`
채팅 API 라우터 (`/api/chat`)

| 엔드포인트                                 | 메서드 | 설명                                                                                |
| ------------------------------------------ | ------ | ----------------------------------------------------------------------------------- |
| `/api/chat/rooms`                          | GET    | 내 채팅방 목록 조회 (최신순)                                                        |
| `/api/chat/rooms`                          | POST   | 새 채팅방 생성                                                                      |
| `/api/chat/rooms/{room_id}`                | GET    | 채팅방 상세 조회 (메시지 포함)                                                      |
| `/api/chat/messages`                       | POST   | 메시지 저장 (단순 저장, LLM 호출 없음)                                              |
| `/api/chat/messages/{message_id}/bookmark` | PATCH  | 메시지 북마크 토글                                                                  |
| `/api/chat/rooms/{room_id}/ask`            | POST   | **핵심 엔드포인트**: 사용자 메시지 저장 → LangGraph 실행 → AI 메시지 저장 (일괄 응답) |
| `/api/chat/rooms/{room_id}/ask/stream`     | POST   | **SSE 스트리밍**: 사용자 메시지 저장 → LangGraph `astream_events()` → 노드 진행 이벤트 + LLM 토큰 SSE 전송 → AI 메시지 저장 |

**`/ask/stream` SSE 스트리밍 엔드포인트:**
1. 채팅방 소유권 확인 & 사용자 메시지 DB 저장
2. LangGraph `astream_events()` 로 그래프 실행
3. 노드 진행 이벤트 전송: `{"step": "intent", "status": "start/done"}`
4. Intent 노드 종료 시 `summary_query`로 채팅방 제목 자동 업데이트 (기본값인 경우에만)
5. LLM 토큰 스트리밍: `{"token": "..."}`
6. AI 메시지 DB 저장 후 완료 이벤트: `{"done": true, "message_id": ..., "room_title": "..."}`

---

## 📁 `app/models/` — SQLAlchemy ORM 모델

### `app/models/orm.py`
모든 모델의 추상 베이스 클래스 `BaseModel`을 정의합니다. `app.database.connection.Base`를 상속합니다.

---

### `app/models/enums.py`
DB에서 사용하는 Enum 타입을 정의합니다.

| Enum         | 값                        |
| ------------ | ------------------------- |
| `GenderType` | `male`, `female`, `other` |
| `RoleType`   | `human`, `ai`             |

---

### `app/models/user.py`
`users` 테이블 ORM 모델입니다.

| 컬럼                                        | 설명                            |
| ------------------------------------------- | ------------------------------- |
| `id`                                        | PK (자동 증가)                  |
| `email`                                     | 이메일 (유니크)                 |
| `name`                                      | 이름                            |
| `gender`                                    | 성별 (`GenderType` Enum)        |
| `social_provider`                           | 소셜 로그인 제공자 (`"google"`) |
| `social_id`                                 | 소셜 고유 ID                    |
| `social_access_token`                       | Google Access Token             |
| `social_refresh_token`                      | Google Refresh Token            |
| `actor/movie/drama/celeb/variety_prefer_id` | 카테고리별 선호도 FK            |
| `with_yn`                                   | 동반자 여부                     |
| `dog_yn`                                    | 반려견 동반 여부                |
| `vegan_yn`                                  | 채식주의자 여부                 |
| `is_join`                                   | 회원가입 완료 여부              |
| `is_prefer`                                 | 선호도 설정 완료 여부           |

**관계:** `rooms` → `ChatRoom` (1:N)

---

### `app/models/chat.py`
채팅방과 메시지 ORM 모델입니다.

**`ChatRoom` (`chat_rooms` 테이블):**
| 컬럼         | 설명                   |
| ------------ | ---------------------- |
| `id`         | PK                     |
| `user_id`    | 소유자 FK (`users.id`) |
| `title`      | 채팅방 제목            |
| `created_at` | 생성 시각              |

**`ChatMessage` (`chat_messages` 테이블):**
| 컬럼          | 설명                               |
| ------------- | ---------------------------------- |
| `id`          | PK                                 |
| `room_id`     | 채팅방 FK                          |
| `message`     | 메시지 내용 (Text)                 |
| `role`        | 발화자 (`human` / `ai`)            |
| `latitude`    | 위도 (선택)                        |
| `longitude`   | 경도 (선택)                        |
| `image_path`  | 이미지 (LONGTEXT, Base64 또는 URL) |
| `bookmark_yn` | 북마크 여부                        |

---

### `app/models/prefer.py`
선호도 마스터 데이터 ORM 모델입니다 (`prefers` 테이블).

| 컬럼         | 설명                                                     |
| ------------ | -------------------------------------------------------- |
| `id`         | PK                                                       |
| `category`   | 카테고리 (`actor`, `movie`, `drama`, `celeb`, `variety`) |
| `type`       | 세부 타입                                                |
| `value`      | 선호도 값                                                |
| `image_path` | 대표 이미지 경로                                         |

---

## 📁 `app/schemas/` — Pydantic 스키마

### `app/schemas/user.py`
사용자 관련 요청/응답 스키마입니다.

| 스키마               | 용도                                       |
| -------------------- | ------------------------------------------ |
| `UserBase`           | 기본 사용자 필드                           |
| `UserUpdate`         | 사용자 정보 수정 요청 (모든 필드 Optional) |
| `UserResponse`       | 사용자 정보 응답                           |
| `Token`              | Access + Refresh Token 응답                |
| `TokenData`          | JWT 페이로드 내 데이터                     |
| `GoogleLoginRequest` | Google Auth Code 요청 (`code` 필드)        |
| `RefreshRequest`     | Refresh Token 갱신 요청                    |

---

### `app/schemas/chat.py`
채팅 관련 요청/응답 스키마입니다.

| 스키마                | 용도                                               |
| --------------------- | -------------------------------------------------- |
| `ChatMessageBase`     | 메시지 기본 필드 (message, 위경도, 이미지, 북마크) |
| `ChatMessageCreate`   | 메시지 생성 요청 (room_id, role 포함)              |
| `ChatMessageResponse` | 메시지 응답 (id, created_at 포함)                  |
| `ChatRoomBase`        | 채팅방 기본 필드 (title)                           |
| `ChatRoomCreate`      | 채팅방 생성 요청                                   |
| `ChatRoomResponse`    | 채팅방 응답 (messages 목록 포함)                   |

---

## 📁 `app/services/` — LLM 서비스

### `app/services/prompts.py`
GPT에게 전달하는 시스템 프롬프트를 정의합니다.

AI의 역할: **초개인화 한국 여행 에이전트**

**핵심 행동 원칙:**
1. **RAG 우선**: 제공된 Context Information을 최우선으로 사용
2. **초개인화**: 사용자 취향, 여행 목적, 대화 맥락 반영
3. **멀티모달**: 이미지 분석을 통한 유사 장소 추천
4. **실행 가능한 정보**: 장소 특징, 추천 이유, 방문 팁 포함
5. **주변 추천**: Context의 `Nearby Places` 정보 활용

응답 스타일: 한국어, 해요체, Markdown 형식

---

### `app/services/vision.py`
GPT-4o-mini를 사용하여 이미지의 정서적 특징 및 검색 키워드를 추출합니다.

**`describe_image(image_data)`**

- 입력: Base64 이미지 스트링 또는 URL
- 출력: 이미지에 대한 감정 키워드, 장소 특징, 검색 키워드 포함 텍스트

---

## 📁 `app/retrieval/` — 벡터 검색

### `app/retrieval/place.py`
Qdrant 벡터 DB에서 관광지를 검색하는 핵심 모듈입니다.

**`PlaceRetriever` 클래스 (싱글톤 패턴):**

| 메서드                                          | 설명                                                          |
| ----------------------------------------------- | ------------------------------------------------------------- |
| `search_text(query, limit)`                     | 텍스트 임베딩으로 `places` 컬렉션의 `text_vec` 검색           |
| `search_image(image_url, limit)`                | 이미지 임베딩으로 `photos` 컬렉션 검색 후 `place_id`로 그룹화 |
| `search_hybrid(query, image_url, limit, alpha)` | 텍스트+이미지 가중합 하이브리드 검색 (alpha: 텍스트 가중치)   |
| `search_nearby(lat, lng, limit, radius_km)`     | Haversine 공식으로 반경 내 장소 검색                          |
| `_haversine(lat1, lon1, lat2, lon2)`            | 두 좌표 간 거리(km) 계산                                      |

**임베딩 모델:** `clip-ViT-B-32` (텍스트/이미지 모두 512차원)

**`retrieval_place(message_in)` 함수:**
1. `search_hybrid()`로 상위 3개 장소 검색
2. 최상위 결과의 좌표 기준 반경 5km 내 주변 장소 추가 검색
3. 결과를 Markdown 형식 문자열로 포맷하여 반환 (LLM Context로 활용)

---

## 📁 `app/database/` — 데이터베이스

### `app/database/connection.py`
MySQL 연결 설정 및 SQLAlchemy 세션 관리를 담당합니다.

- `.env`에서 `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE` 로드
- `pool_pre_ping=True`: 연결 유효성 사전 확인
- `pool_recycle=3600`: 1시간마다 연결 재생성
- `get_db()`: FastAPI Dependency로 사용하는 DB 세션 제공 함수

---

### `app/database/create_db.py`
DBML 스키마 정의를 파싱하여 MySQL 테이블을 자동 생성하는 스크립트입니다.

**내장 DBML 스키마 정의 테이블:**
- `users`: 회원 정보
- `prefers`: 선호도 마스터
- `chat_rooms`: 채팅방
- `chat_messages`: 채팅 메시지
- `country`: 국가 코드

**`deploy_db_from_dbml()` 함수 처리 과정:**
1. DBML → SQL 파싱 (`PyDBML`)
2. PostgreSQL ENUM → MySQL ENUM 변환
3. 쌍따옴표 → MySQL 호환 형식 변환
4. `AUTOINCREMENT` → `AUTO_INCREMENT` 변환
5. `varchar` → `varchar(255)` 변환
6. MySQL 연결 후 SQL 실행 (재시도 5회)

---

### `app/database/insert_db.py`
DB 초기 데이터 삽입 스크립트 (내용 최소화, 별도 구현 예정).

---

## 📁 `app/scripts/` — 데이터 처리 스크립트

### `app/scripts/preprocess_data.py`
데이터 전처리 유틸리티 함수를 제공합니다.

| 함수                           | 설명                                      |
| ------------------------------ | ----------------------------------------- |
| `download_image(url, timeout)` | URL 또는 Base64 문자열에서 PIL Image 로드 |
| `location_to_latlng(location)` | 네이버 Geocoding API로 주소 → 위경도 변환 |

---

### `app/scripts/qdrant_setup.py`
Qdrant 벡터 DB 컬렉션 생성 및 데이터 적재 스크립트입니다.

**`QdrantClientDB` 클래스:**

| 메서드                                                  | 설명                                                          |
| ------------------------------------------------------- | ------------------------------------------------------------- |
| `ensure_collections()`                                  | `places`, `photos` 컬렉션 없으면 생성 (HNSW 인덱스 설정 포함) |
| `aggregate_vectors(vectors, top_k)`                     | 이미지 벡터 여러 개를 평균 내어 대표 벡터 생성 (L2 정규화)    |
| `add_place(place_id, description, image_urls, payload)` | 장소 1개를 텍스트+이미지 임베딩하여 Qdrant에 저장             |
| `ingest_data(file_path)`                                | JSON 파일을 읽어 전체 장소 데이터 일괄 적재                   |

**Qdrant 컬렉션 구조:**

| 컬렉션   | 벡터                                    | 설명                          |
| -------- | --------------------------------------- | ----------------------------- |
| `places` | `text_vec` (512d), `img_vec_agg` (512d) | 장소별 텍스트+대표이미지 벡터 |
| `photos` | 단일 벡터 (512d)                        | 장소별 개별 사진 벡터         |

---

## 📁 `data/`

### `data/visitkorea_data.json`
한국관광공사 데이터를 기반으로 수집한 관광지 정보 JSON 파일입니다.

- 파일 크기: 약 363KB
- 주요 필드: `id`, `name`, `주소`, `photo_urls` 등
- `qdrant_setup.py`의 `ingest_data()`가 이 파일을 읽어 Qdrant에 적재합니다.

---

## 📁 `tests/` — 테스트

### `tests/conftest.py`
pytest 공통 픽스처를 정의합니다.

- **테스트 DB**: SQLite In-Memory (`sqlite:///:memory:`) 사용
- `db` 픽스처: 테스트마다 테이블 생성 → 테스트 실행 → 테이블 삭제
- `client` 픽스처: FastAPI `TestClient` + DB 의존성 오버라이드

---

### `tests/test_auth.py`
인증 API 테스트입니다.

| 테스트                      | 설명                                             |
| --------------------------- | ------------------------------------------------ |
| `test_login_google_success` | Google 로그인 성공 시 토큰 반환 확인 (mock 사용) |
| `test_login_google_failure` | 잘못된 코드로 로그인 시 400 반환 확인            |
| `test_refresh_token`        | Refresh Token으로 새 Access Token 발급 확인      |

---

### `tests/test_chat.py`
채팅 API 테스트입니다.

| 테스트                      | 설명                                  |
| --------------------------- | ------------------------------------- |
| `test_create_session`       | 채팅방 생성 확인                      |
| `test_get_sessions`         | 채팅방 목록 조회 확인                 |
| `test_send_message_stream`  | 스트리밍 메시지 테스트 (미구현, pass) |
| `test_get_session_messages` | 채팅방 메시지 목록 조회 확인          |

---

### `tests/test_chat_stream.py`
SSE 스트리밍 엔드포인트 (`/ask/stream`) 자동 테스트입니다. `httpx.AsyncClient` + LLM/Graph Mock 사용.

| 테스트                            | 설명                                          |
| --------------------------------- | --------------------------------------------- |
| `test_sse_event_format`           | SSE 라인이 `data: {...}` 형식인지 확인        |
| `test_step_events_order`          | 노드 step 이벤트 순서 확인 (intent→retriever→executor) |
| `test_token_streaming`            | token 이벤트 1개 이상 수신 확인               |
| `test_done_event_with_message_id` | 마지막 이벤트에 done + message_id 포함 확인   |
| `test_ai_message_saved_to_db`     | 스트리밍 후 DB에 AI 메시지 저장 확인          |

---

### `tests/test_users.py`
사용자 API 테스트입니다.

| 테스트                | 설명                       |
| --------------------- | -------------------------- |
| `test_read_users_me`  | 현재 사용자 정보 조회 확인 |
| `test_update_user_me` | 사용자 정보 수정 확인      |

---

## 🔄 전체 요청 흐름 요약

```
[클라이언트]
    │
    ▼
[app/main.py] ← CORS, 로깅 미들웨어
    │
    ├─ /api/auth/*  → [api/auth.py] → [core/security.py] → Google OAuth / JWT
    ├─ /api/users/* → [api/users.py] → [models/user.py]
    └─ /api/chat/*  → [api/chat.py]
                           │
                           ├─ [retrieval/place.py] → Qdrant 벡터 검색
                           │       └─ [scripts/preprocess_data.py] (이미지 다운로드)
                           │
                           └─ [agents/graph.py] → LangGraph (Intent, Planner, Retriever, Executor)
                                   └─ [services/prompts.py] (시스템 프롬프트)
```

---

## 🗄️ 데이터베이스 구조 요약

```
MySQL (운영 데이터)
├── users          ← 회원 정보, Google OAuth 토큰, 선호도 FK
├── prefers        ← 선호도 마스터 (배우, 영화, 드라마 등)
├── chat_rooms     ← 채팅방 (user_id FK)
└── chat_messages  ← 메시지 (room_id FK, 위경도, 이미지, 북마크)

Qdrant (벡터 검색)
├── places         ← 장소별 text_vec + img_vec_agg (512d CLIP)
└── photos         ← 장소별 개별 사진 벡터 (512d CLIP)
```
