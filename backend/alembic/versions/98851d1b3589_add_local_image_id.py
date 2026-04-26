"""add local image id

Revision ID: 98851d1b3589
Revises: 8ea01ac2bb12
Create Date: 2026-01-24 01:31:16.104933

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "98851d1b3589"
down_revision: str | Sequence[str] | None = "8ea01ac2bb12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.add_column(
            sa.Column("image_id", sa.String(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.drop_column("image_id")
