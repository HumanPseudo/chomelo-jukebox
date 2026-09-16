from httpx import ASGITransport, AsyncClient

from app.api.deps import get_music_provider
from app.main import app
from app.providers.music import MusicProvider, MusicProviderError, TrackInfo

transport = ASGITransport(app=app)
BASE = "http://test"
PASSWORD = "secure123"


class FakeMusicProvider(MusicProvider):
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def search(self, query: str, limit: int = 5) -> list[TrackInfo]:
        raise MusicProviderError()

    async def get_track(self, track_id: str) -> TrackInfo:
        if self.fail:
            raise MusicProviderError()
        return TrackInfo(
            provider="youtube",
            track_id=track_id,
            title=f"Titulo {track_id}",
            artist="Artista",
            duration_seconds=180,
            thumbnail_url="https://i.ytimg.com/vi/x/default.jpg",
        )

    async def resolve(self, track_id: str):
        raise MusicProviderError()


def use_fake_music(fail: bool = False) -> None:
    app.dependency_overrides[get_music_provider] = lambda: FakeMusicProvider(fail=fail)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register_user(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


async def make_jukebox_x2() -> tuple[str, str, int, str]:
    """Crea jukebox con owner y un member; devuelve tokens owner/member + id + codigo."""
    use_fake_music()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        owner_token = await register_user(c, "vowner@test.com")
        member_token = await register_user(c, "vmember@test.com")
        jb = (
            await c.post(
                "/api/v1/jukeboxes",
                headers=auth(owner_token),
                json={"name": "Votos"},
            )
        ).json()
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=auth(member_token),
            json={"invite_code": jb["invite_code"]},
        )
    return owner_token, member_token, int(jb["id"]), jb["invite_code"]


async def add_item(client: AsyncClient, token: str, jukebox_id: int, track_id: str = "abc"):
    return await client.post(
        f"/api/v1/jukeboxes/{jukebox_id}/queue",
        headers=auth(token),
        json={"track_id": track_id},
    )
