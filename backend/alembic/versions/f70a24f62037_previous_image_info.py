"""previous image info

Revision ID: f70a24f62037
Revises: a1b2c3d4e5f6
Create Date: 2026-08-23 14:50:30.184808

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f70a24f62037"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.add_column(
            sa.Column(
                "previous_image_digests",
                sa.JSON(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "previous_image_tags",
                sa.JSON(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "previous_image_version",
                sa.String(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.drop_column("previous_image_version")
        batch_op.drop_column("previous_image_tags")
        batch_op.drop_column("previous_image_digests")
