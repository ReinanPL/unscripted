from __future__ import annotations

import asyncio
import pathlib
from collections.abc import AsyncGenerator

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.robustness import validate_player_input
from app.api.graph import build_graph_response
from app.api.schemas import (
    ActionEvent,
    ActionRequest,
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignLogResponse,
    CampaignStateResponse,
    GraphResponse,
    TurnTraceResponse,
)
from app.db.base import CampaignRow, TurnTraceRow
from app.db.engine import get_db
from app.runner import (
    CampaignNotFoundError,
    create_adk_session,
    get_active_chapter,
    get_embedder,
    get_narrator_runner,
    get_npc_runner,
    get_referee_runner,
    get_session_service,
    get_settings_cached,
)
from app.runner_turn import process_turn
from app.state.models import Character, GameState, HiddenState, Location

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_CHARACTERS_DIR = pathlib.Path(__file__).parent.parent.parent / "content" / "characters"


def _load_character_yaml(character: str) -> dict:  # type: ignore[type-arg]
    path = _CHARACTERS_DIR / f"{character}.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def _build_initial_game_state(character: str) -> GameState:
    data = _load_character_yaml(character)
    return GameState(
        character=Character.model_validate(data),
        location=Location(id="start", name="Ponto de partida", description=""),
        hidden_state=HiddenState(),
    )


async def _get_campaign_or_404(campaign_id: str, db: AsyncSession) -> CampaignRow:
    result = await db.execute(select(CampaignRow).where(CampaignRow.id == campaign_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    return row


@router.post("", response_model=CampaignCreateResponse, status_code=201)
async def create_campaign_endpoint(
    body: CampaignCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> CampaignCreateResponse:
    game_state = _build_initial_game_state(body.character)
    row = CampaignRow(
        character_class=body.character,
        language="pt",
        game_state=game_state.model_dump(mode="json"),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await create_adk_session(row.id)
    return CampaignCreateResponse(campaign_id=row.id)


@router.post("/{campaign_id}/action", response_model=None)
async def action_endpoint(
    campaign_id: str,
    body: ActionRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse | JSONResponse:
    await _get_campaign_or_404(campaign_id, db)

    # ADR-026: heurística determinística barra ações abusivas, declarações
    # de resultado e conteúdo proibido antes de qualquer LLM.
    verdict = validate_player_input(body.text)
    if not verdict.ok:
        return JSONResponse(
            status_code=200,
            content=ActionEvent(
                type="rejected",
                text=verdict.reason,
                category=verdict.category,
            ).model_dump(),
        )

    settings = get_settings_cached()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            async for ev in process_turn(
                campaign_id=campaign_id,
                text=body.text,
                robustness=verdict,
                referee_runner=get_referee_runner(),
                narrator_runner=get_narrator_runner(),
                npc_runner=get_npc_runner(),
                session_service=get_session_service(),
                embedder=get_embedder(),
                chapter=get_active_chapter(),
                rag_top_k_lore=settings.rag_top_k_lore,
                rag_top_k_rules=settings.rag_top_k_rules,
            ):
                payload = _turn_event_to_sse(ev)
                yield payload
                if ev.type in ("turn_complete", "error_preserve_input"):
                    return
        except CampaignNotFoundError:
            yield (
                "data: "
                + ActionEvent(type="error", text="Campanha não encontrada.").model_dump_json()
                + "\n\n"
            ).encode()
            return
        except asyncio.CancelledError:
            return

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _turn_event_to_sse(ev: object) -> bytes:
    """Converte um TurnEvent em uma linha SSE."""
    from app.agents.contracts import TurnEvent

    assert isinstance(ev, TurnEvent)
    if ev.type == "narration_chunk":
        wire = ActionEvent(type="chunk", text=ev.text)
    elif ev.type == "npc_chunk":
        wire = ActionEvent(type="npc_chunk", text=ev.text, npc_id=ev.npc_id)
    elif ev.type == "error_preserve_input":
        wire = ActionEvent(type="error_preserve_input", text=ev.text)
    else:  # turn_complete
        wire = ActionEvent(type="done", turn_number=ev.turn_number)
    return f"data: {wire.model_dump_json()}\n\n".encode()


@router.get("/{campaign_id}/state", response_model=CampaignStateResponse)
async def get_state_endpoint(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> CampaignStateResponse:
    row = await _get_campaign_or_404(campaign_id, db)
    state = GameState.model_validate(row.game_state)
    return CampaignStateResponse(
        campaign_id=campaign_id,
        character=state.character,
        inventory=state.inventory,
        location=state.location,
        flags=state.flags,
    )


@router.get("/{campaign_id}/log", response_model=CampaignLogResponse)
async def get_log_endpoint(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> CampaignLogResponse:
    row = await _get_campaign_or_404(campaign_id, db)
    state = GameState.model_validate(row.game_state)
    return CampaignLogResponse(campaign_id=campaign_id, history=state.history)


@router.get("/{campaign_id}/graph", response_model=GraphResponse)
async def get_graph_endpoint(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> GraphResponse:
    """Subgrafo revelado de locações para o jogador (ADR-038).

    Filtra por `flags.locations_revealed`; nenhum nó ou aresta de cena
    não-revelada aparece no resultado.
    """
    row = await _get_campaign_or_404(campaign_id, db)
    state = GameState.model_validate(row.game_state)
    chapter = get_active_chapter()
    if chapter is None:
        raise HTTPException(
            status_code=503,
            detail="Nenhum capítulo ativo carregado no servidor.",
        )
    return build_graph_response(
        chapter,
        campaign_id=campaign_id,
        locations_revealed=list(state.flags.locations_revealed),
        current_location=state.location.id,
    )


@router.get("/{campaign_id}/turn/{turn_number}/trace", response_model=TurnTraceResponse)
async def get_turn_trace_endpoint(
    campaign_id: str,
    turn_number: int,
    db: AsyncSession = Depends(get_db),
) -> TurnTraceResponse:
    await _get_campaign_or_404(campaign_id, db)
    result = await db.execute(
        select(TurnTraceRow)
        .where(TurnTraceRow.campaign_id == campaign_id)
        .where(TurnTraceRow.turn_number == turn_number)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Trace de turno não encontrado.")
    return TurnTraceResponse(
        campaign_id=campaign_id,
        turn_number=turn_number,
        trace=row.trace,
    )
