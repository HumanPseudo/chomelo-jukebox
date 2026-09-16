from httpx import ASGITransport, AsyncClient

from app.main import app

_transport = ASGITransport(app=app)
_BASE = "http://test"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------- register ----------


async def test_register_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post(
            "/api/v1/auth/register",
            json={"email": "ok@test.com", "password": "secure123"},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0


async def test_register_duplicate_email():
    payload = {"email": "dup@test.com", "password": "secure123"}
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        assert (await c.post("/api/v1/auth/register", json=payload)).status_code == 201
        r = await c.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["code"] == "email_taken"


async def test_register_short_password():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post(
            "/api/v1/auth/register",
            json={"email": "short@test.com", "password": "short"},
        )
    assert r.status_code == 422


# ---------- login ----------


async def test_login_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        await c.post(
            "/api/v1/auth/register",
            json={"email": "login@test.com", "password": "secure123"},
        )
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "login@test.com", "password": "secure123"},
        )
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_login_wrong_password():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        await c.post(
            "/api/v1/auth/register",
            json={"email": "wrong@test.com", "password": "secure123"},
        )
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "wrong@test.com", "password": "badpassword"},
        )
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"


async def test_login_unknown_email():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "ghost@test.com", "password": "irrelevant"},
        )
    assert r.status_code == 401


# ---------- /users/me ----------


async def test_me_unauthenticated():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.get("/api/v1/users/me")
    assert r.status_code == 401


async def test_me_with_valid_token():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        reg = await c.post(
            "/api/v1/auth/register",
            json={"email": "me@test.com", "password": "secure123"},
        )
        token = reg.json()["access_token"]
        r = await c.get("/api/v1/users/me", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "me@test.com"
    assert body["is_active"] is True
    assert body["display_name"]


async def test_me_with_garbage_token():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.get("/api/v1/users/me", headers=_auth("not-a-real-jwt"))
    assert r.status_code == 401
    assert r.json()["code"] == "auth_invalid"


# ---------- refresh ----------


async def test_refresh_with_access_token_rejected():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        reg = await c.post(
            "/api/v1/auth/register",
            json={"email": "ref@test.com", "password": "secure123"},
        )
        access = reg.json()["access_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401
    assert r.json()["code"] == "auth_invalid"


async def test_refresh_rotates_tokens():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        reg = await c.post(
            "/api/v1/auth/register",
            json={"email": "rot@test.com", "password": "secure123"},
        )
        refresh = reg.json()["refresh_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    body = r.json()
    assert body["refresh_token"]
    assert body["access_token"]
    # Verify new tokens are usable
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        me = await c.get("/api/v1/users/me", headers=_auth(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "rot@test.com"
