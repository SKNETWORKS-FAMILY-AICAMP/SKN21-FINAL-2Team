from dotenv import load_dotenv
load_dotenv()
import os

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles             # 추가
import time
import logging
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from app.api import auth, users, chat, prefer, common, explore, reservations, diaries
# 모델 등록 (Base.metadata에 포함되도록 import)
from app.models import user, chat as chat_model, country, hot_place, reservation, diary
from app.core.retrieval.place import PlaceRetriever
from app.core.llm_factory import LLMFactory
from app.utils.error_handler import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    internal_exception_handler,
    http_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행될 로직
    print("[INFO] Starting up: Loading models...")
    try:
        # CLIP 모델 로드 (PlaceRetriever 초기화)
        PlaceRetriever.get_instance()
        
        # LLM 및 Tavily 인스턴스 초기화
        # 노드별 설정(temperature)에 맞춰 자주 쓰는 조합을 미리 워밍업
        LLMFactory.get_llm(temperature=0.0)  # intent/summarizer
        LLMFactory.get_llm(temperature=0.3)  # planner/missing
        LLMFactory.get_llm(temperature=0.5)  # executor
        LLMFactory.get_llm(temperature=0.7)  # executor
        LLMFactory.get_tavily()
        
        print("[INFO] All models loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load models during startup: {e}")
    
    yield
    # 서버 종료 시 실행될 로직
    print("[INFO] Shutting down...")

def _parse_csv_env(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_cors_settings() -> tuple[list[str], str | None]:
    # EC2/로컬 공통 기본값. 미설정 시에도 운영 도메인과 로컬 개발 도메인을 함께 허용한다.
    default_origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "https://triver-s.com",
        "https://www.triver-s.com",
    ]
    configured_origins = _parse_csv_env(os.environ.get("CORS_ORIGINS"))
    origins = list(dict.fromkeys(configured_origins or default_origins))
    origin_regex = os.environ.get("CORS_ORIGIN_REGEX", "").strip() or None
    return origins, origin_regex


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, internal_exception_handler)

origins, origin_regex = _build_cors_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 이미지 업로드 디렉토리 설정
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# /static 경로 유지 (기존 코드 호환)
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")
# /api/static 경로 추가 (nginx /api/ 블록을 통해 브라우저에서 접근)
app.mount("/api/static", StaticFiles(directory=UPLOAD_DIR), name="api_static")

from app.api import (
    auth, users, chat, prefer, common, explore,
    reservations, diaries
)

# Register Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(prefer.router)
app.include_router(common.router)
app.include_router(explore.router)
app.include_router(reservations.router)
app.include_router(diaries.router)

logger = logging.getLogger("api_logger")
logging.basicConfig(level=logging.INFO)

class RequestLoggingMiddleware:
    """SSE와 충돌하지 않도록 BaseHTTPMiddleware를 피하는 ASGI 로깅 미들웨어."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()
        method = scope.get("method", "")
        path = scope.get("path", "")
        status_code = 500
        origin = ""
        acr_method = ""
        acr_headers = ""
        for key, value in scope.get("headers", []):
            if key == b"origin":
                origin = value.decode("latin-1")
            elif key == b"access-control-request-method":
                acr_method = value.decode("latin-1")
            elif key == b"access-control-request-headers":
                acr_headers = value.decode("latin-1")

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.time() - start) * 1000
            if method == "OPTIONS" and origin:
                logger.info(
                    f"{method} {path} -> {status_code} ({duration_ms:.1f} ms) "
                    f"origin={origin} acr_method={acr_method or '-'} acr_headers={acr_headers or '-'}"
                )
            else:
                logger.info(f"{method} {path} -> {status_code} ({duration_ms:.1f} ms)")


app.add_middleware(RequestLoggingMiddleware)


@app.get("/")
def read_root():
    return {"message": "Hello World"}


@app.get("/api/healthz")
def healthz():
    return {"status": "ok"}
