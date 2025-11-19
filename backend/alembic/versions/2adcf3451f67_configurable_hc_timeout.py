"""configurable hc timeout

Revision ID: 2adcf3451f67
Revises: 43f46d0c1bfd
Create Date: 2025-11-19 22:24:19.926394

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2adcf3451f67"
down_revision: Union[str, Sequence[str], None] = "43f46d0c1bfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "container_hc_timeout",
                sa.Integer(),
                default=60,
                server_default=sa.text("(60)"),
                nullable=False,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.drop_column("container_hc_timeout")
