"""Camada de providers de LLM — multi-provider via env (ADR-009, ADR-045).

Cada provider expõe `build_model(purpose)`, onde `purpose` é:
- `"reasoning"` → modelo usado pelo RefereeAgent (output_schema=Ruling).
- `"narrative"` → modelo usado pelo Narrator/NPCActor (streaming de prosa).

Quando o modelo NARRATIVE não é configurado, o provider faz fallback para o
REASONING (single-model preservado — útil em Gemini/OpenAI).

Para Groq e OpenAI usamos `LiteLlm` do ADK, que cobre dezenas de providers
via prefixo (`groq/...`, `openai/...`). O ADK converte automaticamente
`LlmAgent(output_schema=...)` em `response_format={"type":"json_schema",...}`
para modelos OpenAI-compatible — ver `google/adk/models/lite_llm.py:1788`.
"""

from __future__ import annotations

import os
from typing import Literal, Protocol, runtime_checkable

from google.adk.models.lite_llm import LiteLlm

from app.config import Settings

Purpose = Literal["reasoning", "narrative"]
ModelHandle = str | LiteLlm


@runtime_checkable
class LlmProvider(Protocol):
    """Interface para um provider de LLM.

    Implementações concretas vivem neste módulo. Nenhum outro módulo do
    backend importa diretamente um SDK de LLM — apenas `providers/llm.py`.
    """

    def build_model(self, purpose: Purpose) -> ModelHandle:
        """Retorna um handle de modelo aceito por `LlmAgent(model=...)`."""
        ...


def _resolve(narrative: str, reasoning: str) -> tuple[str, str]:
    """Aplica o fallback NARRATIVE → REASONING quando NARRATIVE está vazio."""
    return reasoning, (narrative.strip() or reasoning)


class GeminiAiStudioProvider:
    """Provider para Gemini via Google AI Studio.

    Mapeia `GEMINI_API_KEY` → `GOOGLE_API_KEY` (lida pelo SDK google-genai),
    força `GOOGLE_GENAI_USE_VERTEXAI=0` (AI Studio, não Vertex), e devolve
    o nome do modelo configurado para cada propósito.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY ausente. "
                "Copie .env.example para .env e preencha a chave antes de subir o backend."
            )
        os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "0")
        self._reasoning, self._narrative = _resolve(
            settings.gemini_model_narrative, settings.gemini_model_reasoning
        )

    def build_model(self, purpose: Purpose) -> ModelHandle:
        return self._reasoning if purpose == "reasoning" else self._narrative


class GroqProvider:
    """Provider para Groq via LiteLlm.

    Groq expõe modelos OpenAI-compatible em `https://api.groq.com/openai/v1`.
    Usamos o wrapper `LiteLlm(model="groq/<modelo>")` do ADK — o LiteLLM
    descobre o endpoint automaticamente a partir do prefixo. A `GROQ_API_KEY`
    é lida do env pelo próprio LiteLLM.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY ausente. "
                "Copie .env.example para .env e preencha a chave antes de subir o backend."
            )
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
        self._reasoning, self._narrative = _resolve(
            settings.groq_model_narrative, settings.groq_model_reasoning
        )

    def build_model(self, purpose: Purpose) -> ModelHandle:
        model = self._reasoning if purpose == "reasoning" else self._narrative
        return LiteLlm(model=f"groq/{model}")


class OpenAiProvider:
    """Provider para OpenAI via LiteLlm.

    Usamos `LiteLlm(model="openai/<modelo>")` para coerência com o resto
    (1 wrapper, mesmo padrão dos outros providers não-Gemini). A
    `OPENAI_API_KEY` é lida do env pelo LiteLLM.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY ausente. "
                "Copie .env.example para .env e preencha a chave antes de subir o backend."
            )
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        self._reasoning, self._narrative = _resolve(
            settings.openai_model_narrative, settings.openai_model_reasoning
        )

    def build_model(self, purpose: Purpose) -> ModelHandle:
        model = self._reasoning if purpose == "reasoning" else self._narrative
        return LiteLlm(model=f"openai/{model}")


def get_llm_provider(settings: Settings) -> LlmProvider:
    """Factory que retorna o provider correto com base em `LLM_PROVIDER`."""
    if settings.llm_provider == "gemini_aistudio":
        return GeminiAiStudioProvider(settings)
    if settings.llm_provider == "groq":
        return GroqProvider(settings)
    if settings.llm_provider == "openai":
        return OpenAiProvider(settings)
    raise RuntimeError(f"LLM_PROVIDER desconhecido: '{settings.llm_provider}'")
