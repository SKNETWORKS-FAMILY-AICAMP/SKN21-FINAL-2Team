import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure `app` package is importable regardless of pytest invocation cwd.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.pool import StaticPool
from app.database.connection import Base, db_manager

# Use SQLite in-memory for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.llm_factory import LLMFactory
    from app.core.retrieval.place import PlaceRetriever

    class _DummyRetriever:
        def _ensure_reranker(self):
            return None

    monkeypatch.setattr(PlaceRetriever, "get_instance", classmethod(lambda cls: _DummyRetriever()))
    monkeypatch.setattr(LLMFactory, "get_llm", classmethod(lambda cls, temperature=0.0: None))

    def override_get_db():
        try:
            yield db
        finally:
            pass # db closed in fixture

    app.dependency_overrides[db_manager.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
