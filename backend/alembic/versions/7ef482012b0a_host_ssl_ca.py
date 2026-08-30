"""host ssl ca

Revision ID: 7ef482012b0a
Revises: f70a24f62037
Create Date: 2026-08-28 16:47:12.222716

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7ef482012b0a"
down_revision: str | Sequence[str] | None = "f70a24f62037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.add_column(sa.Column("ssl_ca", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.drop_column("ssl_ca")
