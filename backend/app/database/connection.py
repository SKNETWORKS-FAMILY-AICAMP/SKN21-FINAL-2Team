from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

class DBManager:
    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        MYSQL_USER = os.getenv("MYSQL_USER", "admin")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
        MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
        MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
        MYSQL_DB = os.getenv("MYSQL_DATABASE", "")

        DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

        self._engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self._session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine
        )

    @property
    def engine(self):
        return self._engine

    def get_db(self):
        """FastAPI Dependency용 제너레이터"""
        db = self._session_factory()
        try:
            yield db
        finally:
            db.close()

    def get_session(self):
        """일반 스크립트용 세션 반환"""
        return self._session_factory()



# 하위 호환성 유지 및 전역 사용을 위한 인스턴스/함수
db_manager = DBManager()

def get_db():
    yield from db_manager.get_db()

def get_engine():
    return db_manager.engine

Base = declarative_base()
