from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from enum import IntEnum
import logging


logger = logging.getLogger("api_logger")


class ErrorCode(IntEnum):
    """API 에러 코드(Enum + int 값)"""
    # Auth
    TOKEN_EXPIRED = 1001
    TOKEN_INVALID = 1002
    REFRESH_TOKEN_EXPIRED = 1003
    REFRESH_TOKEN_INVALID = 1004
    GOOGLE_AUTH_FAILED = 1005

    # User
    USER_NOT_FOUND = 2001

    # Validation
    VALIDATION_ERROR = 3001
    
    # Chat
    CHAT_ROOM_NOT_FOUND = 4001
    CHAT_ROOM_NOT_FOUND_OR_DENIED = 4002
    CHAT_MESSAGE_NOT_FOUND_OR_DENIED = 4003
    ROUTE_NOT_FOUND = 4004
    METHOD_NOT_ALLOWED = 4005

    # Server
    INTERNAL_ERROR = 5001


class AppException(Exception):
    """공통 API 예외 클래스"""

    def __init__(self, error_code: ErrorCode, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def app_exception_handler(request: Request, exc: AppException):
    """AppException을 JSON 응답으로 변환"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": int(exc.error_code),
            "message": exc.message,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 실패를 공통 JSON 응답으로 변환"""
    return JSONResponse(
        status_code=422,
        content={
            "error_code": int(ErrorCode.VALIDATION_ERROR),
            "message": "Validation error",
        },
    )


async def internal_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외를 공통 JSON 응답으로 변환"""
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": int(ErrorCode.INTERNAL_ERROR),
            "message": "Internal server error",
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Starlette HTTP 예외(404/405 등)를 공통 JSON 응답으로 변환"""
    status_code = exc.status_code
    if status_code == 404:
        error_code = ErrorCode.ROUTE_NOT_FOUND
        message = "Not found"
    elif status_code == 405:
        error_code = ErrorCode.METHOD_NOT_ALLOWED
        message = "Method not allowed"
    else:
        error_code = ErrorCode.VALIDATION_ERROR if 400 <= status_code < 500 else ErrorCode.INTERNAL_ERROR
        message = str(exc.detail) if exc.detail else "HTTP error"

    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": int(error_code),
            "message": message,
        },
    )
