"""Testes da ingestão do RAG, incluindo a política de erro granular (ADR-034).

Usa o Postgres do compose. Skipa se DATABASE_URL_TEST não estiver presente.
Usa FakeEmbedder para evitar baixar o modelo real.
"""

from __future__ import annotations

import os
import pathlib

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import RagChunkRow
from app.rag.ingest import ingest_all

DATABASE_URL = os.environ.get("DATABASE_URL_TEST")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="DATABASE_URL_TEST não configurado — pule integração de pgvector.",
    ),
]


class FakeEmbedder:
    dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            seed = sum(ord(c) for c in text) % 997
            vec = [((seed + i) % 7) / 7.0 for i in range(self.dim)]
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out


VALID_CHAPTER = """\
id: aventura-teste
title: Aventura de Teste
language: pt
chapters:
  - id: cap1
    title: Capítulo 1
    premise: x
    background: y
    starting_scene: s1
    progress_condition: z
    scenes:
      - id: s1
        name: Cena 1
        description: Uma descrição razoavelmente longa para gerar pelo menos um chunk.
"""

MALFORMED_CHAPTER = """\
id: aventura-quebrada
title: Quebrada
chapters:
  - id: cap1
    title: x
    starting_scene: s_inexistente
    scenes:
      - id: outra_cena
        name: x
        description: x
"""

SRD_FILE = "Texto de exemplo de regra com vários parágrafos.\n\nOutro parágrafo razoável."


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


@pytest.fixture
def content_root(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "content"
    (root / "srd").mkdir(parents=True)
    (root / "chapters" / "cap-bom").mkdir(parents=True)
    (root / "srd" / "regra.md").write_text(SRD_FILE, encoding="utf-8")
    (root / "chapters" / "cap-bom" / "chapter.yaml").write_text(
        VALID_CHAPTER, encoding="utf-8"
    )
    return root


async def test_ingest_all_processes_rules_and_lore(db_session, content_root):
    report = await ingest_all(db_session, content_root, FakeEmbedder())
    assert report.processados >= 2
    assert report.falhas == []
    rows = await db_session.execute(select(RagChunkRow.corpus))
    corpora = {row[0] for row in rows.all()}
    assert corpora == {"rules", "lore"}


async def test_malformed_chapter_skipped_not_fatal(
    db_session, content_root: pathlib.Path
):
    """ADR-034: capítulo malformado vai para falhas; pipeline conclui sem exceção."""
    bad_dir = content_root / "chapters" / "cap-quebrado"
    bad_dir.mkdir()
    (bad_dir / "chapter.yaml").write_text(MALFORMED_CHAPTER, encoding="utf-8")

    report = await ingest_all(db_session, content_root, FakeEmbedder())

    assert report.processados >= 2
    assert len(report.falhas) == 1
    assert "cap-quebrado" in report.falhas[0].source
    assert report.falhas[0].error_type == "ValidationError"
    rows = await db_session.execute(
        select(RagChunkRow).where(RagChunkRow.source.like("%cap-quebrado%"))
    )
    assert rows.all() == []


async def test_reingestion_is_idempotent(db_session, content_root):
    embedder = FakeEmbedder()
    first = await ingest_all(db_session, content_root, embedder)
    assert first.processados >= 2
    second = await ingest_all(db_session, content_root, embedder)
    assert second.processados == 0
    assert second.skipados >= 2

    count = await db_session.execute(select(RagChunkRow))
    rows = count.all()
    assert len(rows) >= 2


async def test_ingest_summary_includes_failures():
    from app.rag.ingest import IngestFailure, IngestReport

    report = IngestReport(
        processados=3,
        skipados=1,
        falhas=[IngestFailure(source="x.md", error_type="ValidationError", message="bad")],
    )
    msg = report.summary()
    assert "3 ok" in msg
    assert "1 sem mudança" in msg
    assert "1 falhas" in msg
    assert "x.md (ValidationError)" in msg
