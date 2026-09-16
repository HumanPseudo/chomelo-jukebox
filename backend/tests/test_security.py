from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.domain.user import User
from app.infra import rate_limit
from tests.helpers import PASSWORD, auth, register_user


def _client() -> AsyncClient:
    from app.main import app

    return AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def test_security_headers_present():
    async with _client() as c:
        r = await c.get("/api/v1/jukeboxes")
        assert r.status_code == 401
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in r.headers["permissions-policy"]
        assert "no-store" in r.headers.get("cache-control", "")
        assert "server" not in {k.lower() for k in r.headers}


async def test_hsts_and_csp_only_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    async with _client() as c:
        r = await c.get("/api/v1/jukeboxes")
        assert r.headers["strict-transport-security"].startswith("max-age=31536000")
        assert "default-src 'none'" in r.headers["content-security-policy"]


async def test_hsts_and_csp_absent_in_development():
    async with _client() as c:
        r = await c.get("/api/v1/jukeboxes")
        assert "strict-transport-security" not in r.headers
        assert "content-security-policy" not in r.headers


async def test_cors_allowed_origin_only():
    async with _client() as c:
        r = await c.get("/api/v1/jukeboxes", headers={"Origin": "http://localhost:3000"})
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
        r2 = await c.get("/api/v1/jukeboxes", headers={"Origin": "http://evil.example"})
        assert "access-control-allow-origin" not in r2.headers


async def test_global_rate_limit_blocks_and_excludes(monkeypatch):
    async def fake_limited(key: str, limit: int, window: int) -> bool:
        return True

    monkeypatch.setattr(rate_limit, "is_rate_limited", fake_limited)
    async with _client() as c:
        r = await c.get("/api/v1/jukeboxes")
        assert r.status_code == 429
        assert r.json()["code"] == "rate_limited"
        # /health y los preflights OPTIONS se excluyen del límite global.
        r2 = await c.get("/health")
        assert r2.status_code == 200
        r3 = await c.options(
            "/api/v1/jukeboxes",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert r3.status_code == 200


async def test_login_brute_force_per_ip(monkeypatch):
    from app.services import auth_service

    async def fake_limited(key: str, limit: int, window: int) -> bool:
        return key.startswith("login_ip:")

    monkeypatch.setattr(auth_service, "is_rate_limited", fake_limited)
    async with _client() as c:
        r = await c.post(
            "/api/v1/auth/register", json={"email": "bf@test.com", "password": PASSWORD}
        )
        assert r.status_code == 201
        r = await c.post("/api/v1/auth/login", json={"email": "bf@test.com", "password": "wrong"})
        assert r.status_code == 429
        assert r.json()["code"] == "rate_limited"


async def test_generic_500_hides_internals():
    from app.main import app

    async def _boom() -> None:
        raise RuntimeError("secreto interno")

    app.add_api_route("/_test/boom", _boom, methods=["GET"])
    try:
        async with _client() as c:
            r = await c.get("/_test/boom")
            assert r.status_code == 500
            assert "secreto" not in r.text
            assert r.json() == {"detail": "error interno del servidor", "code": "internal_error"}
    finally:
        app.routes[:] = [r for r in app.routes if getattr(r, "path", "") != "/_test/boom"]


async def test_request_id_is_sanitized():
    evil = "abc\n<script>XYZ-123"
    async with _client() as c:
        r = await c.get("/api/v1/jukeboxes", headers={"X-Request-ID": evil})
        rid = r.headers["x-request-id"]
        assert "\n" not in rid and "<" not in rid
        assert len(rid) <= 64


async def test_audit_log_written_on_sensitive_actions(db_session):
    async with _client() as c:
        token = await register_user(c, "audit1@test.com")
        su = User(email="su@test.com", password_hash=hash_password(PASSWORD), is_superuser=True)
        db_session.add(su)
        await db_session.commit()

        r = await c.post("/api/v1/auth/login", json={"email": "su@test.com", "password": PASSWORD})
        assert r.status_code == 200
        su_token = r.json()["access_token"]

        # Un usuario normal no puede consultar el audit log.
        r = await c.get("/api/v1/admin/audit", headers=auth(token))
        assert r.status_code == 403
        assert r.json()["code"] == "admin_required"

        r = await c.get("/api/v1/admin/audit", headers=auth(su_token))
        assert r.status_code == 200
        actions = {item["action"] for item in r.json()}
        assert "auth.register" in actions
        assert "auth.login" in actions


async def test_openapi_enabled_in_dev():
    from app.main import app

    assert app.openapi_url == "/openapi.json"
