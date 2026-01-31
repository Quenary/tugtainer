"""update only running switch

Revision ID: 4020a740da76
Revises: cdb22157557a
Create Date: 2026-01-31 04:20:05.445601

"""

from typing import Sequence, Union
from backend.enums.settings_enum import ESettingKey, ESettingType
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4020a740da76"
down_revision: Union[str, Sequence[str], None] = "cdb22157557a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            """
            INSERT INTO settings (key, value, value_type) VALUES (:key, :value, :value_type)
            """
        ).bindparams(
            key=ESettingKey.UPDATE_ONLY_RUNNING.value,
            value="TRUE",
            value_type=ESettingType.BOOL,
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            DELETE FROM settings WHERE key == :key
            """
        ).bindparams(key=ESettingKey.UPDATE_ONLY_RUNNING.value)
    )
