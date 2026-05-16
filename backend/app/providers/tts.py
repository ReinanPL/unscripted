"""Provider de Text-to-Speech — interface + stub + OpenAI (ADR-047).

A interface unificada de voz da v1 (ADR-014) foi dividida em duas:
`SttProvider` (`stt.py`) e `TtsProvider` (este módulo). Manter uma
interface única forçava implementações stub artificiais em metade
do espaço — Groq não tem TTS bom, OpenAI não tem STT competitivo,
o mix é o caminho natural.

O stub aceita qualquer texto e devolve `b""` — útil para CI sem
chaves e para dev que quer eliminar custo.

`OpenAiTtsProvider` usa `litellm.aspeech` com `gpt-4o-mini-tts`. PT-BR
nativo, MP3 binário no retorno. Coerência com a Fase 1 da v2: tudo
que não é Gemini-direto passa por LiteLlm (ADR-045).
"""

from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

import litellm

from app.config import Settings

logger = logging.getLogger(__name__)


@runtime_checkable
class TtsProvider(Protocol):
    """Recebe texto e devolve bytes de áudio.

    `synthesize` retorna o arquivo completo (uso típico: cliente do
    endpoint `/voice/tts`). Implementações que suportam streaming
    chunk-a-chunk acrescentam `synthesize_stream` quando necessário —
    isso entra com o Bloco 3 (sincronia de frase).
    """

    async def synthesize(self, text: str, *, voice: str = "") -> bytes: ...


class StubTtsProvider:
    """Implementação sem efeito: aceita texto, devolve `b""`.

    Mantém o pipe completo do `POST /voice/tts` funcionando para o
    frontend que esperava o áudio chegar.
    """

    async def synthesize(self, text: str, *, voice: str = "") -> bytes:
        _ = (text, voice)
        return b""


class OpenAiTtsProvider:
    """Text-to-Speech via OpenAI gpt-4o-mini-tts (default).

    A `OPENAI_API_KEY` é lida do settings e exportada como env (mesmo
    padrão do `OpenAiProvider` de LLM — ADR-045). Modelo e voz default
    vêm dos settings; `voice=` no `synthesize()` sobrescreve a voz por
    chamada (útil para o script de amostras do Bloco 2).

    Texto vazio é tratado localmente — não vale gastar uma chamada à
    API. Erros da API propagam para o endpoint, que retorna 500 (o
    frontend tem fallback no banner de erro).

    Retorna MP3 binário. O endpoint base64-encoda; o frontend toca via
    `<audio>` ou `URL.createObjectURL(blob)`.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY ausente. "
                "Copie .env.example para .env e preencha a chave antes de subir o backend."
            )
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        self._model = f"openai/{settings.openai_tts_model}"
        self._default_voice = settings.openai_tts_voice

    async def synthesize(self, text: str, *, voice: str = "") -> bytes:
        if not text or not text.strip():
            return b""
        chosen_voice = voice or self._default_voice
        response = await litellm.aspeech(
            model=self._model,
            input=text,
            voice=chosen_voice,
            response_format="mp3",
        )
        return bytes(response.content)


def get_tts_provider(settings: Settings) -> TtsProvider:
    """Seleciona a implementação de TTS pelo `TTS_PROVIDER`."""
    if settings.tts_provider == "stub":
        return StubTtsProvider()
    if settings.tts_provider == "openai":
        return OpenAiTtsProvider(settings)
    raise RuntimeError(f"TTS_PROVIDER desconhecido: '{settings.tts_provider}'")
