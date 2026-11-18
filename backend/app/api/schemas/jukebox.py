from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.jukebox import Role


class JukeboxCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class JukeboxUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    add_track_cooldown_seconds: int | None = Field(default=None, ge=0)
    add_track_cost_credits: int | None = Field(default=None, ge=0)
    boost_cost_credits: int | None = Field(default=None, ge=0)
    credit_price_cents: int | None = Field(default=None, ge=1)


class JukeboxJoin(BaseModel):
    invite_code: str = Field(min_length=4, max_length=8)


class JukeboxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    owner_id: int
    invite_code: str
    is_active: bool
    add_track_cooldown_seconds: int = 0
    add_track_cost_credits: int = 5
    boost_cost_credits: int = 10
    credit_price_cents: int = 10
    created_at: datetime
    role: str
    member_count: int


class MemberOut(BaseModel):
    user_id: int
    role: str
    display_name: str = ""


class RoleUpdate(BaseModel):
    role: Role
