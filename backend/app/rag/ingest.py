"""Pipeline de ingestão para o RAG — política de erro granular (ADR-034).

Falha estrutural (modelo não carrega, banco indisponível, dependência ausente)
propaga e derruba o caller (startup do FastAPI ou CLI). Falha de conteúdo
individual (YAML inválido, schema malformado, arquivo ilegível) é capturada,
registrada em `IngestReport.falhas` e o pipeline continua.

CLI: `python -m app.rag.ingest`.
"""

from __future__ import annotations

import asyncio
import logging
import pathlib

import yaml
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.embedding import EmbeddingProvider
from app.rag.chunking import chunk_text
from app.rag.vector_store import (
    aggregate_hash,
    compute_hash,
    get_source_hash,
    upsert_source,
)
from app.state.adventure_schema import Adventure

logger = logging.getLogger(__name__)


class IngestFailure(BaseModel):
    source: str
    error_type: str
    message: str


class IngestReport(BaseModel):
    processados: int = 0
    skipados: int = 0
    falhas: list[IngestFailure] = Field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Ingestão: {self.processados} ok, {self.skipados} sem mudança, "
            f"{len(self.falhas)} falhas"
            + (
                ": " + "; ".join(f"{f.source} ({f.error_type})" for f in self.falhas)
                if self.falhas
                else ""
            )
        )


async def _ingest_one_source(
    session: AsyncSession,
    *,
    corpus: str,
    source: str,
    chapter_id: str | None,
    text: str,
    embedder: EmbeddingProvider,
    base_metadata: dict[str, str] | None = None,
) -> str:
    """Ingere um único source. Retorna 'inserido', 'skipado'.

    Falhas estruturais propagam (banco fora, embedder não carrega).
    """
    chunks = chunk_text(text)
    if not chunks:
        return "skipado"
    new_hash = aggregate_hash([compute_hash(c) for c in chunks])
    existing_hash = await get_source_hash(session, corpus=corpus, source=source)
    if existing_hash == new_hash:
        return "skipado"
    await upsert_source(
        session,
        corpus=corpus,
        source=source,
        chapter_id=chapter_id,
        chunks=chunks,
        embedder=embedder,
        base_metadata=base_metadata,
    )
    return "inserido"


async def ingest_srd(
    session: AsyncSession,
    base_dir: pathlib.Path,
    embedder: EmbeddingProvider,
    report: IngestReport,
) -> None:
    if not base_dir.exists():
        return
    for path in sorted(base_dir.rglob("*.md")):
        rel = path.relative_to(base_dir.parent).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
            outcome = await _ingest_one_source(
                session,
                corpus="rules",
                source=rel,
                chapter_id=None,
                text=text,
                embedder=embedder,
            )
            if outcome == "inserido":
                report.processados += 1
            else:
                report.skipados += 1
        except (OSError, UnicodeDecodeError) as exc:
            report.falhas.append(
                IngestFailure(source=rel, error_type=type(exc).__name__, message=str(exc))
            )
            logger.exception("Falha de conteúdo em %s", rel)


async def ingest_chapters(
    session: AsyncSession,
    base_dir: pathlib.Path,
    embedder: EmbeddingProvider,
    report: IngestReport,
) -> None:
    if not base_dir.exists():
        return
    for chapter_dir in sorted(p for p in base_dir.iterdir() if p.is_dir()):
        yaml_path = chapter_dir / "chapter.yaml"
        if not yaml_path.exists():
            continue
        rel = yaml_path.relative_to(base_dir.parent).as_posix()
        try:
            adventure = Adventure.from_yaml(yaml_path)
            for chapter in adventure.chapters:
                text = chapter.to_lore_text()
                outcome = await _ingest_one_source(
                    session,
                    corpus="lore",
                    source=f"{rel}#{chapter.id}",
                    chapter_id=chapter.id,
                    text=text,
                    embedder=embedder,
                    base_metadata={"adventure": adventure.id, "title": chapter.title},
                )
                if outcome == "inserido":
                    report.processados += 1
                else:
                    report.skipados += 1
        except (ValidationError, yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
            report.falhas.append(
                IngestFailure(source=rel, error_type=type(exc).__name__, message=str(exc))
            )
            logger.exception("Falha de conteúdo em %s", rel)


async def ingest_all(
    session: AsyncSession,
    content_root: pathlib.Path,
    embedder: EmbeddingProvider,
) -> IngestReport:
    """Ingere todo o conteúdo de `content_root`. Falhas de conteúdo não derrubam o pipeline (ADR-034)."""
    report = IngestReport()
    await ingest_srd(session, content_root / "srd", embedder, report)
    await ingest_chapters(session, content_root / "chapters", embedder, report)
    await session.commit()
    return report


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from app.config import get_settings
    from app.db.engine import _async_session_factory
    from app.providers import get_embedding_provider

    settings = get_settings()
    embedder = get_embedding_provider(settings)
    content_root = pathlib.Path(__file__).resolve().parents[2] / "content"
    if not content_root.exists():
        content_root = pathlib.Path("/app/content")
    async with _async_session_factory() as session:
        report = await ingest_all(session, content_root, embedder)
    logger.info(report.summary())


if __name__ == "__main__":
    asyncio.run(_main())
