from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.audit import AuditOut
from app.domain.audit import AuditLog
from app.infra.request import get_client_ip


def _clean_ip(raw: str | None) -> str | None:
    if raw is None:
        return None
    return raw[:45]


def _clean_ua(raw: str | None) -> str | None:
    if raw is None:
        return None
    # Evitar log injection con cabeceras controladas por el cliente.
    return "".join(c for c in raw if c.isprintable())[:255]


async def log_action(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict | None = None,
    request: Request | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    if request is not None:
        request_id = request_id or getattr(request.state, "request_id", None) or ""
        ip = ip or get_client_ip(request)
        user_agent = user_agent or request.headers.get("user-agent")
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            detail=detail,
            ip=_clean_ip(ip),
            user_agent=_clean_ua(user_agent),
            request_id=(request_id or "")[:64] or None,
        )
    )


async def list_audit(
    db: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    action: str | None = None,
) -> list[AuditOut]:
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        AuditOut(
            id=row.id,
            user_id=row.user_id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            detail=row.detail,
            ip=row.ip,
            user_agent=row.user_agent,
            request_id=row.request_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
