import asyncio, json, httpx

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10) as c:
        token = (await c.post("/api/v1/auth/login", json={"email": "gamecheck@chomelo.app", "password": "demo1234"})).json()["access_token"]
    from websockets.asyncio.client import connect
    ws = await connect(f"ws://localhost:8000/api/v1/ws/jukebox/4?token={token}", open_timeout=10)
    first = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
    await ws.send('{"type":"ping"}')
    second = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
    print("events:", first.get("event"), second.get("event"))
    await ws.close()

asyncio.run(main())
