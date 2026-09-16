from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

_HSTS = "max-age=31536000; includeSubDomains"
_CSP_API = "default-src 'none'; frame-ancestors 'none'"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade cabeceras de seguridad a todas las respuestas HTTP.

    Las cabeceras CSP y HSTS solo se incluyen cuando
    ``settings.environment == 'production'`` para no romper los
    endpoints de Swagger en desarrollo.  El header ``Server`` se
    suprime siempre para no revelar la pila tecnológica.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        if request.scope.get("type") != "http":
            return response

        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        headers["Cache-Control"] = "no-store"

        if settings.environment == "production":
            headers["Strict-Transport-Security"] = _HSTS
            headers["Content-Security-Policy"] = _CSP_API

        # Suprimir header de servidor (uvicorn / starlette).
        try:
            del headers["server"]
        except KeyError:
            pass
        return response


def setup_security_headers(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
