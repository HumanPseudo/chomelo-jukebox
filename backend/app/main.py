from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging, setup_request_id_middleware

setup_logging()

app = FastAPI(title=settings.app_name, version="0.1.0")

setup_exception_handlers(app)
setup_request_id_middleware(app)

app.include_router(api_router)


@app.get("/health")
async def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "chomelo-backend"}
