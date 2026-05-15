from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from app.agents.narrator import build_narrator_agent
from app.config import Settings
from app.providers.llm import LlmProvider

APP_NAME = "unscripted"
DEFAULT_USER_ID = "anon"

_session_service: DatabaseSessionService | None = None
_runner: Runner | None = None


class CampaignNotFoundError(Exception):
    pass


def init_runner(provider: LlmProvider, settings: Settings) -> None:
    global _runner, _session_service
    _session_service = DatabaseSessionService(db_url=settings.database_url)
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
        state={},
    )


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
