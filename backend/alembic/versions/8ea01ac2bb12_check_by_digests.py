"""check-by-digests

Revision ID: 8ea01ac2bb12
Revises: c34cbd8ce5b4
Create Date: 2026-01-20 03:40:10.148941

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "8ea01ac2bb12"
down_revision: Union[str, Sequence[str], None] = "c34cbd8ce5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.drop_column("notified_available_digests")
        batch_op.add_column(
            sa.Column("local_digests", sa.JSON(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("remote_digests", sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.drop_column("local_digests")
        batch_op.drop_column("remote_digests")
        batch_op.add_column(
            sa.Column(
                "notified_available_digests", sa.JSON(), nullable=True
            )
        )
