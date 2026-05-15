import pytest

from app.rules.consequences import apply_consequence, apply_damage
from app.rules.proposals import ConsequenceProposal, ItemRemoveProposal
from app.state.models import (
    Character,
    CharacterAttributes,
    Flags,
    GameState,
    HistoryEntry,
    HiddenState,
    InventoryItem,
    Location,
)


def _make_character(hp_current: int = 10, hp_max: int = 12) -> Character:
    return Character(
        name="Herói",
        character_class="guerreiro",
        level=1,
        hp_current=hp_current,
        hp_max=hp_max,
        attributes=CharacterAttributes(
            strength=16,
            dexterity=12,
            constitution=15,
            intelligence=10,
            wisdom=11,
            charisma=10,
        ),
    )


def _make_state(
    hp_current: int = 10,
    hp_max: int = 12,
    inventory: list[InventoryItem] | None = None,
) -> GameState:
    return GameState(
        character=_make_character(hp_current, hp_max),
        inventory=inventory or [],
        location=Location(id="taverna", name="Taverna", description=""),
        flags=Flags(),
        history=[],
        hidden_state=HiddenState(),
    )


# ─── apply_damage ──────────────────────────────────────────────────────────────

def test_apply_damage_reduz_hp():
    char = _make_character(hp_current=10, hp_max=12)
    result = apply_damage(char, 4)
    assert result.hp_current == 6


def test_apply_damage_clamp_zero():
    char = _make_character(hp_current=3, hp_max=12)
    result = apply_damage(char, 10)
    assert result.hp_current == 0


def test_apply_damage_zero_nao_muda_hp():
    char = _make_character(hp_current=8, hp_max=12)
    result = apply_damage(char, 0)
    assert result.hp_current == 8


def test_apply_damage_nao_muta_input():
    char = _make_character(hp_current=10, hp_max=12)
    hp_original = char.hp_current
    result = apply_damage(char, 5)
    assert char.hp_current == hp_original  # input não mutado
    assert result.hp_current == 5  # retorno tem o valor novo


# ─── apply_consequence — HP ────────────────────────────────────────────────────

def test_apply_consequence_dano():
    state = _make_state(hp_current=10, hp_max=12)
    proposal = ConsequenceProposal(hp_delta=-4)
    result = apply_consequence(state, proposal)
    assert result.character.hp_current == 6


def test_apply_consequence_cura():
    state = _make_state(hp_current=6, hp_max=12)
    proposal = ConsequenceProposal(hp_delta=3)
    result = apply_consequence(state, proposal)
    assert result.character.hp_current == 9


def test_apply_consequence_cura_clamp_hp_max():
    state = _make_state(hp_current=11, hp_max=12)
    proposal = ConsequenceProposal(hp_delta=5)
    result = apply_consequence(state, proposal)
    assert result.character.hp_current == 12


def test_apply_consequence_dano_clamp_zero():
    state = _make_state(hp_current=2, hp_max=12)
    proposal = ConsequenceProposal(hp_delta=-100)
    result = apply_consequence(state, proposal)
    assert result.character.hp_current == 0


# ─── apply_consequence — itens ─────────────────────────────────────────────────

def test_apply_consequence_adiciona_item_novo():
    state = _make_state()
    proposal = ConsequenceProposal(
        items_added=[InventoryItem(name="Poção de cura", quantity=1)]
    )
    result = apply_consequence(state, proposal)
    assert len(result.inventory) == 1
    assert result.inventory[0].name == "Poção de cura"


def test_apply_consequence_adiciona_item_empilha_existente():
    state = _make_state(inventory=[InventoryItem(name="Seta", quantity=10)])
    proposal = ConsequenceProposal(
        items_added=[InventoryItem(name="Seta", quantity=5)]
    )
    result = apply_consequence(state, proposal)
    assert len(result.inventory) == 1
    assert result.inventory[0].quantity == 15


def test_apply_consequence_remove_item_completamente():
    state = _make_state(inventory=[InventoryItem(name="Tocha", quantity=1)])
    proposal = ConsequenceProposal(items_removed=[ItemRemoveProposal(name="Tocha", quantity=1)])
    result = apply_consequence(state, proposal)
    assert len(result.inventory) == 0


def test_apply_consequence_remove_item_parcialmente():
    state = _make_state(inventory=[InventoryItem(name="Flecha", quantity=5)])
    proposal = ConsequenceProposal(items_removed=[ItemRemoveProposal(name="Flecha", quantity=3)])
    result = apply_consequence(state, proposal)
    assert result.inventory[0].quantity == 2


def test_apply_consequence_remove_item_inexistente_levanta_valueerror():
    state = _make_state()
    proposal = ConsequenceProposal(items_removed=[ItemRemoveProposal(name="Espada mágica")])
    with pytest.raises(ValueError, match="item não encontrado"):
        apply_consequence(state, proposal)


