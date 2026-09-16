from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=500)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    display_name: str
    avatar_url: str | None = None
    bio: str = ""
    xp: int = 0
    level: int = 1
    created_at: datetime
    tracks_added: int = 0
    tracks_played: int = 0
    votes_cast: int = 0
    polls_created: int = 0
    poll_votes_cast: int = 0


class ListenHistoryItem(BaseModel):
    track_id: str
    title: str
    artist: str = ""
    thumbnail_url: str | None = None
    jukebox_name: str
    played_at: datetime
