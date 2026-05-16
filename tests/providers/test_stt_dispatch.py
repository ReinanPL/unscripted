"""Dispatch determinístico de `STT_PROVIDER` (ADR-047).

Não chama a API — só verifica que a factory instancia a classe certa
para cada valor de env e que a falta de chave em modo `groq` levanta
um erro claro no construtor (mesmo padrão do `LlmProvider`).
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.providers.stt import (
    GroqWhisperProvider,
    StubSttProvider,
    get_stt_provider,
)


def test_stub_is_default() -> None:
    settings = Settings()
    provider = get_stt_provider(settings)
    assert isinstance(provider, StubSttProvider)


def test_dispatch_groq_with_key() -> None:
    settings = Settings(stt_provider="groq", groq_api_key="test-groq")
    provider = get_stt_provider(settings)
    assert isinstance(provider, GroqWhisperProvider)


def test_dispatch_groq_without_key_raises() -> None:
    settings = Settings(stt_provider="groq", groq_api_key="")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        get_stt_provider(settings)
