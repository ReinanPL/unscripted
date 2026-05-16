"""Testes do `OpenAiTtsProvider`.

Testes puros (sem rede) cobrem:
- Texto vazio é tratado localmente (sem hit na API).
- Whitespace-only conta como vazio.

O eval opt-in (`@pytest.mark.eval`) só roda quando `OPENAI_API_KEY`
está no env. Pede um TTS curto e confere que volta MP3 válido (header
`fff` típico do MPEG-1 layer III, e bytes não-vazios).
"""

from __future__ import annotations

import os

import pytest

from app.config import Settings
from app.providers.tts import OpenAiTtsProvider


@pytest.mark.asyncio
async def test_synthesize_empty_short_circuits() -> None:
    """Texto vazio não vale uma chamada à API."""
    settings = Settings(tts_provider="openai", openai_api_key="test-openai")
    provider = OpenAiTtsProvider(settings)
    out = await provider.synthesize("")
    assert out == b""


@pytest.mark.asyncio
async def test_synthesize_whitespace_only_short_circuits() -> None:
    settings = Settings(tts_provider="openai", openai_api_key="test-openai")
    provider = OpenAiTtsProvider(settings)
    out = await provider.synthesize("   \n  \t ")
    assert out == b""


@pytest.mark.eval
@pytest.mark.asyncio
async def test_openai_tts_end_to_end() -> None:
    """Eval opt-in: roda contra OpenAI gpt-4o-mini-tts de verdade.

    Confere que volta MP3 não-vazio com header de quadro MPEG. Não
    valida o áudio em si.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY ausente; eval contra OpenAI TTS ignorado.")
    settings = Settings(
        tts_provider="openai",
        openai_api_key=os.environ["OPENAI_API_KEY"],
    )
    provider = OpenAiTtsProvider(settings)
    audio = await provider.synthesize("Olá, aventureiro.", voice="alloy")
    assert len(audio) > 1000  # MP3 de 1s tipicamente >5KB; threshold conservador
    # Quadro MPEG-1 layer III começa com `0xFF` + 3 bits 0xE no nibble alto
    # do byte seguinte. Aceita qualquer variação do sync word.
    assert audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0
