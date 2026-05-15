"""Contratos tipados dos artefatos do turno.

`Ruling` é a saída estruturada do `RefereeAgent` (consumida via
`output_schema` do ADK). `TurnTrace` é o registro persistido em
`turn_traces` que alimenta o painel "pensamento do mestre" (PRD §6.7).

Saída de LLM passa SEMPRE por estes contratos antes de tocar o estado
do jogo (princípio determinístico/LLM, ADR-003).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.agents.robustness import RobustnessVerdict
from app.rules.checks import CheckResult
from app.rules.dice import RollResult
from app.rules.proposals import ConsequenceProposal


class Ruling(BaseModel):
    """Saída estruturada do RefereeAgent.

    Dois modos mutuamente exclusivos:
    - `precisa_rolagem=False` — aplica `consequencia` diretamente.
    - `precisa_rolagem=True`  — rola `notacao_dado`; se total >= `dificuldade`,
      aplica `consequencia_sucesso`; caso contrário, `consequencia_falha`.

    `npc_to_react` é o id do NPC presente na cena que deve reagir após a
    narração principal. `None` se nenhum NPC reage neste turno.
    """

    precisa_rolagem: bool
    pericia: str | None = None
    dificuldade: int | None = None
    notacao_dado: str = "1d20"
    motivo_dificuldade: str = ""
    consequencia: ConsequenceProposal | None = None
    consequencia_sucesso: ConsequenceProposal | None = None
    consequencia_falha: ConsequenceProposal | None = None
    npc_to_react: str | None = None

    @model_validator(mode="after")
    def _validate_modos(self) -> Ruling:
        if self.precisa_rolagem:
            if self.dificuldade is None:
                raise ValueError("precisa_rolagem=True exige `dificuldade` definida")
            if self.consequencia_sucesso is None or self.consequencia_falha is None:
                raise ValueError(
                    "precisa_rolagem=True exige `consequencia_sucesso` e "
                    "`consequencia_falha` definidas"
                )
        elif self.consequencia is None:
            raise ValueError("precisa_rolagem=False exige `consequencia` definida")
        return self


class RetrievalSnippet(BaseModel):
    """Trecho recuperado pelo RAG no turno — registrado para observabilidade."""

    corpus: str
    source: str
    content: str


class RollOutcome(BaseModel):
    """Composição determinística do dado deste turno: rolagem + comparação."""

    roll: RollResult
    check: CheckResult


class TurnTrace(BaseModel):
    """Trace completo do turno, persistido em `turn_traces`."""

    turn: int
    player_action: str
    robustness: RobustnessVerdict
    retrieval_rules: list[RetrievalSnippet] = Field(default_factory=list)
    retrieval_lore: list[RetrievalSnippet] = Field(default_factory=list)
    ruling: Ruling | None = None
    roll_outcome: RollOutcome | None = None
    consequence_applied: ConsequenceProposal | None = None
    narration: str = ""
    npc_reaction: str | None = None
    npc_id: str | None = None
    error: str | None = None


TurnEventType = Literal[
    "narration_chunk",
    "npc_chunk",
    "error_preserve_input",
    "turn_complete",
]


class TurnEvent(BaseModel):
    """Evento emitido pelo orquestrador do turno para o consumo do SSE.

    `narration_chunk` / `npc_chunk` carregam pedaços de texto. `error_preserve_input`
    sinaliza falha não-fatal (frontend devolve a mensagem do jogador, turno
    não é consumido). `turn_complete` fecha o stream com o número do turno.
    """

    type: TurnEventType
    text: str = ""
    npc_id: str | None = None
    turn_number: int | None = None
