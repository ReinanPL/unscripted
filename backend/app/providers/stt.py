"""Provider de Speech-to-Text — interface + stub (ADR-047).

A interface unificada de voz da v1 (ADR-014) foi dividida em duas:
`SttProvider` (este módulo) e `TtsProvider` (`tts.py`). STT e TTS são
serviços distintos com provedores distintos — manter uma interface
única forçava implementações stub artificiais em metade do espaço.

O stub aceita qualquer entrada e devolve string vazia — útil para CI
sem chaves e para dev que quer eliminar custo de API. Implementações
concretas vivem neste módulo.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.config import Settings


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


def get_stt_provider(settings: Settings) -> SttProvider:
    """Seleciona a implementação de STT pelo `STT_PROVIDER`.

    Provider real `groq` (Groq Whisper via litellm) entra no commit
    seguinte. Por enquanto, qualquer valor não-stub levanta — o
    Settings já valida o `Literal[...]`, então o ramo só executa se
    alguém estiver expandindo a enum.
    """
    if settings.stt_provider == "stub":
        return StubSttProvider()
    raise NotImplementedError(
        f"STT_PROVIDER={settings.stt_provider!r} ainda não tem implementação."
    )
