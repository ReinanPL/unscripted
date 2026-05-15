"""Cliente do banco vetorial — escrita idempotente (ADR-032) e busca por similaridade.

A escrita usa delete-por-source dentro de transação: se um arquivo é
re-ingerido, todos os chunks antigos do mesmo (corpus, source) são apagados
antes de inserir os novos. Garantia: sem órfãos, sem duplicação.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RagChunkRow
from app.providers.embedding import EmbeddingProvider


def compute_hash(content: str) -> str:
    """Hash determinístico do conteúdo de um chunk, usado para auditoria."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ChunkHit(BaseModel):
    content: str
    source: str
    score: float
    chunk_metadata: dict[str, Any]


async def get_source_hash(session: AsyncSession, *, corpus: str, source: str) -> str | None:
    """Hash agregado de um source já indexado.

    Concatena os content_hash dos chunks na ordem de chunk_index. Permite
    o caller decidir se o conteúdo mudou e se precisa re-indexar (ADR-032).
    """
    result = await session.execute(
        select(RagChunkRow.content_hash)
        .where(RagChunkRow.corpus == corpus, RagChunkRow.source == source)
        .order_by(RagChunkRow.chunk_index)
    )
    hashes = [row[0] for row in result.all()]
    if not hashes:
        return None
    return hashlib.sha256("".join(hashes).encode("utf-8")).hexdigest()


def aggregate_hash(chunk_hashes: list[str]) -> str:
    """Hash agregado do source a partir dos hashes dos chunks (ordem importa)."""
    return hashlib.sha256("".join(chunk_hashes).encode("utf-8")).hexdigest()


async def upsert_source(
    session: AsyncSession,
    *,
    corpus: str,
    source: str,
    chapter_id: str | None,
    chunks: list[str],
    embedder: EmbeddingProvider,
    base_metadata: dict[str, Any] | None = None,
) -> int:
    """Apaga chunks antigos de (corpus, source) e insere os novos. Retorna a contagem inserida.

    Caller é responsável por gerenciar a transação (commit/rollback).
    """
    if corpus not in {"rules", "lore"}:
        raise ValueError(f"corpus inválido: {corpus!r}")
    if not chunks:
        await session.execute(
            delete(RagChunkRow).where(RagChunkRow.corpus == corpus, RagChunkRow.source == source)
        )
        return 0
    await session.execute(
        delete(RagChunkRow).where(RagChunkRow.corpus == corpus, RagChunkRow.source == source)
    )
    embeddings = embedder.embed(chunks)
    metadata = base_metadata or {}
    rows = [
        RagChunkRow(
            corpus=corpus,
            source=source,
            chapter_id=chapter_id,
            chunk_index=i,
            content=chunk,
            content_hash=compute_hash(chunk),
            embedding=emb,
            chunk_metadata=metadata,
        )
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings, strict=True))
    ]
    session.add_all(rows)
    return len(rows)


async def search(
    session: AsyncSession,
    *,
    corpus: str,
    query: str,
    k: int,
    embedder: EmbeddingProvider,
) -> list[ChunkHit]:
    """Busca top-k chunks do corpus por similaridade coseno com a query."""
    if not query.strip() or k <= 0:
        return []
    [vec] = embedder.embed([query])
    distance = RagChunkRow.embedding.cosine_distance(vec)
    stmt = (
        select(
            RagChunkRow.content,
            RagChunkRow.source,
            RagChunkRow.chunk_metadata,
            distance.label("distance"),
        )
        .where(RagChunkRow.corpus == corpus)
        .order_by(distance)
        .limit(k)
    )
    result = await session.execute(stmt)
    return [
        ChunkHit(
            content=row.content,
            source=row.source,
            score=1.0 - row.distance,
            chunk_metadata=row.chunk_metadata,
        )
        for row in result.all()
    ]
