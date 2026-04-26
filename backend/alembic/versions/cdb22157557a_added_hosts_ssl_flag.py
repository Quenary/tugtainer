"""added hosts.ssl flag

Revision ID: cdb22157557a
Revises: 98851d1b3589
Create Date: 2026-01-28 00:08:11.318293

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cdb22157557a"
down_revision: str | Sequence[str] | None = "98851d1b3589"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "ssl",
                sa.Boolean(),
                default=True,
                server_default=sa.text("TRUE"),
                nullable=False,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.drop_column("ssl")
