"""Provider de voz (interface + stub).

A interface entra na v1; a implementação real de STT/TTS é v2 (ADR-014).
A camada de providers (ADR-009) isola o backend de qualquer SDK
concreto: trocar de provedor depois é escrever um novo módulo e mudar
uma variável de ambiente, sem tocar nos endpoints.

O stub responde com payloads vazios e 200 OK — o frontend exercita o
fluxo sem que áudio real circule pelo sistema.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.config import Settings


@runtime_checkable
class VoiceProvider(Protocol):
    """Interface mínima do provider de voz.

    `transcribe` recebe os bytes de um arquivo de áudio (qualquer formato
    aceito pela implementação) e devolve o texto reconhecido. `synthesize`
    faz o caminho oposto. As implementações concretas decidem formatos,
    tamanhos máximos e tratamento de erro.
    """

    async def transcribe(self, audio: bytes, *, mime_type: str = "") -> str: ...

    async def synthesize(self, text: str, *, voice: str = "") -> bytes: ...


class StubVoiceProvider:
    """Implementação stub: aceita qualquer entrada, responde vazio.

    Existe para que o botão de voz no frontend (Fase 6.18) tenha um
    backend real para chamar — a UI fica completa, a v1 não acopla a
    nenhum serviço externo de áudio. Implementação concreta é v2.
    """

    async def transcribe(self, audio: bytes, *, mime_type: str = "") -> str:
        _ = (audio, mime_type)
        return ""

    async def synthesize(self, text: str, *, voice: str = "") -> bytes:
        _ = (text, voice)
        return b""


def get_voice_provider(settings: Settings) -> VoiceProvider:
    """Seleciona a implementação de provider de voz pelo settings.

    Na v1 só existe a opção `stub`. Adicionar implementação concreta
    em v2 é estender o `Literal` em `Settings.voice_provider` e o
    if/else aqui — sem tocar nos consumidores.
    """
    if settings.voice_provider == "stub":
        return StubVoiceProvider()
    raise ValueError(f"voice_provider desconhecido: {settings.voice_provider!r}")
