"""Orquestrador do turno (ADR-035): pipeline Python que coordena os
agentes ADK individualmente, intercalando etapas determinísticas.

O motivo de a orquestração não ser um BaseAgent/SequentialAgent do ADK
é a fronteira determinístico/LLM (ADR-003): "pular rolagem", "aplicar
consequência", "chamar NPC se há NPC reagindo" são decisões de fluxo,
não de julgamento.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sqlalchemy import select

from app.agents.contracts import (
    RetrievalSnippet,
    RollOutcome,
    Ruling,
    TurnEvent,
    TurnTrace,
)
from app.agents.robustness import RobustnessVerdict
from app.db.base import CampaignRow, TurnTraceRow
from app.db.engine import _async_session_factory
from app.providers.embedding import EmbeddingProvider
from app.rag.vector_store import search
from app.rules.checks import check
from app.rules.consequences import apply_consequence
from app.rules.dice import roll
from app.rules.proposals import ConsequenceProposal
from app.state.adventure_schema import NPC, Chapter
from app.state.models import GameState, HistoryEntry

logger = logging.getLogger(__name__)

APP_NAME = "unscripted"
DEFAULT_USER_ID = "anon"


class CampaignNotFoundError(Exception):
    pass


async def _fetch_corpus(
    corpus: str,
    query: str,
    k: int,
    embedder: EmbeddingProvider,
) -> list[RetrievalSnippet]:
    try:
        async with _async_session_factory() as session:
            hits = await search(
                session,
                corpus=corpus,
                query=query,
                k=k,
                embedder=embedder,
            )
        return [RetrievalSnippet(corpus=corpus, source=h.source, content=h.content) for h in hits]
    except Exception:
        logger.exception("Prefetch de %s falhou; seguindo sem contexto", corpus)
        return []


def _format_snippets(snippets: list[RetrievalSnippet]) -> str:
    if not snippets:
        return ""
    return "\n\n---\n\n".join(f"({s.source})\n{s.content}" for s in snippets)


def _state_summary(state: GameState, chapter: Chapter | None) -> str:
    parts = [
        f"Personagem: {state.character.name} ({state.character.character_class}), "
        f"nível {state.character.level}, HP {state.character.hp_current}/{state.character.hp_max}",
        f"Localização: {state.location.id} — {state.location.name}",
    ]
    if state.inventory:
        items = ", ".join(f"{i.name} x{i.quantity}" for i in state.inventory)
        parts.append(f"Inventário: {items}")
    if state.flags.objectives_completed:
        parts.append("Objetivos concluídos: " + ", ".join(state.flags.objectives_completed))
    if chapter is not None:
        scene = next((s for s in chapter.scenes if s.id == state.location.id), None)
        if scene and scene.present:
            parts.append("NPCs presentes: " + ", ".join(scene.present))
    if state.history:
        last = state.history[-2:]
        recap = "; ".join(f"[{h.turn}] {h.player_action} → {h.narration[:80]}..." for h in last)
        parts.append("Últimos turnos: " + recap)
    return "\n".join(parts)


def _format_npc_persona(npc: NPC) -> str:
    parts = [
        f"Nome: {npc.name}",
        f"Personalidade: {npc.personality}",
        f"Motivação: {npc.motivation}",
    ]
    if npc.knowledge:
        parts.append(f"Conhece: {npc.knowledge}")
    if npc.hidden_state.trait:
        parts.append(f"GM-only — traço: {npc.hidden_state.trait}")
    if npc.hidden_state.notes:
        parts.append(f"GM-only — notas: {npc.hidden_state.notes}")
    return "\n".join(parts)


def _lookup_npc(chapter: Chapter, npc_id: str) -> NPC | None:
    norm = npc_id.strip().lower()
    return next(
        (n for n in chapter.npcs if n.name.strip().lower() == norm),
        None,
    )


async def _set_state(
    session_service: DatabaseSessionService,
    campaign_id: str,
    delta: dict[str, object],
) -> None:
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=DEFAULT_USER_ID,
        session_id=campaign_id,
    )
    if session is None:
        raise CampaignNotFoundError(campaign_id)
    await session_service.append_event(
        session,
        Event(
            invocation_id="turn-state",
            author="system",
            actions=EventActions(state_delta=delta),
        ),
    )


async def _run_referee(runner: Runner, campaign_id: str) -> Ruling:
    msg = types.Content(role="user", parts=[types.Part(text="resolver turno")])
    final_text = ""
    async for event in runner.run_async(
        user_id=DEFAULT_USER_ID, session_id=campaign_id, new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text
            if text:
                final_text = text
    if not final_text:
        raise RuntimeError("RefereeAgent não retornou conteúdo")
    return Ruling.model_validate_json(final_text)


async def _stream_agent_text(
    runner: Runner, campaign_id: str, trigger: str
) -> AsyncGenerator[str, None]:
    msg = types.Content(role="user", parts=[types.Part(text=trigger)])
    async for event in runner.run_async(
        user_id=DEFAULT_USER_ID, session_id=campaign_id, new_message=msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    yield part.text


async def _persist_turn(
    campaign_id: str,
    state: GameState,
    trace: TurnTrace,
    player_action: str,
    narration: str,
    turn_number: int,
) -> None:
    async with _async_session_factory() as db:
        result = await db.execute(select(CampaignRow).where(CampaignRow.id == campaign_id))
        row = result.scalar_one_or_none()
        if row is None:
            return
        state.history.append(
            HistoryEntry(
                turn=turn_number,
                player_action=player_action,
                narration=narration,
            )
        )
        row.game_state = state.model_dump(mode="json")
        row.updated_at = datetime.now(UTC)
        db.add(
            TurnTraceRow(
                campaign_id=campaign_id,
                turn_number=turn_number,
                trace=trace.model_dump(mode="json"),
            )
        )
        await db.commit()


async def _persist_failed_trace(campaign_id: str, turn_number: int, trace: TurnTrace) -> None:
    try:
        async with _async_session_factory() as db:
            db.add(
                TurnTraceRow(
                    campaign_id=campaign_id,
                    turn_number=turn_number,
                    trace=trace.model_dump(mode="json"),
                )
            )
            await db.commit()
    except Exception:
        logger.exception("Não foi possível persistir trace de falha")


async def process_turn(
    *,
    campaign_id: str,
    text: str,
    robustness: RobustnessVerdict,
    referee_runner: Runner,
    narrator_runner: Runner,
    npc_runner: Runner,
    session_service: DatabaseSessionService,
    embedder: EmbeddingProvider,
    chapter: Chapter | None,
    rag_top_k_lore: int,
    rag_top_k_rules: int,
) -> AsyncGenerator[TurnEvent, None]:
    """Pipeline determinístico do turno (ADR-035).

    Assume `robustness.ok=True`. O endpoint barra ações inválidas antes
    de invocar esta função. Em falha, o turno **não** é consumido
    (estado não muda, history não cresce) e um evento
    `error_preserve_input` é emitido.
    """
    async with _async_session_factory() as db:
        result = await db.execute(select(CampaignRow).where(CampaignRow.id == campaign_id))
        row = result.scalar_one_or_none()
    if row is None:
        raise CampaignNotFoundError(campaign_id)
    state = GameState.model_validate(row.game_state)
    turn_number = len(state.history) + 1

    rules_snippets = await _fetch_corpus("rules", text, rag_top_k_rules, embedder)
    lore_snippets = await _fetch_corpus("lore", text, rag_top_k_lore, embedder)
    summary = _state_summary(state, chapter)

    await _set_state(
        session_service,
        campaign_id,
        {
            "action": text,
            "rules_context": _format_snippets(rules_snippets),
            "state_summary": summary,
        },
    )

    narration_text = ""
    npc_text: str | None = None
    npc_id_used: str | None = None
    ruling: Ruling | None = None
    roll_outcome: RollOutcome | None = None
    consequence_applied: ConsequenceProposal | None = None
    npc_error: str | None = None

    # Fase crítica: Referee + Narrator. Falha aqui ⇒ turno NÃO consumido.
    try:
        async with asyncio.timeout(60):
            ruling = await _run_referee(referee_runner, campaign_id)

            if ruling.precisa_rolagem:
                assert ruling.dificuldade is not None
                roll_result = roll(ruling.notacao_dado)
                check_result = check(roll_result, ruling.dificuldade)
                roll_outcome = RollOutcome(roll=roll_result, check=check_result)
                chosen = (
                    ruling.consequencia_sucesso
                    if check_result.success
                    else ruling.consequencia_falha
                )
            else:
                chosen = ruling.consequencia
            assert chosen is not None

            state = apply_consequence(state, chosen)
            consequence_applied = chosen

            await _set_state(
                session_service,
                campaign_id,
                {
                    "lore_context": _format_snippets(lore_snippets),
                    "ruling": ruling.model_dump_json(),
                    "roll_outcome": roll_outcome.model_dump_json() if roll_outcome else "",
                    "consequence_applied": consequence_applied.model_dump_json(),
                },
            )
            async for chunk in _stream_agent_text(narrator_runner, campaign_id, "narrar turno"):
                narration_text += chunk
                yield TurnEvent(type="narration_chunk", text=chunk)
    except Exception as exc:
        logger.exception("Falha crítica no turno %s (Referee/Narrator)", campaign_id)
        partial = TurnTrace(
            turn=turn_number,
            player_action=text,
            robustness=robustness,
            retrieval_rules=rules_snippets,
            retrieval_lore=lore_snippets,
            ruling=ruling,
            roll_outcome=roll_outcome,
            consequence_applied=consequence_applied,
            narration=narration_text,
            error=f"{type(exc).__name__}: {exc}",
        )
        await _persist_failed_trace(campaign_id, turn_number, partial)
        yield TurnEvent(
            type="error_preserve_input",
            text=(
                "Tivemos um problema no processamento. Tente novamente — "
                "seu turno não foi consumido."
            ),
        )
        return

    # NPCActor é opcional: falha aqui não invalida a narração. Turno completa
    # sem reação, com o erro registrado no trace.
    if ruling.npc_to_react and chapter is not None:
        npc = _lookup_npc(chapter, ruling.npc_to_react)
        if npc is not None:
            npc_id_used = ruling.npc_to_react
            try:
                async with asyncio.timeout(45):
                    await _set_state(
                        session_service,
                        campaign_id,
                        {
                            "npc_persona": _format_npc_persona(npc),
                            "narration": narration_text,
                        },
                    )
                    collected = ""
                    async for chunk in _stream_agent_text(
                        npc_runner, campaign_id, "reagir como NPC"
                    ):
                        collected += chunk
                        yield TurnEvent(type="npc_chunk", text=chunk, npc_id=npc_id_used)
                    npc_text = collected
            except Exception as exc:
                logger.exception("NPCActor falhou no turno %s; turno segue sem reação", campaign_id)
                npc_error = f"{type(exc).__name__}: {exc}"

    trace = TurnTrace(
        turn=turn_number,
        player_action=text,
        robustness=robustness,
        retrieval_rules=rules_snippets,
        retrieval_lore=lore_snippets,
        ruling=ruling,
        roll_outcome=roll_outcome,
        consequence_applied=consequence_applied,
        narration=narration_text,
        npc_reaction=npc_text,
        npc_id=npc_id_used,
        error=npc_error,
    )
    try:
        await _persist_turn(campaign_id, state, trace, text, narration_text, turn_number)
    except Exception:
        logger.exception("Falha ao persistir turno %s", campaign_id)

    yield TurnEvent(type="turn_complete", turn_number=turn_number)
