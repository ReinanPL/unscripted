"""Fallback NARRATIVE → REASONING quando `*_MODEL_NARRATIVE` está vazio.

Garante que omitir o modelo NARRATIVE em qualquer provider preserva o
comportamento single-model: `build_model("narrative")` retorna o mesmo
identificador que `build_model("reasoning")`.
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.providers.llm import get_llm_provider


@pytest.fixture
def keys() -> dict[str, str]:
    return {
        "gemini_api_key": "test-gemini",
        "groq_api_key": "test-groq",
        "openai_api_key": "test-openai",
    }


def test_gemini_narrative_falls_back_to_reasoning(keys: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="gemini_aistudio",
        gemini_model_reasoning="gemini-2.5-flash",
        gemini_model_narrative="",
        **keys,
    )
    provider = get_llm_provider(settings)
    reasoning = provider.build_model("reasoning")
    narrative = provider.build_model("narrative")
    assert reasoning == narrative == "gemini-2.5-flash"


def test_gemini_split_uses_distinct_models(keys: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="gemini_aistudio",
        gemini_model_reasoning="gemini-2.5-flash",
        gemini_model_narrative="gemini-2.5-flash-lite",
        **keys,
    )
    provider = get_llm_provider(settings)
    assert provider.build_model("reasoning") == "gemini-2.5-flash"
    assert provider.build_model("narrative") == "gemini-2.5-flash-lite"


def test_groq_narrative_falls_back_to_reasoning(keys: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="groq",
        groq_model_reasoning="llama-3.3-70b-versatile",
        groq_model_narrative="",
        **keys,
    )
    provider = get_llm_provider(settings)
    reasoning = provider.build_model("reasoning")
    narrative = provider.build_model("narrative")
    assert reasoning.model == narrative.model == "groq/llama-3.3-70b-versatile"  # type: ignore[union-attr]


def test_groq_split_uses_distinct_models(keys: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="groq",
        groq_model_reasoning="llama-3.3-70b-versatile",
        groq_model_narrative="llama-3.1-8b-instant",
        **keys,
    )
    provider = get_llm_provider(settings)
    assert provider.build_model("reasoning").model == "groq/llama-3.3-70b-versatile"  # type: ignore[union-attr]
    assert provider.build_model("narrative").model == "groq/llama-3.1-8b-instant"  # type: ignore[union-attr]


def test_openai_narrative_falls_back_to_reasoning(keys: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="openai",
        openai_model_reasoning="gpt-4o-mini",
        openai_model_narrative="",
        **keys,
    )
    provider = get_llm_provider(settings)
    reasoning = provider.build_model("reasoning")
    narrative = provider.build_model("narrative")
    assert reasoning.model == narrative.model == "openai/gpt-4o-mini"  # type: ignore[union-attr]


def test_openai_split_uses_distinct_models(keys: dict[str, str]) -> None:
    settings = Settings(
        llm_provider="openai",
        openai_model_reasoning="gpt-4o",
        openai_model_narrative="gpt-4o-mini",
        **keys,
    )
    provider = get_llm_provider(settings)
    assert provider.build_model("reasoning").model == "openai/gpt-4o"  # type: ignore[union-attr]
    assert provider.build_model("narrative").model == "openai/gpt-4o-mini"  # type: ignore[union-attr]


def test_groq_narrative_whitespace_only_falls_back(keys: dict[str, str]) -> None:
    """Espaços em branco no NARRATIVE também devem cair no fallback."""
    settings = Settings(
        llm_provider="groq",
        groq_model_reasoning="llama-3.3-70b-versatile",
        groq_model_narrative="   ",
        **keys,
    )
    provider = get_llm_provider(settings)
    assert (
        provider.build_model("narrative").model  # type: ignore[union-attr]
        == "groq/llama-3.3-70b-versatile"
    )
