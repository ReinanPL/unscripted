from google.adk.agents import LlmAgent

from app.agents.prompts.narrator import NARRATOR_INSTRUCTION
from app.providers.llm import LlmProvider


def build_narrator_agent(provider: LlmProvider) -> LlmAgent:
    """Narrador — transforma o resultado do turno em prosa, em streaming.

    Sem `output_schema` (prosa livre). Sem tools. Modelo:
    `build_model("narrative")` — favorece velocidade e fluência, pode
    ser um modelo mais leve que o REASONING (split por agente, ADR-045).
    """
    return LlmAgent(
        name="narrator",
        model=provider.build_model("narrative"),
        description="Game Master narrador — interpreta e narra as ações do jogador.",
        instruction=NARRATOR_INSTRUCTION,
    )
