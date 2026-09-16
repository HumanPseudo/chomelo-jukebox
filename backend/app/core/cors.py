from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings

_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_ALLOWED_HEADERS = ["Authorization", "Content-Type", "X-Request-ID"]
_EXPOSED_HEADERS = ["X-Request-ID"]


def setup_cors(app: FastAPI) -> None:
    origins = settings.cors_origins
    allow_all = "*" in origins
    app.add_middleware(
        CORSMiddleware,
        # "*" implica origen arbitrario: se permite sin credenciales.
        allow_origins=["*"] if allow_all else origins,
        allow_methods=_ALLOWED_METHODS,
        allow_headers=_ALLOWED_HEADERS,
        expose_headers=_EXPOSED_HEADERS,
        allow_credentials=not allow_all,
        max_age=600,
    )
