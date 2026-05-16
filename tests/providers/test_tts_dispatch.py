"""Dispatch determinístico de `TTS_PROVIDER` (ADR-047).

Não chama a API — só verifica que a factory instancia a classe certa
para cada valor de env e que a falta de chave em modo `openai` levanta
um erro claro no construtor (mesmo padrão do `LlmProvider`).
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.providers.tts import (
    OpenAiTtsProvider,
    StubTtsProvider,
    get_tts_provider,
)


def test_stub_is_returned() -> None:
    settings = Settings(tts_provider="stub")
    provider = get_tts_provider(settings)
    assert isinstance(provider, StubTtsProvider)


def test_dispatch_openai_with_key() -> None:
    settings = Settings(tts_provider="openai", openai_api_key="test-openai")
    provider = get_tts_provider(settings)
    assert isinstance(provider, OpenAiTtsProvider)


def test_dispatch_openai_without_key_raises() -> None:
    settings = Settings(tts_provider="openai", openai_api_key="")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_tts_provider(settings)
