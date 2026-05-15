"""Wiring do ADK: cria os 3 Runners (Referee, Narrator, NPCActor) sobre
um único DatabaseSessionService. A orquestração do turno vive em
`runner_turn.py` (ADR-035).
"""

from __future__ import annotations

import logging
import pathlib

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

from app.agents.narrator import build_narrator_agent
from app.agents.npc import build_npc_agent
from app.agents.referee import build_referee_agent
from app.config import Settings
from app.providers.embedding import EmbeddingProvider
from app.providers.llm import LlmProvider
from app.providers.voice import VoiceProvider, get_voice_provider
from app.runner_turn import APP_NAME, DEFAULT_USER_ID, CampaignNotFoundError
from app.state.adventure_schema import Adventure, Chapter

logger = logging.getLogger(__name__)

__all__ = [
    "APP_NAME",
    "CampaignNotFoundError",
    "DEFAULT_USER_ID",
    "create_adk_session",
    "get_active_chapter",
    "get_embedder",
    "get_npc_runner",
    "get_narrator_runner",
    "get_referee_runner",
    "get_session_service",
    "get_settings_cached",
    "get_voice_provider_cached",
    "init_runner",
]

_session_service: DatabaseSessionService | None = None
_referee_runner: Runner | None = None
_narrator_runner: Runner | None = None
_npc_runner: Runner | None = None
_embedder: EmbeddingProvider | None = None
_settings: Settings | None = None
_active_chapter: Chapter | None = None
_voice_provider: VoiceProvider | None = None


def _load_active_chapter() -> Chapter | None:
    """Carrega o primeiro capítulo da aventura inicial (v1: única aventura).

    Multi-aventura/multi-capítulo será resolvido quando o estado da sessão
    apontar para `chapter_id` específico — v2.
    """
    candidates = sorted(pathlib.Path("/app/content/chapters").glob("*/chapter.yaml"))
    if not candidates:
        return None
    try:
        adventure = Adventure.from_yaml(candidates[0])
        return adventure.chapters[0] if adventure.chapters else None
    except Exception:
        logger.exception("Falha ao carregar capítulo ativo de %s", candidates[0])
        return None


def init_runner(provider: LlmProvider, settings: Settings, embedder: EmbeddingProvider) -> None:
    global \
        _session_service, \
        _referee_runner, \
        _narrator_runner, \
        _npc_runner, \
        _embedder, \
        _settings, \
        _active_chapter, \
        _voice_provider
    _session_service = DatabaseSessionService(db_url=settings.database_url)
    _embedder = embedder
    _settings = settings
    _voice_provider = get_voice_provider(settings)
    _referee_runner = Runner(
        app_name=APP_NAME,
        agent=build_referee_agent(provider),
        session_service=_session_service,
    )
    _narrator_runner = Runner(
        app_name=APP_NAME,
        agent=build_narrator_agent(provider),
        session_service=_session_service,
    )
    _npc_runner = Runner(
        app_name=APP_NAME,
        agent=build_npc_agent(provider),
        session_service=_session_service,
    )
    _active_chapter = _load_active_chapter()


async def create_adk_session(campaign_id: str) -> None:
    assert _session_service is not None, "init_runner() não foi chamado"
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=DEFAULT_USER_ID,
        session_id=campaign_id,
        state={"lore_context": "", "rules_context": "", "state_summary": ""},
    )


def get_session_service() -> DatabaseSessionService:
    assert _session_service is not None, "init_runner() não foi chamado"
    return _session_service


def get_referee_runner() -> Runner:
    assert _referee_runner is not None, "init_runner() não foi chamado"
    return _referee_runner


def get_narrator_runner() -> Runner:
    assert _narrator_runner is not None, "init_runner() não foi chamado"
    return _narrator_runner


def get_npc_runner() -> Runner:
    assert _npc_runner is not None, "init_runner() não foi chamado"
    return _npc_runner


def get_embedder() -> EmbeddingProvider:
    assert _embedder is not None, "init_runner() não foi chamado"
    return _embedder


def get_settings_cached() -> Settings:
    assert _settings is not None, "init_runner() não foi chamado"
    return _settings


def get_active_chapter() -> Chapter | None:
    return _active_chapter


def get_voice_provider_cached() -> VoiceProvider:
    assert _voice_provider is not None, "init_runner() não foi chamado"
    return _voice_provider
