from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    phone_number: str = Field(pattern=r"^\+?[0-9]{7,15}$", max_length=32)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=100)


class LoginRequest(BaseModel):
    phone_number: str = Field(pattern=r"^\+?[0-9]{7,15}$", max_length=32)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str | None = None
    email: str | None = None
    is_active: bool
    is_superuser: bool = False
    created_at: datetime
    display_name: str = ""
