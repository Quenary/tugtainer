"""multi host support

Revision ID: b8dc3f40419f
Revises: 0e88bae8a098
Create Date: 2025-10-13 02:41:37.218044

"""

from typing import Sequence, Union, cast
import os
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b8dc3f40419f"
down_revision: Union[str, Sequence[str], None] = "0e88bae8a098"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "hosts",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "prune",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("(FALSE)"),
        ),
        sa.Column("config", sa.String(), nullable=True),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("host", sa.String(), nullable=True),
        sa.Column("tls", sa.Boolean(), nullable=True),
        sa.Column("tlscacert", sa.String(), nullable=True),
        sa.Column("tlscert", sa.String(), nullable=True),
        sa.Column("tlskey", sa.String(), nullable=True),
        sa.Column("tlsverify", sa.Boolean(), nullable=True),
        sa.Column("client_binary", sa.String(), nullable=True),
        sa.Column(
            "client_call",
            sa.JSON,
            nullable=True,
        ),
        sa.Column("client_type", sa.String(), nullable=True),
    )

    if os.path.exists("/var/run/docker.sock"):
        print(
            "Local docker socket detected, adding default 'local' docker host entry to 'hosts' table"
        )
        op.execute(
            sa.text(
                "INSERT INTO hosts (name, enabled) VALUES ('local', TRUE)"
            )
        )

    op.drop_table("containers")

    op.create_table(
        "containers",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column(
            "check_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "update_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "update_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "host_id",
            sa.Integer(),
            sa.ForeignKey("hosts.id"),
            nullable=False,
        ),
    )

    op.execute(
        sa.text("DELETE FROM settings WHERE key = 'PRUNE_IMAGES'")
    )

    op.execute(
        sa.text(
            "INSERT INTO settings (key, value, value_type) VALUES ('DOCKER_TIMEOUT', '15', 'int')"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("containers")
    op.drop_table("hosts")
    op.create_table(
        "containers",
        sa.Column(
            "name",
            sa.String(),
            nullable=False,
            unique=True,
            primary_key=True,
        ),
        sa.Column(
            "check_enabled",
            sa.Boolean(),
            server_default=sa.text("(FALSE)"),
            nullable=False,
        ),
        sa.Column(
            "update_enabled",
            sa.Boolean(),
            server_default=sa.text("(FALSE)"),
            nullable=False,
        ),
        sa.Column(
            "update_available",
            sa.Boolean(),
            server_default=sa.text("(FALSE)"),
            nullable=False,
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            server_onupdate=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value, value_type) VALUES ('PRUNE_IMAGES', 'FALSE', 'bool')"
        )
    )
    op.execute(
        sa.text("DELETE FROM settings WHERE key = 'DOCKER_TIMEOUT'")
    )
