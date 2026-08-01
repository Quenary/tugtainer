"""container hooks

Revision ID: 08648d4c4d99
Revises: b9034fe596ee
Create Date: 2026-07-30 22:31:09.461582

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "08648d4c4d99"
down_revision: str | Sequence[str] | None = "b9034fe596ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.add_column(
            sa.Column(
                "hooks",
                sa.JSON(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.drop_column("hooks")
