from fastapi import APIRouter

from app.api.routes import (
    auth,
    games,
    health,
    jukeboxes,
    music,
    polls,
    profile,
    queue,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(profile.router)
api_router.include_router(jukeboxes.router)
api_router.include_router(music.router)
api_router.include_router(queue.router)
api_router.include_router(polls.router)
api_router.include_router(games.router)
