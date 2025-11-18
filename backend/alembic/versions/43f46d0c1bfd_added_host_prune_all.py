"""added host.prune_all

Revision ID: 43f46d0c1bfd
Revises: 74c15c1c767e
Create Date: 2025-11-18 02:05:40.678029

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "43f46d0c1bfd"
down_revision: Union[str, Sequence[str], None] = "74c15c1c767e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "prune_all",
                sa.Boolean(),
                default=False,
                server_default=sa.text("(FALSE)"),
                nullable=False,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.drop_column("prune_all")
