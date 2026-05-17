"""Orquestrador do turno (ADR-035): pipeline Python que coordena os
agentes ADK individualmente, intercalando etapas determinísticas.

O motivo de a orquestração não ser um BaseAgent/SequentialAgent do ADK
é a fronteira determinístico/LLM (ADR-003): "pular rolagem", "aplicar
consequência", "chamar NPC se há NPC reagindo" são decisões de fluxo,
não de julgamento.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TypedDict

from google.adk.agents.run_config import RunConfig, StreamingMode
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
from app.agents.sentence_buffer import SentenceBuffer
from app.db.base import CampaignRow, TurnTraceRow
from app.db.engine import _async_session_factory
from app.providers.embedding import EmbeddingProvider
from app.providers.tts import TtsProvider
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


class StreamStats(TypedDict):
    """Saída mutável do `_stream_with_audio` consumida pelo caller."""

    text: str
    next_sentence_index: int
    tts_errors: list[str]


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
    """Itera deltas do agente em modo SSE.

    Sem `streaming_mode=SSE`, o ADK consolida toda a resposta num
    único event final — o cliente percebe o texto chegando "de vez".
    Com SSE, cada delta vira um yield e a cadência editorial volta.

    Dois ramos só:
      - `text.startswith(yielded)` → evento cumulativo crescente (raro
        com LiteLlm+OpenAI; comum em outros adaptadores). Emite só o
        sufixo novo.
      - caso contrário → delta puro. Emite e acumula.

    A versão anterior tinha um terceiro ramo `elif text in yielded:
    continue` como suposta proteção contra "evento final cumulativo
    redundante". A medição mostrou que esse ramo:
      - disparou 102 vezes em um turno de ~256 events;
      - em 100% dos casos `text != yielded` E `text` não era sufixo
        cumulativo: eram deltas curtos legítimos (" e ", " de ",
        " ao ", " um ") cujas letras já apareciam em outras palavras
        do acumulado;
      - resultado: descartava conteúdo bom. Sem TTS o olho completava
        o texto e o bug passava despercebido (~12% dos chars perdidos
        no buffer interno; o frontend mostrava chunked junto). Com
        TTS, o `SentenceBuffer` lia frases corrompidas para sintetizar
        ("As paredes madeira" sem o "de") — surgiu como "comendo
        palavras" no áudio.
      - Bug existe desde a Fase 1 da v1; a voz revelou. Removido.

    Defesa em profundidade contra o cenário oposto (evento final
    cumulativo gigante caindo no `else` e duplicando frases) vive no
    `_stream_with_audio` via dedupe `(posição, frase)`.
    """
    msg = types.Content(role="user", parts=[types.Part(text=trigger)])
    run_config = RunConfig(streaming_mode=StreamingMode.SSE)
    yielded = ""
    async for event in runner.run_async(
        user_id=DEFAULT_USER_ID,
        session_id=campaign_id,
        new_message=msg,
        run_config=run_config,
    ):
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            text = part.text
            if not text:
                continue
            if text.startswith(yielded):
                # Cumulativo crescente do ADK (raro com LiteLlm+OpenAI mas
                # acontece em alguns providers): emite só o sufixo novo.
                delta = text[len(yielded) :]
                if delta:
                    yield delta
                    yielded += delta
            else:
                # Delta puro. Caminho dominante com LiteLlm+OpenAI: cada
                # evento traz só o próximo pedaço de texto. Emite direto.
                yield text
                yielded += text


async def _stream_with_audio(
    *,
    runner: Runner,
    campaign_id: str,
    trigger: str,
    text_event_type: str,
    npc_id: str | None,
    tts_provider: TtsProvider | None,
    tts_voice: str,
    sentence_index_start: int,
    stats: StreamStats,
) -> AsyncGenerator[TurnEvent, None]:
    """Stream texto + (se `tts_provider`) audio_sentence em paralelo (ADR-048).

    Texto chega imediatamente conforme o LLM emite. Quando `tts_provider` é
    passado, o `SentenceBuffer` detecta fim de frase e dispara
    `asyncio.create_task` do TTS — emite o `audio_sentence` (base64 MP3)
    no mesmo gerador assim que cada áudio fica pronto, **em ordem de
    `sentence_index`**. Quando passado `None`, zero chamadas TTS.

    `stats` é mutado pra devolver ao caller:
        - `stats["text"]` (str): texto acumulado de tudo que foi yieldado.
        - `stats["next_sentence_index"]` (int): próximo índice livre.
        - `stats["tts_errors"]` (list[str]): falhas individuais de frase.

    Reordenação garantida no backend: se a frase N fica pronta antes da
    N-1, segura no buffer e só emite depois — o frontend pode confiar
    em FIFO.
    """
    queue: asyncio.Queue[TurnEvent | None] = asyncio.Queue()
    pending: list[asyncio.Task[None]] = []
    ready: dict[int, TurnEvent | None] = {}
    sentence_buffer = SentenceBuffer()
    next_to_emit = sentence_index_start
    next_to_assign = sentence_index_start
    tts_errors: list[str] = []
    text_acc = ""
    # Defesa em profundidade contra o cenário do "boom" (evento final
    # cumulativo gigante que cai no `else` de `_stream_agent_text` e
    # acaba sendo reprocessado pelo SentenceBuffer, gerando as MESMAS
    # frases nas MESMAS posições do buffer cumulativo). Chave = (posição
    # ordinal, frase normalizada). Mesma frase em posição diferente
    # ("Silêncio. Silêncio.") tem chaves distintas e sai normalmente.
    already_synthed: set[tuple[int, str]] = set()
    sentence_position = 0

    async def _release_in_order() -> None:
        nonlocal next_to_emit
        while next_to_emit in ready:
            ev = ready.pop(next_to_emit)
            if ev is not None:
                await queue.put(ev)
            next_to_emit += 1

    async def _synth(idx: int, sentence: str) -> None:
        if tts_provider is None:
            return
        try:
            audio = await tts_provider.synthesize(sentence, voice=tts_voice)
            if audio:
                ready[idx] = TurnEvent(
                    type="audio_sentence",
                    sentence_index=idx,
                    audio_b64=base64.b64encode(audio).decode("ascii"),
                    mime="audio/mpeg",
                )
            else:
                # TTS retornou vazio (texto sem som útil): pula esta frase
                # sem bloquear a ordem.
                ready[idx] = None
        except Exception as exc:
            logger.exception("TTS falhou na frase #%d", idx)
            tts_errors.append(f"frase {idx}: {type(exc).__name__}: {exc}")
            ready[idx] = None
        await _release_in_order()

    def _dispatch_synth(sentence: str) -> None:
        """Aplica dedupe `(posição, frase)` antes de criar a task de TTS.

        Frase duplicada na mesma posição (cenário do "boom") é skipada
        — não incrementa `next_to_assign` nem cria task. Frase repetida
        em outra posição (`"Silêncio. Silêncio."` legítimo) sai normal.
        """
        nonlocal sentence_position, next_to_assign
        key = (sentence_position, sentence.strip().lower())
        sentence_position += 1
        if key in already_synthed:
            return
        already_synthed.add(key)
        idx = next_to_assign
        next_to_assign += 1
        pending.append(asyncio.create_task(_synth(idx, sentence)))

    async def _stream() -> None:
        nonlocal text_acc
        try:
            async for chunk in _stream_agent_text(runner, campaign_id, trigger):
                text_acc += chunk
                await queue.put(TurnEvent(type=text_event_type, text=chunk, npc_id=npc_id))
                if tts_provider is not None:
                    for sentence in sentence_buffer.push(chunk):
                        _dispatch_synth(sentence)
            # Frase residual ao fim do stream do agente.
            if tts_provider is not None:
                residual = sentence_buffer.flush()
                if residual:
                    _dispatch_synth(residual)
            # Aguarda todas as tasks de TTS terminarem antes de sinalizar fim.
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        finally:
            await queue.put(None)

    streamer = asyncio.create_task(_stream())
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
    finally:
        if not streamer.done():
            streamer.cancel()
        stats["text"] = text_acc
        stats["next_sentence_index"] = next_to_assign
        stats["tts_errors"] = tts_errors


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
    tts_provider: TtsProvider | None = None,
    tts_voice: str = "",
    tts_enabled: bool = False,
) -> AsyncGenerator[TurnEvent, None]:
    """Pipeline determinístico do turno (ADR-035).

    Assume `robustness.ok=True`. O endpoint barra ações inválidas antes
    de invocar esta função. Em falha, o turno **não** é consumido
    (estado não muda, history não cresce) e um evento
    `error_preserve_input` é emitido.

    Quando `tts_enabled=True` e `tts_provider` é passado, dispara TTS por
    frase em paralelo ao stream do Narrator/NPC (ADR-048) — emite
    `audio_sentence` no mesmo gerador conforme cada áudio fica pronto,
    em ordem de `sentence_index`. Falha de TTS de uma frase **não**
    corrompe o turno: registra em `tts_errors` do trace e segue.
    """
    effective_tts = tts_provider if tts_enabled else None
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
    tts_errors_acc: list[str] = []
    next_sentence_idx = 0

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
            narrator_stats: StreamStats = {
                "text": "",
                "next_sentence_index": next_sentence_idx,
                "tts_errors": [],
            }
            async for ev in _stream_with_audio(
                runner=narrator_runner,
                campaign_id=campaign_id,
                trigger="narrar turno",
                text_event_type="narration_chunk",
                npc_id=None,
                tts_provider=effective_tts,
                tts_voice=tts_voice,
                sentence_index_start=next_sentence_idx,
                stats=narrator_stats,
            ):
                yield ev
            narration_text = narrator_stats["text"]
            next_sentence_idx = narrator_stats["next_sentence_index"]
            tts_errors_acc.extend(narrator_stats["tts_errors"])
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
                    npc_stats: StreamStats = {
                        "text": "",
                        "next_sentence_index": next_sentence_idx,
                        "tts_errors": [],
                    }
                    async for ev in _stream_with_audio(
                        runner=npc_runner,
                        campaign_id=campaign_id,
                        trigger="reagir como NPC",
                        text_event_type="npc_chunk",
                        npc_id=npc_id_used,
                        tts_provider=effective_tts,
                        tts_voice=tts_voice,
                        sentence_index_start=next_sentence_idx,
                        stats=npc_stats,
                    ):
                        yield ev
                    npc_text = npc_stats["text"]
                    next_sentence_idx = npc_stats["next_sentence_index"]
                    tts_errors_acc.extend(npc_stats["tts_errors"])
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
        tts_errors=tts_errors_acc,
    )
    try:
        await _persist_turn(campaign_id, state, trace, text, narration_text, turn_number)
    except Exception:
        logger.exception("Falha ao persistir turno %s", campaign_id)

    yield TurnEvent(type="turn_complete", turn_number=turn_number)
