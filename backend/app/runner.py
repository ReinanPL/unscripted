from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from app.agents.narrator import build_narrator_agent
from app.config import Settings
from app.db.engine import _async_session_factory
from app.providers.embedding import EmbeddingProvider
from app.providers.llm import LlmProvider
from app.rag.vector_store import search

logger = logging.getLogger(__name__)

APP_NAME = "unscripted"
DEFAULT_USER_ID = "anon"

_session_service: DatabaseSessionService | None = None
_runner: Runner | None = None
_embedder: EmbeddingProvider | None = None
_settings: Settings | None = None


class CampaignNotFoundError(Exception):
    pass


def init_runner(provider: LlmProvider, settings: Settings, embedder: EmbeddingProvider) -> None:
    global _runner, _session_service, _embedder, _settings
    _session_service = DatabaseSessionService(db_url=settings.database_url)
    _embedder = embedder
    _settings = settings
    _runner = Runner(
        app_name=APP_NAME,
        agent=build_narrator_agent(provider),
        session_service=_session_service,
    )


async def create_adk_session(campaign_id: str) -> None:
    assert _session_service is not None, "init_runner() não foi chamado"
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=DEFAULT_USER_ID,
        session_id=campaign_id,
        state={"lore_context": ""},
    )


async def _fetch_lore_context(query: str) -> str:
    """Prefetch determinístico do corpus de lore (ADR-031).

    Retorna string vazia se a busca não tiver resultados ou se o RAG falhar
    — o agente segue narrando, apenas sem grounding extra.
    """
    assert _embedder is not None and _settings is not None
    try:
        async with _async_session_factory() as session:
            hits = await search(
                session,
                corpus="lore",
                query=query,
                k=_settings.rag_top_k_lore,
                embedder=_embedder,
            )
        if not hits:
            return ""
        formatted = "\n\n---\n\n".join(f"({h.source})\n{h.content}" for h in hits)
        return formatted
    except Exception:
        logger.exception("Prefetch de lore falhou; agente seguirá sem contexto")
        return ""


async def stream_turn(campaign_id: str, text: str) -> AsyncGenerator[str, None]:
    assert _runner is not None, "init_runner() não foi chamado no startup"
    assert _session_service is not None, "init_runner() não foi chamado no startup"

    session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id=DEFAULT_USER_ID,
        session_id=campaign_id,
    )
    if session is None:
        raise CampaignNotFoundError(campaign_id)

    lore_context = await _fetch_lore_context(text)
    await _session_service.append_event(
        session,
        Event(
            invocation_id="lore-prefetch",
            author="system",
            actions=EventActions(state_delta={"lore_context": lore_context}),
        ),
    )

    message = types.Content(role="user", parts=[types.Part(text=text)])

    try:
        async with asyncio.timeout(60):
            async for event in _runner.run_async(
                user_id=DEFAULT_USER_ID,
                session_id=campaign_id,
                new_message=message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            yield part.text
    except TimeoutError:
        yield "\n[Narração interrompida: tempo de resposta excedido.]"
