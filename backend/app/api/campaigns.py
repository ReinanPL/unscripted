from __future__ import annotations

import asyncio
import pathlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ActionEvent,
    ActionRequest,
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignLogResponse,
    CampaignStateResponse,
)
from app.db.base import CampaignRow
from app.db.engine import _async_session_factory, get_db
from app.runner import CampaignNotFoundError, create_adk_session, stream_turn
from app.state.models import Character, GameState, HiddenState, HistoryEntry, Location

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


@asynccontextmanager
async def _db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_factory() as session:
        yield session


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


@router.post("/{campaign_id}/action")
async def action_endpoint(
    campaign_id: str,
    body: ActionRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    await _get_campaign_or_404(campaign_id, db)

    async def event_stream() -> AsyncGenerator[bytes, None]:
        narration_chunks: list[str] = []
        try:
            async for chunk in stream_turn(campaign_id, body.text):
                narration_chunks.append(chunk)
                event = ActionEvent(type="chunk", text=chunk)
                yield f"data: {event.model_dump_json()}\n\n".encode()
        except CampaignNotFoundError:
            yield f"data: {ActionEvent(type='error', text='Campanha não encontrada.').model_dump_json()}\n\n".encode()
            return
        except TimeoutError:
            yield f"data: {ActionEvent(type='error', text='Tempo de resposta excedido.').model_dump_json()}\n\n".encode()
            return
        except asyncio.CancelledError:
            return

        full_narration = "".join(narration_chunks)
        if full_narration:
            async with _db_session() as db_write:
                result = await db_write.execute(
                    select(CampaignRow).where(CampaignRow.id == campaign_id)
                )
                row = result.scalar_one_or_none()
                if row is not None:
                    state = GameState.model_validate(row.game_state)
                    turn_number = len(state.history) + 1
                    state.history.append(
                        HistoryEntry(
                            turn=turn_number,
                            player_action=body.text,
                            narration=full_narration,
                        )
                    )
                    row.game_state = state.model_dump(mode="json")
                    row.updated_at = datetime.now(UTC)
                    await db_write.commit()

        yield f"data: {ActionEvent(type='done').model_dump_json()}\n\n".encode()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
