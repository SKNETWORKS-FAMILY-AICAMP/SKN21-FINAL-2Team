import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, _build_cors_settings


def test_build_cors_settings_default_includes_ec2_domains(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ORIGIN_REGEX", raising=False)

    origins, origin_regex = _build_cors_settings()

    assert "http://localhost" in origins
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1" in origins
    assert "https://triver-s.com" in origins
    assert "https://www.triver-s.com" in origins
    assert origin_regex is None


@pytest.mark.asyncio
async def test_preflight_allows_localhost_origin_without_port():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/chat/rooms/105/autostart/stream",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost"
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_preflight_allows_production_origin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/chat/rooms/104/autostart/stream",
            headers={
                "Origin": "https://triver-s.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://triver-s.com"
    assert response.headers.get("access-control-allow-credentials") == "true"
