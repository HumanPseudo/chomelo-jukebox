"""0012 colapsar a dos roles: ADMIN y MEMBER

OWNER y MODERATOR pasan a ADMIN; GUEST pasa a MEMBER. No hay columna de
tipo enum en la base de datos (`role` es `String(20)`), así que esto es
una migración de datos, no de esquema.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_two_roles"
down_revision = "0011_boost"
branch_labels = None
depends_on = None

_members = sa.table(
    "jukebox_members",
    sa.column("role", sa.String),
)


def upgrade() -> None:
    op.execute(
        _members.update().where(_members.c.role.in_(["OWNER", "MODERATOR"])).values(role="ADMIN")
    )
    op.execute(_members.update().where(_members.c.role == "GUEST").values(role="MEMBER"))


def downgrade() -> None:
    # Colapsar OWNER/MODERATOR/GUEST en dos roles pierde la distinción
    # original — no hay forma correcta de "deshacer" esto sin ese dato,
    # así que el downgrade es intencionalmente un no-op.
    pass
