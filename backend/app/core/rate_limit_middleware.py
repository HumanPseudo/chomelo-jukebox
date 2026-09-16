import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.infra import rate_limit

logger = logging.getLogger(__name__)

_EXCLUDED_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")
_EXCLUDED_METHODS = {"OPTIONS", "HEAD"}


def _is_excluded(request: Request) -> bool:
    path = request.url.path
    if path in _EXCLUDED_PREFIXES or path.startswith("/payments/webhook"):
        return True
    if request.method in _EXCLUDED_METHODS:
        return True
    return False


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Limita el número de peticiones por IP en una ventana de tiempo.

    Fail-open: si Redis no está disponible permite pasar la petición.
    Se omiten healthcheck, endpoints de webhook y preflights OPTIONS.
    """

    async def dispatch(self, request: Request, call_next) -> JSONResponse | None:
        if not _is_excluded(request):
            ip = request.client.host if request.client else "unknown"
            key = f"global:{ip}"
            if await rate_limit.is_rate_limited(
                key,
                limit=settings.rate_limit_global_limit,
                window=settings.rate_limit_global_window,
            ):
                logger.info("global rate limit exceeded", extra={"ip": ip})
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "demasiadas peticiones, espera un momento",
                        "code": "rate_limited",
                    },
                )
        return await call_next(request)


def setup_global_rate_limit(app: FastAPI) -> None:
    app.add_middleware(GlobalRateLimitMiddleware)
