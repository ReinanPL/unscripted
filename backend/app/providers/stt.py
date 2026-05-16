"""Provider de Speech-to-Text — interface + stub + Groq Whisper (ADR-047).

A interface unificada de voz da v1 (ADR-014) foi dividida em duas:
`SttProvider` (este módulo) e `TtsProvider` (`tts.py`). STT e TTS são
serviços distintos com provedores distintos — manter uma interface
única forçava implementações stub artificiais em metade do espaço.

O stub aceita qualquer entrada e devolve string vazia — útil para CI
sem chaves e para dev que quer eliminar custo de API.

`GroqWhisperProvider` usa `litellm.atranscription` com o modelo
`groq/whisper-large-v3-turbo`. Coerência com a Fase 1 da v2 (ADR-045):
todo provider que não é Gemini-direto passa por LiteLlm.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Protocol, runtime_checkable

import litellm

from app.config import Settings

logger = logging.getLogger(__name__)

# Mime → extensão aceita pelo endpoint /audio/transcriptions do Groq.
# Whisper precisa do nome do arquivo com extensão pra escolher o decoder.
# O navegador padrão grava `audio/webm; codecs=opus` (Chrome/Firefox/Edge);
# Safari grava `audio/mp4`. Outros formatos vêm como fallback.
_MIME_TO_EXT: dict[str, str] = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
}


def _filename_for(mime_type: str) -> str:
    base = mime_type.split(";", 1)[0].strip().lower() if mime_type else ""
    ext = _MIME_TO_EXT.get(base, "webm")
    return f"audio.{ext}"


@runtime_checkable
class SttProvider(Protocol):
    """Recebe áudio cru e devolve texto reconhecido."""

    async def transcribe(self, audio: bytes, *, mime_type: str = "") -> str: ...


class StubSttProvider:
    """Implementação sem efeito: aceita áudio, devolve `""`.

    Mantém o pipe completo do `POST /voice/stt` funcionando para o
    frontend que já gravou o blob e está esperando uma resposta.
    """

    async def transcribe(self, audio: bytes, *, mime_type: str = "") -> str:
        _ = (audio, mime_type)
        return ""


class GroqWhisperProvider:
    """Speech-to-Text via Groq Whisper (`whisper-large-v3-turbo`).

    A `GROQ_API_KEY` é lida do settings e exportada como env (mesmo
    padrão do `GroqProvider` de LLM — ADR-045). O modelo é configurado
    via `groq_stt_model`; ajustar no `.env` se quiser trocar para o
    Whisper full (`whisper-large-v3`).

    Áudio vazio é tratado localmente — não vale gastar uma chamada à
    API para receber um 400. Erros da API propagam para o endpoint,
    que retorna 500 (o frontend tem `onError`).
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY ausente. "
                "Copie .env.example para .env e preencha a chave antes de subir o backend."
            )
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
        self._model = f"groq/{settings.groq_stt_model}"

    async def transcribe(self, audio: bytes, *, mime_type: str = "") -> str:
        if not audio:
            return ""
        buffer = io.BytesIO(audio)
        buffer.name = _filename_for(mime_type)
        response = await litellm.atranscription(model=self._model, file=buffer)
        text = getattr(response, "text", "") or ""
        return text.strip()


def get_stt_provider(settings: Settings) -> SttProvider:
    """Seleciona a implementação de STT pelo `STT_PROVIDER`."""
    if settings.stt_provider == "stub":
        return StubSttProvider()
    if settings.stt_provider == "groq":
        return GroqWhisperProvider(settings)
    raise RuntimeError(f"STT_PROVIDER desconhecido: '{settings.stt_provider}'")
