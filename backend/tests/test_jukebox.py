from httpx import ASGITransport, AsyncClient

from app.main import app

_transport = ASGITransport(app=app)
_BASE = "http://test"
_PASSWORD = "secure123"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


async def _make_jukebox(client: AsyncClient, token: str, name: str = "Mi Jukebox") -> dict:
    r = await client.post(
        "/api/v1/jukeboxes",
        headers=_auth(token),
        json={"name": name, "description": ""},
    )
    assert r.status_code == 201
    return r.json()


def _member_uid(members: list[dict], display_name: str) -> int:
    return next(m["user_id"] for m in members if m["display_name"] == display_name)


# ---------- create / list ----------


async def test_create_jukebox_requires_auth():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post("/api/v1/jukeboxes", json={"name": "x"})
    assert r.status_code == 401


async def test_create_jukebox_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _register(c, "owner@test.com")
        body = await _make_jukebox(c, token, "Fiesta")
    assert body["name"] == "Fiesta"
    assert body["role"] == "ADMIN"
    assert body["member_count"] == 1
    assert len(body["invite_code"]) == 6


async def test_list_my_jukeboxes():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _register(c, "list@test.com")
        first = await _make_jukebox(c, token, "Uno")
        await _make_jukebox(c, token, "Dos")
        r = await c.get("/api/v1/jukeboxes", headers=_auth(token))
    assert r.status_code == 200
    names = [j["name"] for j in r.json()]
    assert names[:2] == ["Dos", "Uno"]  # orden DESC por id
    assert first["id"] in [j["id"] for j in r.json()]


# ---------- join ----------


async def test_join_by_code_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "host@test.com")
        jb = await _make_jukebox(c, owner_token, "Compartida")
        member_token = await _register(c, "invitado@test.com")
        r = await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(member_token),
            json={"invite_code": jb["invite_code"].lower()},  # case-insensitive
        )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == jb["id"]
    assert body["role"] == "MEMBER"
    assert body["member_count"] == 2


async def test_join_by_code_wrong_code():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _register(c, "ghost@test.com")
        r = await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(token),
            json={"invite_code": "XXXXXX"},
        )
    assert r.status_code == 404
    assert r.json()["code"] == "invite_invalid"


async def test_join_duplicate():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "host2@test.com")
        jb = await _make_jukebox(c, owner_token)
        token = await _register(c, "again@test.com")
        invite = {"invite_code": jb["invite_code"]}
        await c.post("/api/v1/jukeboxes/join", headers=_auth(token), json=invite)
        r = await c.post("/api/v1/jukeboxes/join", headers=_auth(token), json=invite)
    assert r.status_code == 409
    assert r.json()["code"] == "already_member"


# ---------- detail / access ----------


async def test_non_member_cannot_view():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "priv@test.com")
        jb = await _make_jukebox(c, owner_token)
        stranger_token = await _register(c, "stranger@test.com")
        r = await c.get(f"/api/v1/jukeboxes/{jb['id']}", headers=_auth(stranger_token))
    assert r.status_code == 404


async def test_update_requires_admin():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "adminchk@test.com")
        jb = await _make_jukebox(c, owner_token)
        guest_token = await _register(c, "guest@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(guest_token),
            json={"invite_code": jb["invite_code"]},
        )
        r = await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}",
            headers=_auth(guest_token),
            json={"name": "hack"},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "insufficient_role"


async def test_update_jukebox_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _register(c, "edit@test.com")
        jb = await _make_jukebox(c, token)
        r = await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}",
            headers=_auth(token),
            json={"name": "Renombrado"},
        )
    assert r.status_code == 200
    assert r.json()["name"] == "Renombrado"


async def test_delete_requires_admin():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "delowner@test.com")
        jb = await _make_jukebox(c, owner_token)
        member_token = await _register(c, "delmember@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(member_token),
            json={"invite_code": jb["invite_code"]},
        )
        r = await c.delete(f"/api/v1/jukeboxes/{jb['id']}", headers=_auth(member_token))
    assert r.status_code == 403


async def test_delete_jukebox_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _register(c, "deleter@test.com")
        jb = await _make_jukebox(c, token)
        r = await c.delete(f"/api/v1/jukeboxes/{jb['id']}", headers=_auth(token))
        after = await c.get(f"/api/v1/jukeboxes/{jb['id']}", headers=_auth(token))
    assert r.status_code == 204
    assert after.status_code == 404


