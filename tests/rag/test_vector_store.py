"""Testes de integração do vector_store contra Postgres real.

Requer o Postgres do docker-compose rodando com pgvector e a migration 002
aplicada. Skipa se a env var DATABASE_URL_TEST não estiver presente.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import RagChunkRow
from app.rag.vector_store import (
    aggregate_hash,
    compute_hash,
    get_source_hash,
    search,
    upsert_source,
)


DATABASE_URL = os.environ.get("DATABASE_URL_TEST")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="DATABASE_URL_TEST não configurado — pule integração de pgvector.",
    ),
]


class FakeEmbedder:
    """Embedder de teste com vetores determinísticos por hash do texto.

    Sem dependência de sentence-transformers — torna os testes rápidos
    e independentes do modelo real.
    """

    dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            seed = sum(ord(c) for c in text) % 997
            vec = [((seed + i) % 7) / 7.0 for i in range(self.dim)]
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out


@pytest_asyncio.fixture
async def db_session():
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(RagChunkRow))
        await session.commit()
        yield session
        await session.execute(delete(RagChunkRow))
        await session.commit()
    await engine.dispose()


async def test_upsert_and_search_roundtrip(db_session):
    embedder = FakeEmbedder()
    chunks = ["alpha alpha alpha", "beta beta beta", "gamma gamma gamma"]
    inserted = await upsert_source(
        db_session,
        corpus="lore",
        source="test/a.md",
        chapter_id=None,
        chunks=chunks,
        embedder=embedder,
    )
    await db_session.commit()
    assert inserted == 3

    hits = await search(db_session, corpus="lore", query="alpha alpha alpha", k=1, embedder=embedder)
    assert len(hits) == 1
    assert hits[0].content == "alpha alpha alpha"


async def test_reupsert_replaces_old_chunks(db_session):
    embedder = FakeEmbedder()
    await upsert_source(
        db_session,
        corpus="lore",
        source="test/b.md",
        chapter_id=None,
        chunks=["one", "two", "three", "four"],
        embedder=embedder,
    )
    await db_session.commit()
    await upsert_source(
        db_session,
        corpus="lore",
        source="test/b.md",
        chapter_id=None,
        chunks=["new1", "new2"],
        embedder=embedder,
    )
    await db_session.commit()

    result = await db_session.execute(
        select(RagChunkRow.content)
        .where(RagChunkRow.source == "test/b.md")
        .order_by(RagChunkRow.chunk_index)
    )
    contents = [row[0] for row in result.all()]
    assert contents == ["new1", "new2"]


async def test_search_filters_by_corpus(db_session):
    embedder = FakeEmbedder()
    await upsert_source(
        db_session,
        corpus="lore",
        source="lore/x.md",
        chapter_id=None,
        chunks=["taverna escura"],
        embedder=embedder,
    )
    await upsert_source(
        db_session,
        corpus="rules",
        source="rules/y.md",
        chapter_id=None,
        chunks=["dificuldade média 15"],
        embedder=embedder,
    )
    await db_session.commit()

    lore_hits = await search(db_session, corpus="lore", query="taverna", k=5, embedder=embedder)
    rules_hits = await search(db_session, corpus="rules", query="taverna", k=5, embedder=embedder)
    assert all(h.source.startswith("lore/") for h in lore_hits)
    assert all(h.source.startswith("rules/") for h in rules_hits)


async def test_get_source_hash_matches_aggregate(db_session):
    embedder = FakeEmbedder()
    chunks = ["alpha", "beta", "gamma"]
    await upsert_source(
        db_session,
        corpus="lore",
        source="test/h.md",
        chapter_id=None,
        chunks=chunks,
        embedder=embedder,
    )
    await db_session.commit()
    stored = await get_source_hash(db_session, corpus="lore", source="test/h.md")
    expected = aggregate_hash([compute_hash(c) for c in chunks])
    assert stored == expected


async def test_get_source_hash_unknown_source_returns_none(db_session):
    result = await get_source_hash(db_session, corpus="lore", source="never/ingested.md")
    assert result is None


async def test_invalid_corpus_raises(db_session):
    with pytest.raises(ValueError):
        await upsert_source(
            db_session,
            corpus="invalid",
            source="x",
            chapter_id=None,
            chunks=["x"],
            embedder=FakeEmbedder(),
        )
