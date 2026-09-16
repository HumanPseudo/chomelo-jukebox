from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.jukebox import Role


class JukeboxCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class JukeboxUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


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
    created_at: datetime
    role: str
    member_count: int


class MemberOut(BaseModel):
    user_id: int
    role: str
    display_name: str = ""


class RoleUpdate(BaseModel):
    role: Role