# ---------- members / roles ----------


async def test_members_list():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "staff@test.com")
        jb = await _make_jukebox(c, owner_token)
        member_token = await _register(c, "staff2@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(member_token),
            json={"invite_code": jb["invite_code"]},
        )
        r = await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(owner_token))
    assert r.status_code == 200
    roles = {m["display_name"]: m["role"] for m in r.json()}
    assert roles.get("staff") == "ADMIN"
    assert roles.get("staff2") == "MEMBER"


async def test_cannot_demote_last_admin():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "boss@test.com")
        jb = await _make_jukebox(c, owner_token)
        members = (
            await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(owner_token))
        ).json()
        boss_uid = _member_uid(members, "boss")
        r = await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}/members/{boss_uid}",
            headers=_auth(owner_token),
            json={"role": "MEMBER"},
        )
    assert r.status_code == 409
    assert r.json()["code"] == "last_admin"


async def test_admin_can_demote_another_admin_if_not_last():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "boss2@test.com")
        jb = await _make_jukebox(c, owner_token)
        admin_token = await _register(c, "admin2@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(admin_token),
            json={"invite_code": jb["invite_code"]},
        )
        members = (
            await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(owner_token))
        ).json()
        admin_uid = _member_uid(members, "admin2")
        boss_uid = _member_uid(members, "boss2")
        await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}/members/{admin_uid}",
            headers=_auth(owner_token),
            json={"role": "ADMIN"},
        )
        # con dos admins, uno puede bajar al otro a MEMBER sin dejar la
        # jukebox huérfana de administración.
        r = await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}/members/{boss_uid}",
            headers=_auth(admin_token),
            json={"role": "MEMBER"},
        )
    assert r.status_code == 200
    assert r.json()["role"] == "MEMBER"


async def test_member_cannot_promote_self():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "promo@test.com")
        jb = await _make_jukebox(c, owner_token)
        member_token = await _register(c, "promo2@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(member_token),
            json={"invite_code": jb["invite_code"]},
        )
        members = (
            await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(member_token))
        ).json()
        uid = _member_uid(members, "promo2")
        r = await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}/members/{uid}",
            headers=_auth(member_token),
            json={"role": "ADMIN"},
        )
    assert r.status_code == 403


async def test_role_update_rejects_unknown_role():
    """OWNER/MODERATOR/GUEST ya no existen: el schema los rechaza (422)."""
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "tr1@test.com")
        jb = await _make_jukebox(c, owner_token)
        members = (
            await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(owner_token))
        ).json()
        uid = _member_uid(members, "tr1")
        r = await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}/members/{uid}",
            headers=_auth(owner_token),
            json={"role": "OWNER"},
        )
    assert r.status_code == 422


async def test_any_admin_promotes_member_to_admin():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "ap@test.com")
        jb = await _make_jukebox(c, owner_token)
        admin_token = await _register(c, "ap2@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(admin_token),
            json={"invite_code": jb["invite_code"]},
        )
        members = (
            await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(owner_token))
        ).json()
        admin_uid = _member_uid(members, "ap2")
        await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}/members/{admin_uid}",
            headers=_auth(owner_token),
            json={"role": "ADMIN"},
        )
        target_token = await _register(c, "ap3@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(target_token),
            json={"invite_code": jb["invite_code"]},
        )
        members = (
            await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(admin_token))
        ).json()
        uid = _member_uid(members, "ap3")
        # ap2 (promovido por ap, no el creador) también tiene poder de
        # admin completo: no hay jerarquía por debajo de ADMIN.
        r = await c.patch(
            f"/api/v1/jukeboxes/{jb['id']}/members/{uid}",
            headers=_auth(admin_token),
            json={"role": "ADMIN"},
        )
    assert r.status_code == 200
    assert r.json()["role"] == "ADMIN"


async def test_remove_member_ok():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "rm@test.com")
        jb = await _make_jukebox(c, owner_token)
        member_token = await _register(c, "rm2@test.com")
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(member_token),
            json={"invite_code": jb["invite_code"]},
        )
        members = (
            await c.get(f"/api/v1/jukeboxes/{jb['id']}/members", headers=_auth(owner_token))
        ).json()
        uid = _member_uid(members, "rm2")
        r = await c.delete(
            f"/api/v1/jukeboxes/{jb['id']}/members/{uid}", headers=_auth(owner_token)
        )
    assert r.status_code == 204