def test_apply_consequence_remove_quantidade_maior_que_estoque_levanta_valueerror():
    state = _make_state(inventory=[InventoryItem(name="Seta", quantity=2)])
    proposal = ConsequenceProposal(items_removed=[ItemRemoveProposal(name="Seta", quantity=5)])
    with pytest.raises(ValueError, match="quantidade insuficiente"):
        apply_consequence(state, proposal)


# ─── apply_consequence — localização ──────────────────────────────────────────

def test_apply_consequence_atualiza_localizacao():
    state = _make_state()
    nova_loc = Location(id="floresta", name="Floresta Sombria", description="Escuro aqui.")
    proposal = ConsequenceProposal(new_location=nova_loc)
    result = apply_consequence(state, proposal)
    assert result.location.id == "floresta"
    assert result.location.name == "Floresta Sombria"


def test_apply_consequence_nova_localizacao_entra_em_locations_revealed():
    state = _make_state()
    nova_loc = Location(id="ruinas", name="Ruínas", description="")
    proposal = ConsequenceProposal(new_location=nova_loc)
    result = apply_consequence(state, proposal)
    assert "ruinas" in result.flags.locations_revealed


def test_apply_consequence_localizacao_ja_revelada_nao_duplica():
    state = _make_state()
    state = state.model_copy(
        update={"flags": state.flags.model_copy(update={"locations_revealed": ["floresta"]})}
    )
    nova_loc = Location(id="floresta", name="Floresta", description="")
    proposal = ConsequenceProposal(new_location=nova_loc)
    result = apply_consequence(state, proposal)
    assert result.flags.locations_revealed.count("floresta") == 1


# ─── apply_consequence — flags ─────────────────────────────────────────────────

def test_apply_consequence_adiciona_evento():
    state = _make_state()
    proposal = ConsequenceProposal(events_occurred=["encontrou_mercador"])
    result = apply_consequence(state, proposal)
    assert "encontrou_mercador" in result.flags.events_occurred


def test_apply_consequence_eventos_nao_duplicam():
    state = _make_state()
    state = state.model_copy(
        update={"flags": state.flags.model_copy(update={"events_occurred": ["evento_a"]})}
    )
    proposal = ConsequenceProposal(events_occurred=["evento_a", "evento_b"])
    result = apply_consequence(state, proposal)
    assert result.flags.events_occurred.count("evento_a") == 1
    assert "evento_b" in result.flags.events_occurred


def test_apply_consequence_adiciona_objetivo_completo():
    state = _make_state()
    proposal = ConsequenceProposal(objectives_completed=["resgatar_aldeao"])
    result = apply_consequence(state, proposal)
    assert "resgatar_aldeao" in result.flags.objectives_completed


def test_apply_consequence_objetivos_nao_duplicam():
    state = _make_state()
    state = state.model_copy(
        update={
            "flags": state.flags.model_copy(
                update={"objectives_completed": ["objetivo_1"]}
            )
        }
    )
    proposal = ConsequenceProposal(objectives_completed=["objetivo_1"])
    result = apply_consequence(state, proposal)
    assert result.flags.objectives_completed.count("objetivo_1") == 1


# ─── Pureza de input ───────────────────────────────────────────────────────────

def test_apply_consequence_nao_muta_state_original():
    state = _make_state(
        hp_current=10,
        inventory=[InventoryItem(name="Tocha", quantity=2)],
    )
    hp_original = state.character.hp_current
    inv_original_len = len(state.inventory)

    proposal = ConsequenceProposal(
        hp_delta=-3,
        items_added=[InventoryItem(name="Poção de cura")],
        events_occurred=["novo_evento"],
    )
    result = apply_consequence(state, proposal)

    # Input não mutado
    assert state.character.hp_current == hp_original
    assert len(state.inventory) == inv_original_len
    assert state.flags.events_occurred == []

    # Retorno com valores novos
    assert result.character.hp_current == 7
    assert len(result.inventory) == 2
    assert "novo_evento" in result.flags.events_occurred


def test_apply_consequence_proposta_vazia_retorna_estado_equivalente():
    state = _make_state(hp_current=10)
    result = apply_consequence(state, ConsequenceProposal())
    assert result.character.hp_current == state.character.hp_current
    assert result.inventory == state.inventory
    assert result.location == state.location


# ─── history não é tocada ──────────────────────────────────────────────────────

def test_apply_consequence_nao_toca_history():
    from datetime import UTC, datetime

    entry = HistoryEntry(
        turn=1,
        player_action="atacar goblin",
        narration="O herói avança.",
        timestamp=datetime.now(UTC),
    )
    state = _make_state()
    state = state.model_copy(update={"history": [entry]})
    result = apply_consequence(state, ConsequenceProposal(hp_delta=-1))
    assert len(result.history) == 1
    assert result.history[0].turn == 1
