# Error Handler 분석

## 1. 개요

현재 백엔드의 공통 에러 처리는 `AppException` + 전역 예외 핸들러(`app_exception_handler`) 조합으로 구성되어 있습니다.

- 예외 정의: `backend/app/utils/error_handler.py`
- 전역 등록: `backend/app/main.py`
- 주요 사용: `backend/app/api/auth.py`, `backend/app/utils/security.py`

핵심 목표는 서비스에서 발생한 예외를 **일관된 JSON 스키마**로 응답하는 것입니다.

---

## 2. 구성 요소 분석

### 2.1 `ErrorCode` Enum 클래스
파일: `backend/app/utils/error_handler.py:5`

정의된 코드:

- `TOKEN_EXPIRED = 1001`
- `TOKEN_INVALID = 1002`
- `REFRESH_TOKEN_EXPIRED = 1003`
- `REFRESH_TOKEN_INVALID = 1004`
- `GOOGLE_AUTH_FAILED = 1005`
- `USER_NOT_FOUND = 2001`
- `VALIDATION_ERROR = 3001`
- `CHAT_ROOM_NOT_FOUND = 4001`
- `CHAT_ROOM_NOT_FOUND_OR_DENIED = 4002`
- `CHAT_MESSAGE_NOT_FOUND_OR_DENIED = 4003`
- `ROUTE_NOT_FOUND = 4004`
- `METHOD_NOT_ALLOWED = 4005`
- `INTERNAL_ERROR = 5001`

특징:

- `IntEnum` 기반으로 타입 안정성이 개선되었습니다.
- API 응답 `error_code`가 숫자 코드로 고정됩니다.

### 2.2 `AppException`
파일: `backend/app/utils/error_handler.py:24`

필드:

- `error_code: str`
- `message: str`
- `status_code: int = 400`

특징:

- 비즈니스 예외를 표현하기 위한 공통 타입입니다.
- HTTP 상태 코드와 도메인 에러 코드를 함께 전달할 수 있습니다.

### 2.3 `app_exception_handler`
파일: `backend/app/utils/error_handler.py:34`

응답 형태:

```json
{
  "error_code": 1002,
  "message": "Invalid access token"
}
```

특징:

- `AppException`을 `JSONResponse`로 변환합니다.
- 응답 바디 구조가 고정되어 프론트엔드 처리 일관성이 높습니다.

### 2.4 추가 전역 핸들러
파일: `backend/app/utils/error_handler.py`

- `validation_exception_handler`: `RequestValidationError`를 `VALIDATION_ERROR(3001)`로 변환 (422)
- `http_exception_handler`: Starlette `HTTPException`(404/405 등)을 공통 포맷으로 변환
- `internal_exception_handler`: 처리되지 않은 예외를 `INTERNAL_ERROR(5001)`로 변환 (500)

### 2.5 FastAPI 앱 등록
파일: `backend/app/main.py:38`

```python
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, internal_exception_handler)
```

의미:

- 애플리케이션 전역에서 `AppException`/검증 에러/미처리 예외에 대해 동일한 응답 포맷을 강제합니다.
- 애플리케이션 전역에서 `AppException`/검증 에러/HTTP 예외/미처리 예외에 대해 동일한 응답 포맷을 강제합니다.

---

## 3. 실제 에러 발생 흐름

### 3.1 인증/인가 계층 (`security.py`)
파일: `backend/app/utils/security.py`

주요 발생 지점:

- 토큰 `sub` 누락 → `TOKEN_INVALID` (401)
- access 타입 불일치 → `TOKEN_INVALID` (401)
- access 만료 → `TOKEN_EXPIRED` (401)
- access 위변조/파싱 실패 → `TOKEN_INVALID` (401)
- 사용자 미존재 → `USER_NOT_FOUND` (401)
- refresh 타입 불일치 → `REFRESH_TOKEN_INVALID` (401)
- refresh 만료 → `REFRESH_TOKEN_EXPIRED` (401)
- refresh 위변조/파싱 실패 → `REFRESH_TOKEN_INVALID` (401)

흐름 요약:

1. `get_current_user()` / `verify_refresh_token()` 에서 `AppException` 발생
2. FastAPI 전역 핸들러가 예외를 수신
3. `status_code + {error_code, message}` JSON으로 응답

### 3.2 인증 API (`auth.py`)
파일: `backend/app/api/auth.py`

주요 발생 지점:

- Google 인증 코드 교환 실패 → `GOOGLE_AUTH_FAILED` (400)
- refresh 토큰 누락 → `REFRESH_TOKEN_INVALID` (401)
- refresh 검증 후 사용자 미존재 → `USER_NOT_FOUND` (401)

---

## 4. 현재 구조의 장점

- 인증 관련 에러가 `AppException`으로 비교적 잘 통일되어 있음
- 프론트엔드가 `error_code` 기준 분기 처리 가능
- FastAPI 전역 등록으로 중복 응답 생성 코드 감소

---

## 5. 확인된 한계/리스크

### 5.1 포맷 통일 상태
현재 `backend/app` 내 비즈니스 예외는 `AppException` 기반으로 통일되어, 실패 응답 포맷 일관성이 개선되었습니다.

잔여 리스크:

- 401/403처럼 FastAPI/Starlette 내부에서 발생하는 예외 메시지는 상황별로 내용이 달라질 수 있음 (포맷은 통일됨)

### 5.2 미사용/미구현 코드
- `ErrorCode.VALIDATION_ERROR`, `ErrorCode.INTERNAL_ERROR`는 정의돼 있지만 현재 공통 핸들러에서 별도 활용 흐름이 없음
- `RequestValidationError`, 일반 `Exception`에 대한 커스텀 핸들러 부재

영향:

- Pydantic 검증 실패 시 기본 FastAPI 포맷으로 응답
- 서버 내부 예외 발생 시 도메인 표준 포맷 보장이 약함

### 5.3 스택/추적 정보 미포함
현재 응답은 `error_code`, `message`만 포함합니다.

영향:

- 운영 환경에서 문제 추적 시 요청 단위 `trace_id`가 없어 상관관계 분석이 어려움

---

## 6. 개선 권장사항

1. `error_code` 번호 정책(도메인별 범위)을 별도 문서로 고정해 장기 운영 시 충돌 방지
2. 아래 전역 핸들러 추가 검토
   - `RequestValidationError` → `VALIDATION_ERROR`
   - `Exception` → `INTERNAL_ERROR` (메시지는 일반화)
3. 에러 응답 표준 확장
   - `timestamp`, `path`, `trace_id` 필드 추가
4. `ErrorCode` 번호 체계를 문서화해 코드 충돌 방지
5. 인증/채팅/기타 도메인별 에러 코드 네이밍 규칙 문서화

---

## 7. 정리

현재 Error Handler는 인증 영역에서 효과적으로 동작하며, `AppException`을 통한 표준화 기반이 이미 갖춰져 있습니다.  
다만 프로젝트 전체 관점에서는 `HTTPException`과 혼용되어 실패 응답 스키마가 일관되지 않으므로, 전역 예외 정책을 확장해 단일 포맷으로 통합하는 것이 다음 단계로 적절합니다.
