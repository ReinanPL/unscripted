"""Testes determinísticos da camada de providers (ADR-045).

Sem chamar LLM real — só verifica que:
- `get_llm_provider(settings)` instancia a classe correta para cada
  valor de `LLM_PROVIDER`.
- `build_model("reasoning")` e `build_model("narrative")` devolvem o
  tipo certo: `str` para Gemini, `LiteLlm` para Groq e OpenAI.
- Sem chave da API configurada, o provider correspondente levanta
  RuntimeError com mensagem clara.
"""

from __future__ import annotations

import pytest
from google.adk.models.lite_llm import LiteLlm

from app.config import Settings
from app.providers.llm import (
    GeminiAiStudioProvider,
    GroqProvider,
    OpenAiProvider,
    get_llm_provider,
)


@pytest.fixture
def base_settings_kwargs() -> dict[str, str]:
    """Settings com todas as chaves preenchidas — testes individuais
    sobrescrevem `llm_provider`.
    """
    return {
        "gemini_api_key": "test-gemini",
        "groq_api_key": "test-groq",
        "openai_api_key": "test-openai",
    }


def test_dispatch_gemini(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(llm_provider="gemini_aistudio", **base_settings_kwargs)
    provider = get_llm_provider(settings)
    assert isinstance(provider, GeminiAiStudioProvider)


def test_dispatch_groq(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(llm_provider="groq", **base_settings_kwargs)
    provider = get_llm_provider(settings)
    assert isinstance(provider, GroqProvider)


def test_dispatch_openai(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(llm_provider="openai", **base_settings_kwargs)
    provider = get_llm_provider(settings)
    assert isinstance(provider, OpenAiProvider)


def test_gemini_returns_string_model(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(llm_provider="gemini_aistudio", **base_settings_kwargs)
    provider = get_llm_provider(settings)
    assert isinstance(provider.build_model("reasoning"), str)
    assert isinstance(provider.build_model("narrative"), str)


def test_groq_returns_litellm(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(llm_provider="groq", **base_settings_kwargs)
    provider = get_llm_provider(settings)
    assert isinstance(provider.build_model("reasoning"), LiteLlm)
    assert isinstance(provider.build_model("narrative"), LiteLlm)


def test_openai_returns_litellm(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(llm_provider="openai", **base_settings_kwargs)
    provider = get_llm_provider(settings)
    assert isinstance(provider.build_model("reasoning"), LiteLlm)
    assert isinstance(provider.build_model("narrative"), LiteLlm)


def test_groq_prefix_in_model_name(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="groq",
        groq_model_reasoning="llama-3.3-70b-versatile",
        groq_model_narrative="llama-3.1-8b-instant",
        **base_settings_kwargs,
    )
    provider = get_llm_provider(settings)
    reasoning = provider.build_model("reasoning")
    narrative = provider.build_model("narrative")
    assert isinstance(reasoning, LiteLlm)
    assert isinstance(narrative, LiteLlm)
    assert reasoning.model == "groq/llama-3.3-70b-versatile"
    assert narrative.model == "groq/llama-3.1-8b-instant"


def test_openai_prefix_in_model_name(base_settings_kwargs: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="openai",
        openai_model_reasoning="gpt-4o-mini",
        **base_settings_kwargs,
    )
    provider = get_llm_provider(settings)
    reasoning = provider.build_model("reasoning")
    assert isinstance(reasoning, LiteLlm)
    assert reasoning.model == "openai/gpt-4o-mini"


def test_gemini_missing_key_raises() -> None:
    settings = Settings(llm_provider="gemini_aistudio", gemini_api_key="")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        get_llm_provider(settings)


def test_groq_missing_key_raises() -> None:
    settings = Settings(llm_provider="groq", groq_api_key="")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        get_llm_provider(settings)


def test_openai_missing_key_raises() -> None:
    settings = Settings(llm_provider="openai", openai_api_key="")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_llm_provider(settings)


def test_unknown_provider_raises(base_settings_kwargs: dict[str, str]) -> None:
    # Bypass do Literal via construct — verifica fallback do factory.
    settings = Settings(**base_settings_kwargs)
    settings.llm_provider = "wat"  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="LLM_PROVIDER desconhecido"):
        get_llm_provider(settings)
