import asyncio, json, httpx, sys

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10) as c:
        token = (await c.post("/api/v1/auth/login", json={"email": "gamecheck@chomelo.app", "password": "demo1234"})).json()["access_token"]
    from websockets.asyncio.client import connect
    ws = await connect(f"ws://localhost:8000/api/v1/ws/jukebox/4?token={token}", open_timeout=10)
    await ws.send('{"type":"ping"}')
    try:
        m = await asyncio.wait_for(ws.recv(), timeout=8)
        print("recv:", json.loads(m).get("event"))
    except Exception as e:
        print("recv error:", type(e).__name__)
    await ws.close()

asyncio.run(main())