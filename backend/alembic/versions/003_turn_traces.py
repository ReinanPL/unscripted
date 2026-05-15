"""create turn_traces table

Revision ID: 003
Revises: 002
Create Date: 2026-05-15

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "turn_traces",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "campaign_id",
            sa.String(36),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_number", sa.Integer, nullable=False),
        sa.Column("trace", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "campaign_id", "turn_number", name="turn_traces_campaign_turn_uq"
        ),
    )


def downgrade() -> None:
    op.drop_table("turn_traces")
