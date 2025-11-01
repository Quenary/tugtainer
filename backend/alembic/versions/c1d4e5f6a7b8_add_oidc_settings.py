"""add_oidc_settings

Revision ID: c1d4e5f6a7b8
Revises: b8dc3f40419f
Create Date: 2025-10-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1d4e5f6a7b8'
down_revision = 'b8dc3f40419f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add OIDC settings to the settings table."""
    op.execute(
        sa.text(
            """
        INSERT INTO settings (key, value, value_type) VALUES
        ('OIDC_ENABLED', 'FALSE', 'bool'),
        ('OIDC_WELL_KNOWN_URL', '', 'str'),
        ('OIDC_CLIENT_ID', '', 'str'),
        ('OIDC_CLIENT_SECRET', '', 'str'),
        ('OIDC_REDIRECT_URI', '', 'str'),
        ('OIDC_SCOPES', 'openid profile email', 'str')
        """
        )
    )


def downgrade() -> None:
    """Remove OIDC settings from the settings table."""
    op.execute(
        sa.text(
            """
        DELETE FROM settings WHERE key IN (
            'OIDC_ENABLED',
            'OIDC_WELL_KNOWN_URL', 
            'OIDC_CLIENT_ID',
            'OIDC_CLIENT_SECRET',
            'OIDC_REDIRECT_URI',
            'OIDC_SCOPES'
        )
        """
        )
    )