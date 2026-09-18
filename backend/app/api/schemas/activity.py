from datetime import datetime

from pydantic import BaseModel


class ActivityOut(BaseModel):
    """Un evento derivado de datos ya existentes: nadie puede "inventar"
    actividad, esto es una lectura agregada de las tablas del jukebox."""

    id: int
    kind: str
    user_id: int | None = None
    display_name: str = ""
    title: str | None = None
    subtitle: str | None = None
    created_at: datetime
