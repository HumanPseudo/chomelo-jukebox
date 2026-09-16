from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_api_v1() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "X-Request-ID" in response.headers


async def test_health_root() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_unknown_route_returns_json_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/nope")
    assert response.status_code == 404
    assert "detail" in response.json()


async def test_validation_error_shape() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/health")
    assert response.status_code == 405
    body = response.json()
    assert body.get("detail") is not None


# Sanidad: el módulo AppError se importa sin errores.
def test_app_error_import() -> None:
    from app.core.exceptions import AppError

    err = AppError("boom", code="test_error", status_code=422)
    assert err.code == "test_error"
    assert err.status_code == 422
    assert err.message == "boom"
