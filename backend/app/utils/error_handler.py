from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode:
    """API 에러 코드 상수"""
    # Auth
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    REFRESH_TOKEN_EXPIRED = "REFRESH_TOKEN_EXPIRED"
    REFRESH_TOKEN_INVALID = "REFRESH_TOKEN_INVALID"
    GOOGLE_AUTH_FAILED = "GOOGLE_AUTH_FAILED"

    # User
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Server
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    """공통 API 예외 클래스"""

    def __init__(self, error_code: str, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def app_exception_handler(request: Request, exc: AppException):
    """AppException을 JSON 응답으로 변환"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )
