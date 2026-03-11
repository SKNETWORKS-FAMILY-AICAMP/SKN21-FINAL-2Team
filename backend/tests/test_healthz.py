from fastapi.testclient import TestClient

from app.core.llm_factory import LLMFactory
from app.core.retrieval.place import PlaceRetriever
from app.main import app


def test_healthz_returns_ok(monkeypatch):
    monkeypatch.setattr(PlaceRetriever, "get_instance", classmethod(lambda cls: None))
    monkeypatch.setattr(LLMFactory, "get_llm", classmethod(lambda cls, temperature=0.0: None))
    monkeypatch.setattr(LLMFactory, "get_tavily", classmethod(lambda cls: None))

    with TestClient(app) as client:
        response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
