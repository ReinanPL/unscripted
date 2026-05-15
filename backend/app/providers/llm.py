import os
from typing import Protocol, runtime_checkable

from app.config import Settings


@runtime_checkable
class LlmProvider(Protocol):
    """Interface para o provider de LLM.

    Implementações concretas ficam neste módulo. Nenhum outro módulo
    importa diretamente o SDK do Gemini — apenas providers/llm.py.
    """

    def build_model(self) -> str:
        """Retorna o identificador de modelo que o LlmAgent do ADK aceita."""
        ...


class GeminiAiStudioProvider:
    """Provider para Gemini via Google AI Studio.

    Responsável por:
    - Mapear GEMINI_API_KEY → GOOGLE_API_KEY (variável lida pelo SDK google-genai).
    - Garantir que GOOGLE_GENAI_USE_VERTEXAI=0 (AI Studio, não Vertex).
    - Devolver o nome do modelo configurado.

    Deve ser instanciado uma única vez no startup do backend.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY ausente. "
                "Copie .env.example para .env e preencha a chave antes de subir o backend."
            )
        os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "0")
        self._model = settings.gemini_model

    def build_model(self) -> str:
        return self._model


def get_llm_provider(settings: Settings) -> LlmProvider:
    """Factory que retorna o provider correto com base em LLM_PROVIDER."""
    if settings.llm_provider == "gemini_aistudio":
        return GeminiAiStudioProvider(settings)
    raise RuntimeError(f"LLM_PROVIDER desconhecido: '{settings.llm_provider}'")
