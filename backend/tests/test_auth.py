from httpx import ASGITransport, AsyncClient

from app.main import app

_transport = ASGITransport(app=app)
_BASE = "http://test"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _phone(email: str) -> str:
    digits = "".join(str(ord(ch) % 10) for ch in email if ch.isalnum())
    return "+57" + digits[:12]


def _register_body(email: str, password: str = "secure123") -> dict[str, str]:
    return {"phone_number": _phone(email), "password": password}


async def test_register_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post("/api/v1/auth/register", json=_register_body("ok@test.com"))
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0


async def test_register_duplicate_email():
    payload = _register_body("dup@test.com")
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        assert (await c.post("/api/v1/auth/register", json=payload)).status_code == 201
        r = await c.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["code"] == "phone_taken"


async def test_register_short_password():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post(
            "/api/v1/auth/register", json=_register_body("short@test.com", "short")
        )
    assert r.status_code == 422


async def test_login_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        await c.post("/api/v1/auth/register", json=_register_body("login@test.com"))
        r = await c.post(
            "/api/v1/auth/login",
            json={"phone_number": _phone("login@test.com"), "password": "secure123"},
        )
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_login_wrong_password():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        await c.post("/api/v1/auth/register", json=_register_body("wrong@test.com"))
        r = await c.post(
            "/api/v1/auth/login",
            json={"phone_number": _phone("wrong@test.com"), "password": "badpassword"},
        )
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"


async def test_login_unknown_email():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"phone_number": _phone("ghost@test.com"), "password": "irrelevant"},
        )
    assert r.status_code == 401


async def test_me_unauthenticated():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.get("/api/v1/users/me")
    assert r.status_code == 401


async def test_me_with_valid_token():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        reg = await c.post("/api/v1/auth/register", json=_register_body("me@test.com"))
        token = reg.json()["access_token"]
        r = await c.get("/api/v1/users/me", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["phone_number"] == _phone("me@test.com")
    assert body["is_active"] is True
    assert body["display_name"]


async def test_me_with_garbage_token():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.get("/api/v1/users/me", headers=_auth("not-a-real-jwt"))
    assert r.status_code == 401
    assert r.json()["code"] == "auth_invalid"


async def test_refresh_with_access_token_rejected():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        reg = await c.post("/api/v1/auth/register", json=_register_body("ref@test.com"))
        access = reg.json()["access_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401
    assert r.json()["code"] == "auth_invalid"


async def test_refresh_rotates_tokens():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        reg = await c.post("/api/v1/auth/register", json=_register_body("rot@test.com"))
        refresh = reg.json()["refresh_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    body = r.json()
    assert body["refresh_token"]
    assert body["access_token"]
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        me = await c.get("/api/v1/users/me", headers=_auth(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["phone_number"] == _phone("rot@test.com")


async def test_refresh_token_reuse_is_rejected():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        reg = await c.post("/api/v1/auth/register", json=_register_body("reuse@test.com"))
        old_access = reg.json()["access_token"]
        refresh = reg.json()["refresh_token"]
        first = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        replay = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        me = await c.get("/api/v1/users/me", headers=_auth(old_access))
    assert first.status_code == 200
    assert replay.status_code == 401
    assert replay.json()["code"] == "auth_invalid"
    assert me.status_code == 401
