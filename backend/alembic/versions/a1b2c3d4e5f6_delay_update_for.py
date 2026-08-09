"""delay update for

Revision ID: a1b2c3d4e5f6
Revises: 08648d4c4d99
Create Date: 2026-08-09 23:58:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from backend.modules.settings.settings_enum import (
    ESettingKey,
    ESettingType,
)

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "08648d4c4d99"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            """
            INSERT INTO settings (key, value, value_type) VALUES (:key, :value, :value_type)
            """
        ).bindparams(
            key=ESettingKey.DELAY_UPDATE_FOR.value,
            value="0",
            value_type=ESettingType.INT,
        )
    )
    with op.batch_alter_table("containers") as batch_op:
        batch_op.add_column(
            sa.Column(
                "remote_digests_changed_at",
                sa.DateTime(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "delay_update_for",
                sa.Integer(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("containers") as batch_op:
        batch_op.drop_column("delay_update_for")
        batch_op.drop_column("remote_digests_changed_at")
    op.execute(
        sa.text(
            """
            DELETE FROM settings WHERE key == :key
            """
        ).bindparams(key=ESettingKey.DELAY_UPDATE_FOR.value)
    )
