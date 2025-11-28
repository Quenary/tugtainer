"""notification-template-settings

Revision ID: c34cbd8ce5b4
Revises: 2adcf3451f67
Create Date: 2025-11-26 21:39:47.683226

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.const import DEFAULT_NOTIFICATION_TEMPLATE
from backend.enums.settings_enum import ESettingKey, ESettingType


# revision identifiers, used by Alembic.
revision: str = "c34cbd8ce5b4"
down_revision: Union[str, Sequence[str], None] = "2adcf3451f67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    stmt = sa.text(
        """
        INSERT INTO settings (key, value, value_type) VALUES (:key, :value, :value_type)
        """
    )
    conn.execute(
        stmt,
        {
            "key": ESettingKey.NOTIFICATION_BODY_TEMPLATE.value,
            "value": DEFAULT_NOTIFICATION_TEMPLATE,
            "value_type": ESettingType.STR.value,
        },
    )
    conn.execute(
        stmt,
        {
            "key": ESettingKey.NOTIFICATION_TITLE_TEMPLATE.value,
            "value": "Tugtainer",
            "value_type": ESettingType.STR.value,
        },
    )
    conn.execute(
        sa.text(
            """
            UPDATE settings SET key = 'NOTIFICATION_URLS'
            WHERE key = 'NOTIFICATION_URL'
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    stmt = sa.text(
        f"""
    DELETE FROM settings WHERE key in :keys
    """
    ).bindparams(sa.bindparam("keys", expanding=True))
    conn.execute(
        stmt,
        {
            "keys": [
                ESettingKey.NOTIFICATION_BODY_TEMPLATE.value,
                ESettingKey.NOTIFICATION_TITLE_TEMPLATE.value,
            ]
        },
    )
    conn.execute(
        sa.text(
            """
            UPDATE settings SET key = 'NOTIFICATION_URL'
            WHERE key = 'NOTIFICATION_URLS'
            """
        )
    )
