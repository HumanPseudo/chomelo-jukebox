from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    resource_type: str | None
    resource_id: str | None
    detail: dict | None
    ip: str | None
    user_agent: str | None
    request_id: str | None
    created_at: datetime
