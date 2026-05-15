from __future__ import annotations

from typing import Any

from google.adk.tools.function_tool import FunctionTool

from app.rules.checks import check
from app.rules.consequences import apply_consequence, apply_damage
from app.rules.dice import roll
from app.rules.proposals import ConsequenceProposal
from app.state.models import Character, GameState


def _roll_dice(notation: str) -> dict[str, Any]:
    """Rola dados a partir de notação padrão (ex: 1d20, 2d6+3, adv:1d20, dis:1d20)."""
    return roll(notation).model_dump()


def _check_skill(notation: str, difficulty: int) -> dict[str, Any]:
    """Rola dados e compara com dificuldade. Retorna resultado da rolagem e sucesso/falha."""
    roll_result = roll(notation)
    check_result = check(roll_result, difficulty)
    return {"roll": roll_result.model_dump(), "check": check_result.model_dump()}


def _apply_damage(character: dict[str, Any], amount: int) -> dict[str, Any]:
    """Aplica dano a um personagem e retorna o Character atualizado (hp nunca abaixo de 0)."""
    char = Character.model_validate(character)
    return apply_damage(char, amount).model_dump()


def _apply_consequence(state: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Valida proposta tipada do LLM e aplica ao GameState. Rejeita propostas inválidas."""
    game_state = GameState.model_validate(state)
    prop = ConsequenceProposal.model_validate(proposal)
    return apply_consequence(game_state, prop).model_dump()


roll_dice_tool = FunctionTool(func=_roll_dice)
check_skill_tool = FunctionTool(func=_check_skill)
apply_damage_tool = FunctionTool(func=_apply_damage)
apply_consequence_tool = FunctionTool(func=_apply_consequence)
