from google.adk.agents import LlmAgent

from app.agents.contracts import Ruling
from app.agents.prompts.referee import REFEREE_INSTRUCTION
from app.providers.llm import LlmProvider


def build_referee_agent(provider: LlmProvider) -> LlmAgent:
    """Árbitro do turno — emite um Ruling estruturado (sem prosa).

    Usa `output_schema=Ruling` do ADK. Por isso não recebe tools: o
    contexto de regras chega via prefetch determinístico no `runner.py`
    (mesmo padrão da ADR-031 para o lore).

    Modelo: `build_model("reasoning")` — favorece capacidade analítica.
    """
    return LlmAgent(
        name="referee",
        model=provider.build_model("reasoning"),
        description="Árbitro — define se há rolagem, qual perícia e dificuldade.",
        instruction=REFEREE_INSTRUCTION,
        output_schema=Ruling,
    )
