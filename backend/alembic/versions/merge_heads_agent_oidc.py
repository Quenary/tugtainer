"""Merge agent and OIDC migrations

Revision ID: d2e3f4a5b6c7
Revises: 74c15c1c767e, c1d4e5f6a7b8
Create Date: 2025-11-01 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = ('74c15c1c767e', 'c1d4e5f6a7b8')
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migration - no changes needed as both previous migrations are independent."""
    pass


def downgrade() -> None:
    """Merge migration - no changes needed as both previous migrations are independent."""
    pass
