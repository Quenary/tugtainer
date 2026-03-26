"""insecure registries

Revision ID: b9034fe596ee
Revises: 463265eb08b8
Create Date: 2026-03-26 23:19:03.376073

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.modules.settings.settings_enum import (
    ESettingKey,
    ESettingType,
)


# revision identifiers, used by Alembic.
revision: str = "b9034fe596ee"
down_revision: Union[str, Sequence[str], None] = "463265eb08b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value, value_type) VALUES (:key, :value, :value_type)"
        ).bindparams(
            key=ESettingKey.INSECURE_REGISTRIES.value,
            value="",
            value_type=ESettingType.STR.value,
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text("DELETE FROM settings WHERE key = :key").bindparams(
            key=ESettingKey.INSECURE_REGISTRIES.value,
        )
    )
