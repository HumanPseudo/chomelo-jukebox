from app.infra.ws_manager import ws_manager


async def notify_jukebox(jukebox_id: int, event_type: str, **data) -> None:
    """Difunde un evento en el canal WebSocket del jukebox (local + Redis Pub/Sub)."""
    await ws_manager.publish_event(jukebox_id, event_type, **data)
