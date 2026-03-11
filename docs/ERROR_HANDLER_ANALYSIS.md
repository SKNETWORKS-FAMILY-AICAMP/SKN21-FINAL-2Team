# Error Handler 분석

## 1) 개요

현재 백엔드의 공통 에러 처리는 `AppException`과 전역 예외 핸들러 조합으로 구성되어 있습니다.

- 예외 정의: `backend/app/utils/error_handler.py`
- 전역 등록: `backend/app/main.py`

핵심 목표는 서비스에서 발생한 예외를 일관된 JSON 스키마로 반환하는 것입니다.

응답 기본 형식:

```json
{
  "error_code": 1002,
  "message": "Invalid access token"
}
```

---

## 2) 구성 요소

### 2.1 `ErrorCode`

주요 범주:

- 인증: `1001`~`1005`
- 사용자: `2001`
- 검증: `3001`
- 채팅/라우팅: `4001`~`4005`
- 서버: `5001`

현재 정의된 핵심 코드:

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

### 2.2 `AppException`

- 비즈니스 예외를 위한 공통 타입
- `error_code`, `message`, `status_code`를 함께 전달

### 2.3 전역 핸들러

현재 구현된 핸들러:

- `app_exception_handler`
  - `AppException`을 공통 포맷으로 변환
- `validation_exception_handler`
  - `RequestValidationError`를 `422 + VALIDATION_ERROR`로 변환
- `http_exception_handler`
  - `404`는 `ROUTE_NOT_FOUND`
  - `405`는 `METHOD_NOT_ALLOWED`
  - 그 외 4xx는 `VALIDATION_ERROR`
  - 5xx는 `INTERNAL_ERROR`
- `internal_exception_handler`
  - 미처리 예외를 `500 + INTERNAL_ERROR`로 변환
  - 서버 로그에는 `logger.exception(...)`으로 stack trace를 남김

---

## 3) 앱 등록 현황

`backend/app/main.py`에서 아래 핸들러가 모두 등록되어 있습니다.

- `AppException`
- `RequestValidationError`
- `StarletteHTTPException`
- `Exception`

즉, 현재는 문서상 권고 수준이 아니라 실제로 전역 예외 정책이 적용된 상태입니다.

---

## 4) 실제 동작 흐름

### 4.1 인증/인가 계층

`backend/app/utils/security.py`에서 토큰 검증 실패, 사용자 미존재 등을 `AppException`으로 발생시킵니다.

대표 사례:

- access 만료 → `TOKEN_EXPIRED`
- access 위변조/파싱 실패 → `TOKEN_INVALID`
- refresh 만료 → `REFRESH_TOKEN_EXPIRED`
- refresh 위변조/타입 오류 → `REFRESH_TOKEN_INVALID`
- 사용자 미존재 → `USER_NOT_FOUND`

### 4.2 요청 검증 실패

- Pydantic/FastAPI 검증 오류는 `RequestValidationError`로 수집
- 응답은 `422`와 `VALIDATION_ERROR(3001)`로 통일

### 4.3 라우트/메서드 오류

- 없는 경로 → `404 + ROUTE_NOT_FOUND`
- 허용되지 않은 메서드 → `405 + METHOD_NOT_ALLOWED`

### 4.4 미처리 서버 오류

- 예상하지 못한 예외는 `500 + INTERNAL_ERROR`
- 외부 노출 메시지는 일반화되고, 상세 stack trace는 로그에 남음

---

## 5) 장점

- 비즈니스 예외와 프레임워크 예외 모두 공통 JSON 포맷으로 응답
- 프론트엔드는 `error_code` 기준 분기 처리가 가능
- 미처리 예외도 `5001`로 표준화되어 운영 시 분류가 쉬움
- 서버 로그에는 예외 stack trace가 남아 디버깅이 가능

---

## 6) 현재 한계와 리스크

### 6.1 상세 검증 정보 미포함

- 검증 오류 응답은 `"Validation error"`로 고정되어 있음
- 어떤 필드가 실패했는지 응답 바디만으로는 바로 확인하기 어려움

### 6.2 추적 메타데이터 부재

- `trace_id`, `path`, `timestamp` 같은 운영 추적 정보는 아직 없음
- 로그와 클라이언트 오류를 1:1로 연결하기 어렵다

### 6.3 도메인별 코드 확장 규칙 문서화 부족

- 현재 범주는 암묵적으로 나뉘어 있지만, 신규 에러 코드 추가 규칙이 별도 문서로 고정되어 있지는 않음

---

## 7) 개선 권장사항

1. 검증 오류 응답에 실패 필드 요약을 포함할지 결정
2. `trace_id`, `path`, `timestamp` 필드 추가 검토
3. 도메인별 에러 코드 범위를 별도 문서로 명시
4. 주요 API에서 사용하는 `AppException` 사례를 운영 문서에 연결

---

## 8) 정리

현재 Error Handler는 인증 영역뿐 아니라 검증 오류, 라우팅 오류, 미처리 예외까지 공통 포맷으로 통합되어 있습니다. 과거 문서 기준의 미구현 상태는 해소되었고, 이제 남은 과제는 응답 상세도와 운영 추적성을 높이는 방향입니다.
