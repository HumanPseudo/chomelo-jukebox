from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.game import GameRound


@dataclass
class RoundData:
    track_id: str
    title: str
    artist: str
    thumbnail_url: str | None
    options: list[str]


class Game(ABC):
    """Motor extensible: cada juego implementa construir rondas y calificar."""

    key: str = ""
    name: str = ""

    @abstractmethod
    async def build(self, db: AsyncSession, jukebox_id: int, now: datetime) -> RoundData:
        """Selecciona la respuesta secreta oculta tras sus opciones."""

    def grade(self, round_: GameRound, selected: str) -> bool:
        return selected == round_.title
