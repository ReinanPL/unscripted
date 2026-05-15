"""Endpoints de voz (STT / TTS).

A interface entra na v1 (ADR-014); a implementação concreta é v2. O
provider real fica em `app.providers.voice`. Estes endpoints existem
para o botão de gravar do frontend (Fase 6.18) ter onde chamar — a
resposta vazia é esperada enquanto não há provider concreto.

Payloads em JSON com base64 evitam multipart e mantêm o frontend
simples (sem FormData / browser-only APIs).
"""

from __future__ import annotations

import base64

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.providers.voice import VoiceProvider
from app.runner import get_voice_provider_cached

router = APIRouter(prefix="/voice", tags=["voice"])


class SttRequest(BaseModel):
    audio_base64: str = Field(default="", description="Áudio capturado, base64-encoded.")
    mime_type: str = Field(default="", description="Ex.: audio/webm; codecs=opus.")


class SttResponse(BaseModel):
    text: str


class TtsRequest(BaseModel):
    text: str = Field(min_length=0, max_length=4000)
    voice: str = Field(default="", description="Identificador de voz; provider escolhe o padrão.")


class TtsResponse(BaseModel):
    audio_base64: str
    mime_type: str = ""


@router.post("/stt", response_model=SttResponse)
async def stt_endpoint(body: SttRequest) -> SttResponse:
    provider: VoiceProvider = get_voice_provider_cached()
    audio = base64.b64decode(body.audio_base64) if body.audio_base64 else b""
    text = await provider.transcribe(audio, mime_type=body.mime_type)
    return SttResponse(text=text)


@router.post("/tts", response_model=TtsResponse)
async def tts_endpoint(body: TtsRequest) -> TtsResponse:
    provider: VoiceProvider = get_voice_provider_cached()
    audio = await provider.synthesize(body.text, voice=body.voice)
    return TtsResponse(audio_base64=base64.b64encode(audio).decode("ascii") if audio else "")
