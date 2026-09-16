from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QueueAdd(BaseModel):
    track_id: str = Field(min_length=1, max_length=64)


class ItemMove(BaseModel):
    position: int = Field(ge=0)


class SeekRequest(BaseModel):
    position_ms: int = Field(ge=0)


class BoostRequest(BaseModel):
    credits: int = Field(ge=1, le=1000)


class QueueItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_id: str
    title: str
    artist: str
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    added_by: int
    status: str
    position: int | None = None
    created_at: datetime
    score: int = 0
    voted_by_me: bool = False
    boost: int = 0


class PlayerStateOut(BaseModel):
    is_playing: bool
    position_ms: int
    current_item_id: int | None = None


class QueueOut(BaseModel):
    items: list[QueueItemOut]
    player: PlayerStateOut
