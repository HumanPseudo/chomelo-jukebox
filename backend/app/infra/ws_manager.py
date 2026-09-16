import asyncio
import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger(__name__)

WS_CHANNEL = "chomelo:ws"

_redis_client: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=1
            )
        except Exception:
            return None
    return _redis_client


class WSManager:
    """Conexiones WebSocket activas agrupadas por jukebox.

    - `broadcast` entrega a los clientes locales y publica en Redis Pub/Sub para
      que otras instancias del backend (tras un balanceador) reenvíen a las suyas.
    - Cada evento lleva `instance_id`; el suscriptor ignora los mensajes que emitió
      esta misma instancia para no duplicar la entrega local.
    - Fail-open: si Redis no está disponible, la difusión local sigue funcionando y
      la publicación se registra como warning sin romper la operación.
    """

    def __init__(self) -> None:
        self.instance_id: str = uuid.uuid4().hex[:8]
        self._connections: dict[int, set[WebSocket]] = {}
        self._subscriber_task: asyncio.Task | None = None

    def reset(self) -> None:
        self._connections.clear()

    async def connect(self, jukebox_id: int, websocket: WebSocket) -> None:
        self._connections.setdefault(jukebox_id, set()).add(websocket)

    def disconnect(self, jukebox_id: int, websocket: WebSocket) -> None:
        sockets = self._connections.get(jukebox_id)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(jukebox_id, None)

    async def broadcast_local(self, jukebox_id: int, event: dict) -> None:
        for websocket in list(self._connections.get(jukebox_id, ())):
            try:
                await websocket.send_json(event)
            except Exception:
                self.disconnect(jukebox_id, websocket)

    async def publish_event(self, jukebox_id: int, event_type: str, **data) -> None:
        event = {
            "event": event_type,
            "jukebox_id": jukebox_id,
            "instance_id": self.instance_id,
            "data": data,
        }
        await self.broadcast_local(jukebox_id, event)
        if settings.ws_pubsub_enabled:
            await self._publish(event)

    async def _publish(self, event: dict) -> None:
        client = _get_redis()
        if client is None:
            return
        try:
            await client.publish(WS_CHANNEL, json.dumps(event))
        except Exception:
            logger.warning("WS pub/sub publish failed; local broadcast only", exc_info=True)

    def start_subscriber(self) -> None:
        if not settings.ws_pubsub_enabled:
            return
        client = _get_redis()
        if client is None:
            return
        self._subscriber_task = asyncio.create_task(self._consume(client))

    async def _consume(self, client: aioredis.Redis) -> None:
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(WS_CHANNEL)
        except Exception:
            logger.warning("WS pub/sub subscribe failed; skipping subscriber", exc_info=True)
            return
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                except (TypeError, ValueError):
                    continue
                if event.get("instance_id") == self.instance_id:
                    continue
                try:
                    await self.broadcast_local(int(event["jukebox_id"]), event)
                except (KeyError, TypeError, ValueError):
                    continue
        except asyncio.CancelledError:
            await self._unsafe_unsubscribe(pubsub)
            raise
        except Exception:
            logger.warning("WS subscriber stopped", exc_info=True)
            await self._unsafe_unsubscribe(pubsub)

    async def _unsafe_unsubscribe(self, pubsub) -> None:
        try:
            await pubsub.unsubscribe(WS_CHANNEL)
        except Exception:
            pass

    def stop_subscriber(self) -> None:
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            self._subscriber_task = None


ws_manager = WSManager()
