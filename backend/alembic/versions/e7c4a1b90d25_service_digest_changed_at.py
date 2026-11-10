"""swarm service digest change time

Revision ID: e7c4a1b90d25
Revises: 554ba6b3dc03
Create Date: 2026-11-10 03:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7c4a1b90d25"
down_revision: str | Sequence[str] | None = "554ba6b3dc03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("swarm_services") as batch_op:
        batch_op.add_column(
            sa.Column("remote_digests_changed_at", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("swarm_services") as batch_op:
        batch_op.drop_column("remote_digests_changed_at")
