"""Add client consent table and relay start timestamp

Revision ID: 3c8c9f4e1a2b
Revises: 0ef15b3117dd
Create Date: 2025-12-28 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3c8c9f4e1a2b"
down_revision: Union[str, None] = "0ef15b3117dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("device", sa.Column("relay_start_at", sa.TIMESTAMP(), nullable=True))

    op.create_table(
        "client_consent",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("consent_date", sa.Date(), nullable=False),
        sa.Column("consent_time", sa.Time(), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("agreed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["device.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_client_consent_owner_id", "client_consent", ["owner_id"])
    op.create_index("ix_client_consent_device_id", "client_consent", ["device_id"])
    op.create_index("ix_client_consent_consent_date", "client_consent", ["consent_date"])
    op.create_index("ix_client_consent_consent_time", "client_consent", ["consent_time"])
    op.create_index("ix_client_consent_email", "client_consent", ["email"])


def downgrade() -> None:
    op.drop_index("ix_client_consent_email", table_name="client_consent")
    op.drop_index("ix_client_consent_consent_time", table_name="client_consent")
    op.drop_index("ix_client_consent_consent_date", table_name="client_consent")
    op.drop_index("ix_client_consent_device_id", table_name="client_consent")
    op.drop_index("ix_client_consent_owner_id", table_name="client_consent")
    op.drop_table("client_consent")
    op.drop_column("device", "relay_start_at")
