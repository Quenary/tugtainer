"""remove_oidc_settings

Revision ID: d2e3f4g5h6i7
Revises: c1d4e5f6a7b8
Create Date: 2025-11-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd2e3f4g5h6i7'
down_revision = 'c1d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove OIDC settings as they are now configured via environment variables."""
    # Remove OIDC settings from the database
    op.execute("DELETE FROM settings WHERE key IN ('OIDC_ENABLED', 'OIDC_WELL_KNOWN_URL', 'OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET', 'OIDC_REDIRECT_URI', 'OIDC_SCOPES')")


def downgrade() -> None:
    """Re-add OIDC settings to database (not recommended as they should use env vars)."""
    # Insert OIDC settings with default values
    op.execute("""
        INSERT OR IGNORE INTO settings (key, value, value_type, modified_at) VALUES
        ('OIDC_ENABLED', 'FALSE', 'bool', datetime('now')),
        ('OIDC_WELL_KNOWN_URL', '', 'str', datetime('now')),
        ('OIDC_CLIENT_ID', '', 'str', datetime('now')),
        ('OIDC_CLIENT_SECRET', '', 'str', datetime('now')),
        ('OIDC_REDIRECT_URI', '', 'str', datetime('now')),
        ('OIDC_SCOPES', 'openid profile email', 'str', datetime('now'))
    """)