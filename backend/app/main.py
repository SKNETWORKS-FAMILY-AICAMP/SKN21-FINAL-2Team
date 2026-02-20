from dotenv import load_dotenv
load_dotenv()
import os                                               # 추가

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles             # 추가
import time
import logging
from app.api import auth, users, chat, prefer, common
from app.database.connection import Base, get_engine
from app.models import user, chat as chat_model, prefer as prefer_model, country as country_model  # noqa: F401 - 테이블 등록용

app = FastAPI()

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
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# /static 경로로 uploads 디렉토리 서빙
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# Register Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(prefer.router)
app.include_router(common.router)

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
