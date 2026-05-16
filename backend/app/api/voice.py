"""Endpoints de voz (STT / TTS).

Providers concretos vivem em `app.providers.stt` e `app.providers.tts`
(ADR-047). Os endpoints recebem JSON com base64 (sem multipart, frontend
simples) e despacham para o provider cacheado no `runner.py`.

Stub na ausência de chaves de API: o provider devolve payloads vazios e
o frontend trata como "voz indisponível".
"""

from __future__ import annotations

import base64

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.providers.stt import SttProvider
from app.providers.tts import TtsProvider
from app.runner import get_stt_provider_cached, get_tts_provider_cached

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
    provider: SttProvider = get_stt_provider_cached()
    audio = base64.b64decode(body.audio_base64) if body.audio_base64 else b""
    text = await provider.transcribe(audio, mime_type=body.mime_type)
    return SttResponse(text=text)


@router.post("/tts", response_model=TtsResponse)
async def tts_endpoint(body: TtsRequest) -> TtsResponse:
    provider: TtsProvider = get_tts_provider_cached()
    audio = await provider.synthesize(body.text, voice=body.voice)
    if not audio:
        return TtsResponse(audio_base64="", mime_type="")
    return TtsResponse(
        audio_base64=base64.b64encode(audio).decode("ascii"),
        mime_type="audio/mpeg",
    )
