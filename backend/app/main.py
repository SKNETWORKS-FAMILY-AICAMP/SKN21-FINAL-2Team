from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from app.api import auth, users, chat, prefer
from app.retrieval.place import PlaceRetriever
from app.utils.llm_factory import LLMFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행될 로직
    print("[INFO] Starting up: Loading models...")
    try:
        # CLIP 모델 로드 (PlaceRetriever 초기화)
        PlaceRetriever.get_instance()
        
        # LLM 및 Tavily 인스턴스 초기화
        LLMFactory.get_llm()
        LLMFactory.get_tavily()
        
        print("[INFO] All models loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load models during startup: {e}")
    
    yield
    # 서버 종료 시 실행될 로직
    print("[INFO] Shutting down...")

app = FastAPI(lifespan=lifespan)

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

# Register Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(prefer.router)

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
