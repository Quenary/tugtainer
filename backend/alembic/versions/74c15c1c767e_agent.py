"""agent

Revision ID: 74c15c1c767e
Revises: b8dc3f40419f
Create Date: 2025-10-27 22:00:41.764622

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "74c15c1c767e"
down_revision: Union[str, Sequence[str], None] = "b8dc3f40419f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    hosts = conn.execute(sa.text("SELECT id, host FROM hosts")).all()
    if hosts:
        not_local = [item for item in hosts if item[1]]
        for nl in not_local:
            conn.execute(
                sa.text(
                    "DELETE FROM containers WHERE host_id = :hid"
                ),
                {"hid": nl[0]},
            )
            conn.execute(
                sa.text("DELETE FROM hosts WHERE id = :hid"),
                {"hid": nl[0]},
            )

    with op.batch_alter_table("hosts", schema=None) as batch_op:
        batch_op.drop_column("config")
        batch_op.drop_column("context")
        batch_op.drop_column("host")
        batch_op.drop_column("tls")
        batch_op.drop_column("tlscacert")
        batch_op.drop_column("tlscert")
        batch_op.drop_column("tlskey")
        batch_op.drop_column("tlsverify")
        batch_op.drop_column("client_binary")
        batch_op.drop_column("client_call")
        batch_op.drop_column("client_type")
        batch_op.add_column(
            sa.Column("url", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("secret", sa.String(), nullable=True)
        )

    conn.execute(
        sa.text("UPDATE hosts SET url = 'http://127.0.0.1:8001'")
    )
    with op.batch_alter_table("hosts", schema=None) as batch_op:
        batch_op.alter_column(
            "url", existing_type=sa.String(), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.drop_column("url")
        batch_op.drop_column("secret")
        batch_op.add_column(
            sa.Column("config", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("context", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("host", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("tls", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("tlscacert", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("tlscert", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("tlskey", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("tlsverify", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("client_binary", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "client_call",
                sa.JSON,
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("client_type", sa.String(), nullable=True)
        )
