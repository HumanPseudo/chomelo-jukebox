import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState

from app.core.security import decode_token
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.domain.user import User
from app.infra.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def _resolve_user(db: AsyncSession, token: str) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload.get("sub", "0"))
    except (JWTError, TypeError, ValueError):
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


@router.websocket("/ws/jukebox/{jukebox_id}")
async def ws_jukebox(
    websocket: WebSocket,
    jukebox_id: int,
    db: AsyncSession = Depends(get_db),
    token: str = Query(default=""),
) -> None:
    user = await _resolve_user(db, token)
    if user is None:
        await websocket.close(code=4401)
        return

    result = await db.execute(
        select(JukeboxMember).where(
            JukeboxMember.user_id == user.id,
            JukeboxMember.jukebox_id == jukebox_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None or member.role == Role.GUEST.value:
        await websocket.close(code=4403)
        return

    if websocket.application_state != WebSocketState.CONNECTED:
        await websocket.accept()

    await ws_manager.connect(jukebox_id, websocket)
    await websocket.send_json({"event": "connected", "jukebox_id": jukebox_id, "data": {}})
    try:
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_json({"event": "pong", "jukebox_id": jukebox_id, "data": {}})
    except WebSocketDisconnect:
        ws_manager.disconnect(jukebox_id, websocket)
    except Exception:
        logger.debug("ws client dropped", exc_info=True)
        ws_manager.disconnect(jukebox_id, websocket)
