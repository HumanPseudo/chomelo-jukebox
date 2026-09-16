from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging, setup_request_id_middleware
from app.core.rate_limit_middleware import setup_global_rate_limit
from app.core.security_headers import setup_security_headers
from app.infra.ws_manager import ws_manager

setup_logging()

_in_production = settings.environment == "production"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ws_manager.start_subscriber()
    yield
    ws_manager.stop_subscriber()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    # Nunca exponer tracebacks: el handler genérico registra en logs y devuelve
    # un 500 JSON sin filtrar internos (también en desarrollo).
    debug=False,
    # La superficie expuesta (docs, schema OpenAPI) se desactiva en producción.
    docs_url=None if _in_production else "/docs",
    redoc_url=None if _in_production else "/redoc",
    openapi_url=None if _in_production else "/openapi.json",
)

setup_exception_handlers(app)

# Middleware: el último añadido es el más externo.
setup_request_id_middleware(app)
setup_global_rate_limit(app)
setup_security_headers(app)
setup_cors(app)

app.include_router(api_router)


@app.get("/health")
async def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "chomelo-backend"}
