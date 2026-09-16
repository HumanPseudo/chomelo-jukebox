from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging, setup_request_id_middleware
from app.infra.ws_manager import ws_manager

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ws_manager.start_subscriber()
    yield
    ws_manager.stop_subscriber()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

setup_exception_handlers(app)
setup_request_id_middleware(app)

app.include_router(api_router)


@app.get("/health")
async def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "chomelo-backend"}
