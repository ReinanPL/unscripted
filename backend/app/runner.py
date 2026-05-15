from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.narrator import build_narrator_agent
from app.providers.llm import LlmProvider

APP_NAME = "unscripted"
DEFAULT_USER_ID = "anon"

_session_service: InMemorySessionService = InMemorySessionService()  # type: ignore[no-untyped-call]
_runner: Runner | None = None
_campaigns: dict[str, dict[str, str]] = {}


class CampaignNotFoundError(Exception):
    pass


def init_runner(provider: LlmProvider) -> None:
    global _runner
    _runner = Runner(
        app_name=APP_NAME,
        agent=build_narrator_agent(provider),
        session_service=_session_service,
    )


async def create_campaign() -> str:
    campaign_id = str(uuid4())
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=DEFAULT_USER_ID,
        session_id=campaign_id,
        state={},
    )
    _campaigns[campaign_id] = {"character": "guerreiro"}
    return campaign_id


async def stream_turn(campaign_id: str, text: str) -> AsyncGenerator[str, None]:
    if campaign_id not in _campaigns:
        raise CampaignNotFoundError(campaign_id)

    assert _runner is not None, "init_runner() não foi chamado no startup"

    message = types.Content(role="user", parts=[types.Part(text=text)])

    # Timeout de 60s por turno — se o LLM travar, cancela e libera o cliente
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
