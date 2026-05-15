from __future__ import annotations

from pydantic import BaseModel

from app.state.models import InventoryItem, Location


class ItemRemoveProposal(BaseModel):
    name: str
    quantity: int = 1


class ConsequenceProposal(BaseModel):
    """Proposta tipada emitida pelo LLM (RefereeAgent).

    O código a valida e aplica — nunca muta o estado diretamente.
    hp_delta: negativo = dano, positivo = cura.
    new_location: se definido, atualiza localização e revela o id nos flags.
    """

    hp_delta: int | None = None
    items_added: list[InventoryItem] = []
    items_removed: list[ItemRemoveProposal] = []
    new_location: Location | None = None
    events_occurred: list[str] = []
    objectives_completed: list[str] = []
