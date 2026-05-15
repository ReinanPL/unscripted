from google.adk.agents import LlmAgent

from app.agents.prompts.narrator import NARRATOR_INSTRUCTION
from app.providers.llm import LlmProvider


def build_narrator_agent(provider: LlmProvider) -> LlmAgent:
    """Cria o NarratorAgent mínimo da Fase 1.

    Sem RAG, sem FunctionTools. Apenas narração em linguagem natural.
    """
    return LlmAgent(
        name="narrator",
        model=provider.build_model(),
        description="Game Master narrador — interpreta e narra as ações do jogador.",
        instruction=NARRATOR_INSTRUCTION,
    )
