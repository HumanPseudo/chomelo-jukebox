from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from tests.helpers import PASSWORD, auth, use_fake_music

PASS = PASSWORD


def _register(client: TestClient, email: str) -> str:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": PASS})
    assert r.status_code == 201
    return r.json()["access_token"]


def _create_jukebox(client: TestClient, token: str, name: str) -> int:
    r = client.post("/api/v1/jukeboxes", headers=auth(token), json={"name": name})
    assert r.status_code == 201
    return int(r.json()["id"])


def _ws_url(jukebox_id: int, token: str) -> str:
    return f"/api/v1/ws/jukebox/{jukebox_id}?token={token}"


def test_ws_rejects_bad_token():
    use_fake_music()
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(_ws_url(1, "token-invalido")):
                pass
        assert exc.value.code == 4401


def test_ws_rejects_non_member():
    use_fake_music()
    with TestClient(app) as client:
        owner = _register(client, "wsowner@test.com")
        outsider = _register(client, "wsout@test.com")
        jb = _create_jukebox(client, owner, "Solo")
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(_ws_url(jb, outsider)):
                pass
        assert exc.value.code == 4403


def test_ws_sends_connected_hello():
    use_fake_music()
    with TestClient(app) as client:
        token = _register(client, "wshello@test.com")
        jb = _create_jukebox(client, token, "Hola")
        with client.websocket_connect(_ws_url(jb, token)) as ws:
            msg = ws.receive_json()
            assert msg["event"] == "connected"
            assert msg["jukebox_id"] == jb


def test_ws_broadcasts_queue_updated_on_add():
    use_fake_music()
    with TestClient(app) as client:
        token = _register(client, "wsq@test.com")
        jb = _create_jukebox(client, token, "Cola")
        with client.websocket_connect(_ws_url(jb, token)) as ws:
            ws.receive_json()  # connected
            r = client.post(
                f"/api/v1/jukeboxes/{jb}/queue",
                headers=auth(token),
                json={"track_id": "abc"},
            )
            assert r.status_code == 201
            msg = ws.receive_json()
            assert msg["event"] == "queue.updated"
            assert msg["data"]["item_id"] == r.json()["id"]


def test_ws_broadcasts_player_and_poll_and_game():
    use_fake_music()
    with TestClient(app) as client:
        token = _register(client, "wsevents@test.com")
        jb = _create_jukebox(client, token, "Juegos")
        with client.websocket_connect(_ws_url(jb, token)) as ws:
            ws.receive_json()  # connected

            # 4 canciones distintas reproducidas (requisito de Guess the Song)
            for track_id in ["abc", "def", "ghi", "jkl"]:
                r = client.post(
                    f"/api/v1/jukeboxes/{jb}/queue",
                    headers=auth(token),
                    json={"track_id": track_id},
                )
                assert r.status_code == 201
                assert ws.receive_json()["event"] == "queue.updated"

            r = client.post(f"/api/v1/jukeboxes/{jb}/player/play", headers=auth(token))
            assert r.status_code == 204
            assert ws.receive_json()["event"] == "player.updated"

            for _ in range(3):
                r = client.post(f"/api/v1/jukeboxes/{jb}/player/next", headers=auth(token))
                assert r.status_code == 204
                assert ws.receive_json()["event"] == "player.updated"

            r = client.post(
                f"/api/v1/jukeboxes/{jb}/polls",
                headers=auth(token),
                json={"question": "¿Cuál?", "options": ["A", "B"]},
            )
            assert r.status_code == 201
            assert ws.receive_json()["event"] == "poll.updated"

            r = client.post(
                f"/api/v1/jukeboxes/{jb}/games/guess_the_song/rounds",
                headers=auth(token),
                json={"duration_seconds": 60},
            )
            assert r.status_code == 201
            msg = ws.receive_json()
            assert msg["event"] == "game.updated"
            assert msg["data"]["round_id"] == r.json()["id"]


def test_ws_events_are_isolated_per_jukebox():
    use_fake_music()
    with TestClient(app) as client:
        token = _register(client, "wsiso@test.com")
        jb1 = _create_jukebox(client, token, "Uno")
        jb2 = _create_jukebox(client, token, "Dos")
        with client.websocket_connect(_ws_url(jb1, token)) as ws1:
            ws1.receive_json()  # connected
            with client.websocket_connect(_ws_url(jb2, token)) as ws2:
                ws2.receive_json()  # connected
                r = client.post(
                    f"/api/v1/jukeboxes/{jb2}/queue",
                    headers=auth(token),
                    json={"track_id": "bbb"},
                )
                assert r.status_code == 201
                assert ws2.receive_json()["event"] == "queue.updated"
                # el evento de jb2 no debe llegar a ws1
                r1 = client.post(
                    f"/api/v1/jukeboxes/{jb1}/queue",
                    headers=auth(token),
                    json={"track_id": "aaa"},
                )
                assert r1.status_code == 201
                msg1 = ws1.receive_json()
                assert msg1["event"] == "queue.updated"
                assert msg1["data"]["item_id"] == r1.json()["id"]
