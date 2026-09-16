from datetime import datetime

from pydantic import BaseModel, Field


class RoundStartRequest(BaseModel):
    duration_seconds: int | None = Field(default=60, ge=10, le=300)


class AnswerRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class MyAttemptOut(BaseModel):
    selected: str
    correct: bool
    points: int = 0


class RoundOut(BaseModel):
    id: int
    jukebox_id: int
    game_key: str
    game_name: str
    status: str
    track_id: str
    artist: str = ""
    thumbnail_url: str | None = None
    options: list[str]
    starts_at: datetime
    expires_at: datetime
    finished_at: datetime | None = None
    created_by: int
    my_attempt: MyAttemptOut | None = None
    correct_title: str | None = None


class AttemptOut(BaseModel):
    round_id: int
    selected: str
    correct: bool
    points: int = 0
    correct_title: str | None = None
    round_status: str
