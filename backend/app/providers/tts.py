"""Provider de Text-to-Speech — interface + stub (ADR-047).

A interface unificada de voz da v1 (ADR-014) foi dividida em duas:
`SttProvider` (`stt.py`) e `TtsProvider` (este módulo). Manter uma
interface única forçava implementações stub artificiais em metade
do espaço — Groq não tem TTS bom, OpenAI não tem STT competitivo,
o mix é o caminho natural.

O stub aceita qualquer texto e devolve `b""` — útil para CI sem
chaves e para dev que quer eliminar custo. Implementações concretas
vivem neste módulo.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.config import Settings


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


def get_tts_provider(settings: Settings) -> TtsProvider:
    """Seleciona a implementação de TTS pelo `TTS_PROVIDER`.

    Provider real `openai` (gpt-4o-mini-tts via litellm) entra no
    Bloco 2 — por enquanto, qualquer valor não-stub levanta.
    """
    if settings.tts_provider == "stub":
        return StubTtsProvider()
    raise NotImplementedError(
        f"TTS_PROVIDER={settings.tts_provider!r} ainda não tem implementação."
    )
