from dotenv import load_dotenv
load_dotenv()
import os                                               # 추가

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles             # 추가
import time
import logging
from app.api import auth, users, chat, prefer, common, explore
from app.api import hot_place as hot_place_api
# 모델 등록 (Base.metadata에 포함되도록 import)
from app.models import user, chat as chat_model, country, hot_place, reservation
from app.retrieval.place import PlaceRetriever
from app.utils.llm_factory import LLMFactory
from app.utils.error_handler import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    internal_exception_handler,
    http_exception_handler,
)
from app.database.connection import Base, get_engine


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

app = FastAPI(lifespan=lifespan)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, internal_exception_handler)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=get_engine())

# CORS 설정 (프론트엔드 3000번 포트 허용)
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    attractions, restaurants, hot_place as hot_place_api
)

# Register Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(prefer.router)
app.include_router(common.router)
app.include_router(explore.router)
app.include_router(attractions.router)
app.include_router(restaurants.router)
app.include_router(hot_place_api.router)

logger = logging.getLogger("api_logger")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f} ms)")
    return response


@app.get("/")
def read_root():
    return {"message": "Hello World"}

# 실행 명령어: uvicorn app.main:app --reload
