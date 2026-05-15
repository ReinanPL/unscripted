"""Testes de integração dos FunctionTools — chamados diretamente, sem agente."""
import pytest

from app.agents.tools import (
    apply_consequence_tool,
    apply_damage_tool,
    check_skill_tool,
    roll_dice_tool,
)
from app.state.models import (
    Character,
    CharacterAttributes,
    Flags,
    GameState,
    HiddenState,
    InventoryItem,
    Location,
)


def _state_dict(hp_current: int = 10, hp_max: int = 12) -> dict:
    state = GameState(
        character=Character(
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
        ),
        inventory=[InventoryItem(name="Espada longa", quantity=1)],
        location=Location(id="taverna", name="Taverna", description=""),
        flags=Flags(),
        history=[],
        hidden_state=HiddenState(),
    )
    return state.model_dump()


# ─── roll_dice_tool ─────────────────────────────────────────────────────────────

def test_roll_dice_tool_retorna_dict_com_campos_esperados():
    result = roll_dice_tool.func("1d20")
    assert isinstance(result, dict)
    assert "notation" in result
    assert "rolls" in result
    assert "total" in result
    assert "modifier" in result
    assert "advantage" in result
    assert "disadvantage" in result


def test_roll_dice_tool_total_dentro_do_range():
    for i in range(20):
        result = roll_dice_tool.func("1d6+3")
        assert 4 <= result["total"] <= 9


def test_roll_dice_tool_vantagem():
    result = roll_dice_tool.func("adv:1d20")
    assert result["advantage"] is True
    assert len(result["rolls"]) == 2
    assert result["total"] == max(result["rolls"])


def test_roll_dice_tool_desvantagem():
    result = roll_dice_tool.func("dis:1d20")
    assert result["disadvantage"] is True
    assert result["total"] == min(result["rolls"])


def test_roll_dice_tool_notacao_invalida_levanta_valueerror():
    with pytest.raises(ValueError):
        roll_dice_tool.func("invalido")


# ─── check_skill_tool ──────────────────────────────────────────────────────────

def test_check_skill_tool_retorna_roll_e_check():
    result = check_skill_tool.func("1d20", 15)
    assert "roll" in result
    assert "check" in result
    assert "success" in result["check"]
    assert "margin" in result["check"]
    assert "difficulty" in result["check"]
    assert result["check"]["difficulty"] == 15


def test_check_skill_tool_check_coerente_com_roll():
    result = check_skill_tool.func("1d20+5", 15)
    roll_total = result["roll"]["total"]
    assert result["check"]["roll_total"] == roll_total
    assert result["check"]["success"] == (roll_total >= 15)
    assert result["check"]["margin"] == roll_total - 15


# ─── apply_damage_tool ─────────────────────────────────────────────────────────

def test_apply_damage_tool_reduz_hp():
    char = Character(
        name="Herói",
        character_class="guerreiro",
        level=1,
        hp_current=10,
        hp_max=12,
        attributes=CharacterAttributes(
            strength=16, dexterity=12, constitution=15,
            intelligence=10, wisdom=11, charisma=10,
        ),
    )
    result = apply_damage_tool.func(char.model_dump(), 4)
    assert result["hp_current"] == 6


def test_apply_damage_tool_clamp_zero():
    char = Character(
        name="Herói",
        character_class="guerreiro",
        level=1,
        hp_current=2,
        hp_max=12,
        attributes=CharacterAttributes(
            strength=16, dexterity=12, constitution=15,
            intelligence=10, wisdom=11, charisma=10,
        ),
    )
    result = apply_damage_tool.func(char.model_dump(), 100)
    assert result["hp_current"] == 0


def test_apply_damage_tool_retorna_character_completo():
    char = Character(
        name="Herói",
        character_class="guerreiro",
        level=1,
        hp_current=10,
        hp_max=12,
        attributes=CharacterAttributes(
            strength=16, dexterity=12, constitution=15,
            intelligence=10, wisdom=11, charisma=10,
        ),
    )
    result = apply_damage_tool.func(char.model_dump(), 3)
    assert result["name"] == "Herói"
    assert result["hp_max"] == 12
    assert result["hp_current"] == 7


# ─── apply_consequence_tool ────────────────────────────────────────────────────

def test_apply_consequence_tool_aplica_dano():
    state = _state_dict(hp_current=10)
    proposal = {"hp_delta": -5}
    result = apply_consequence_tool.func(state, proposal)
    assert result["character"]["hp_current"] == 5


def test_apply_consequence_tool_aplica_cura():
    state = _state_dict(hp_current=6, hp_max=12)
    proposal = {"hp_delta": 4}
    result = apply_consequence_tool.func(state, proposal)
    assert result["character"]["hp_current"] == 10


def test_apply_consequence_tool_adiciona_item():
    state = _state_dict()
    proposal = {"items_added": [{"name": "Poção de cura", "quantity": 1}]}
    result = apply_consequence_tool.func(state, proposal)
    nomes = [item["name"] for item in result["inventory"]]
    assert "Poção de cura" in nomes


def test_apply_consequence_tool_rejeita_item_inexistente():
    state = _state_dict()
    proposal = {"items_removed": [{"name": "Item Fantasma", "quantity": 1}]}
    with pytest.raises(ValueError, match="item não encontrado"):
        apply_consequence_tool.func(state, proposal)


def test_apply_consequence_tool_proposta_vazia_retorna_estado_inalterado():
    state = _state_dict(hp_current=10)
    result = apply_consequence_tool.func(state, {})
    assert result["character"]["hp_current"] == 10
