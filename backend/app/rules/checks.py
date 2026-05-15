from __future__ import annotations

from pydantic import BaseModel

from app.rules.dice import RollResult


class CheckResult(BaseModel):
    success: bool
    roll_total: int
    difficulty: int
    margin: int  # roll_total - difficulty; positivo = passou por X, negativo = falhou por X


def check(roll_result: RollResult, difficulty: int) -> CheckResult:
    margin = roll_result.total - difficulty
    return CheckResult(
        success=roll_result.total >= difficulty,
        roll_total=roll_result.total,
        difficulty=difficulty,
        margin=margin,
    )
