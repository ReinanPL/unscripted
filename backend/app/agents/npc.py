from google.adk.agents import LlmAgent

from app.agents.prompts.npc import NPC_INSTRUCTION
from app.providers.llm import LlmProvider


def build_npc_agent(provider: LlmProvider) -> LlmAgent:
    """Intérprete de NPC genérico.

    Um único agente serve a qualquer NPC: a persona ativa é injetada no
    prompt via placeholder `{npc_persona}` a cada turno. A persona vem do
    capítulo (`Adventure.chapters[].npcs[]`), incluindo personalidade,
    motivação, conhecimento e estado oculto.
    """
    return LlmAgent(
        name="npc_actor",
        model=provider.build_model(),
        description="Intérprete de NPC — fala e reage em personagem.",
        instruction=NPC_INSTRUCTION,
    )
