from __future__ import annotations

from app.rules.proposals import ConsequenceProposal
from app.state.models import Character, GameState


def apply_damage(character: Character, amount: int) -> Character:
    """Pure — não muta o input. amount >= 0 (quantidade de dano)."""
    new_hp = max(0, character.hp_current - amount)
    return character.model_copy(update={"hp_current": new_hp})


def apply_consequence(state: GameState, proposal: ConsequenceProposal) -> GameState:
    """Valida a proposta tipada do LLM e retorna novo GameState sem mutar o input."""
    character = state.character
    inventory = list(state.inventory)
    location = state.location
    flags = state.flags

    if proposal.hp_delta is not None:
        if proposal.hp_delta < 0:
            character = apply_damage(character, -proposal.hp_delta)
        else:
            new_hp = min(character.hp_max, character.hp_current + proposal.hp_delta)
            character = character.model_copy(update={"hp_current": new_hp})

    for removal in proposal.items_removed:
        idx = next(
            (i for i, item in enumerate(inventory) if item.name == removal.name),
            None,
        )
        if idx is None:
            raise ValueError(f"item não encontrado no inventário: {removal.name!r}")
        current_item = inventory[idx]
        if current_item.quantity < removal.quantity:
            raise ValueError(
                f"quantidade insuficiente de {removal.name!r}: "
                f"tem {current_item.quantity}, pediu {removal.quantity}"
            )
        if current_item.quantity == removal.quantity:
            inventory.pop(idx)
        else:
            inventory[idx] = current_item.model_copy(
                update={"quantity": current_item.quantity - removal.quantity}
            )

    for item in proposal.items_added:
        existing_idx = next(
            (i for i, inv in enumerate(inventory) if inv.name == item.name),
            None,
        )
        if existing_idx is not None:
            existing = inventory[existing_idx]
            inventory[existing_idx] = existing.model_copy(
                update={"quantity": existing.quantity + item.quantity}
            )
        else:
            inventory.append(item)

    if proposal.new_location is not None:
        location = proposal.new_location
        revealed = list(flags.locations_revealed)
        if location.id not in revealed:
            revealed.append(location.id)
        flags = flags.model_copy(update={"locations_revealed": revealed})

    if proposal.events_occurred:
        existing_events = set(flags.events_occurred)
        new_events = [e for e in proposal.events_occurred if e not in existing_events]
        if new_events:
            flags = flags.model_copy(
                update={"events_occurred": list(flags.events_occurred) + new_events}
            )

    if proposal.objectives_completed:
        existing_objectives = set(flags.objectives_completed)
        new_objectives = [o for o in proposal.objectives_completed if o not in existing_objectives]
        if new_objectives:
            flags = flags.model_copy(
                update={"objectives_completed": list(flags.objectives_completed) + new_objectives}
            )

    return state.model_copy(
        update={
            "character": character,
            "inventory": inventory,
            "location": location,
            "flags": flags,
        }
    )
