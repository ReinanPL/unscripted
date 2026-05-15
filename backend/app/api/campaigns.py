from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import ActionEvent, ActionRequest, CampaignCreateResponse
from app.runner import CampaignNotFoundError, create_campaign, stream_turn

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignCreateResponse, status_code=201)
async def create_campaign_endpoint() -> CampaignCreateResponse:
    campaign_id = await create_campaign()
    return CampaignCreateResponse(campaign_id=campaign_id)


@router.post("/{campaign_id}/action")
async def action_endpoint(campaign_id: str, body: ActionRequest) -> StreamingResponse:
    # Verifica existência antes de abrir o stream — retorna 404 síncrono
    from app.runner import _campaigns  # noqa: PLC0415

    if campaign_id not in _campaigns:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")

    async def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            async for chunk in stream_turn(campaign_id, body.text):
                event = ActionEvent(type="chunk", text=chunk)
                yield f"data: {event.model_dump_json()}\n\n".encode()
        except CampaignNotFoundError:
            event = ActionEvent(type="error", text="Campanha não encontrada.")
            yield f"data: {event.model_dump_json()}\n\n".encode()
            return
        except TimeoutError:
            # stream_turn já emite a mensagem de timeout antes de lançar;
            # este bloco cobre o caso de TimeoutError re-lançado fora do generator
            event = ActionEvent(type="error", text="Tempo de resposta excedido.")
            yield f"data: {event.model_dump_json()}\n\n".encode()
            return
        except asyncio.CancelledError:
            # Cliente desconectou — encerra silenciosamente sem poluir o log
            return

        yield f"data: {ActionEvent(type='done').model_dump_json()}\n\n".encode()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
