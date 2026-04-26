"""Separate jobs for check and update

Revision ID: 463265eb08b8
Revises: 4020a740da76
Create Date: 2026-03-03 01:28:44.979330

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from backend.modules.settings.settings_enum import (
    ESettingKey,
    ESettingType,
)

# revision identifiers, used by Alembic.
revision: str = "463265eb08b8"
down_revision: str | Sequence[str] | None = "4020a740da76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "UPDATE settings SET key = :new_key WHERE key == :old_key"
        ).bindparams(
            new_key=ESettingKey.CHECK_CRONTAB_EXPR.value,
            old_key="CRONTAB_EXPR",
        )
    )
    insert_text = "INSERT INTO settings (key, value, value_type) VALUES (:key, :value, :value_type)"
    op.execute(
        sa.text(
            insert_text,
        ).bindparams(
            key=ESettingKey.UPDATE_CRONTAB_EXPR.value,
            value="0 7 * * *",
            value_type=ESettingType.STR.value,
        )
    )
    op.execute(
        sa.text(
            insert_text,
        ).bindparams(
            key=ESettingKey.PULL_BEFORE_CHECK.value,
            value=False,
            value_type=ESettingType.BOOL.value,
        )
    )
    op.execute(
        sa.text(
            insert_text,
        ).bindparams(
            key=ESettingKey.REGISTRY_REQ_DELAY.value,
            value=5,
            value_type=ESettingType.INT.value,
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "UPDATE settings SET key = :new_key WHERE key == :old_key"
        ).bindparams(
            new_key="CRONTAB_EXPR",
            old_key=ESettingKey.CHECK_CRONTAB_EXPR.value,
        )
    )
    delete_text = "DELETE FROM settings WHERE key == :key"
    op.execute(
        sa.text(delete_text).bindparams(
            key=ESettingKey.UPDATE_CRONTAB_EXPR.value
        )
    )
    op.execute(
        sa.text(delete_text).bindparams(
            key=ESettingKey.PULL_BEFORE_CHECK.value
        )
    )
    op.execute(
        sa.text(delete_text).bindparams(
            key=ESettingKey.REGISTRY_REQ_DELAY.value
        )
    )
