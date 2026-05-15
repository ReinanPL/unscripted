"""create rag_chunks table and pgvector extension

Revision ID: 002
Revises: 001
Create Date: 2026-05-15

"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("corpus", sa.String(20), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("chapter_id", sa.String(64), nullable=True),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "chunk_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("corpus IN ('rules','lore')", name="rag_chunks_corpus_check"),
        sa.UniqueConstraint("corpus", "source", "chunk_index", name="rag_chunks_source_chunk_uq"),
    )
    op.create_index("rag_chunks_corpus_idx", "rag_chunks", ["corpus"])
    op.execute(
        "CREATE INDEX rag_chunks_embedding_idx ON rag_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS rag_chunks_embedding_idx")
    op.drop_index("rag_chunks_corpus_idx", table_name="rag_chunks")
    op.drop_table("rag_chunks")
