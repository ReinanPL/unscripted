from __future__ import annotations

import random
import re

from pydantic import BaseModel

_NOTATION_RE = re.compile(
    r"^(?:(?P<mode>adv|dis):)?(?P<count>\d+)d(?P<sides>\d+)(?P<mod>[+-]\d+)?$",
    re.IGNORECASE,
)


class RollResult(BaseModel):
    notation: str
    rolls: list[int]
    modifier: int
    total: int
    advantage: bool = False
    disadvantage: bool = False


def _parse(notation: str) -> tuple[str | None, int, int, int]:
    m = _NOTATION_RE.match(notation.strip())
    if not m:
        raise ValueError(f"notação inválida: {notation!r}")
    mode = m.group("mode").lower() if m.group("mode") else None
    count = int(m.group("count"))
    sides = int(m.group("sides"))
    modifier = int(m.group("mod")) if m.group("mod") else 0
    if sides < 1:
        raise ValueError(f"número de faces deve ser >= 1: {notation!r}")
    if count < 1:
        raise ValueError(f"número de dados deve ser >= 1: {notation!r}")
    return mode, count, sides, modifier


def roll(notation: str, *, seed: int | None = None) -> RollResult:
    """Rola dados a partir de notação padrão. seed=N para testes determinísticos."""
    rng = random.Random(seed)
    mode, count, sides, modifier = _parse(notation)

    if mode == "adv":
        rolls = [rng.randint(1, sides), rng.randint(1, sides)]
        total = max(rolls) + modifier
        return RollResult(
            notation=notation,
            rolls=rolls,
            modifier=modifier,
            total=total,
            advantage=True,
        )

    if mode == "dis":
        rolls = [rng.randint(1, sides), rng.randint(1, sides)]
        total = min(rolls) + modifier
        return RollResult(
            notation=notation,
            rolls=rolls,
            modifier=modifier,
            total=total,
            disadvantage=True,
        )

    rolls = [rng.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    return RollResult(notation=notation, rolls=rolls, modifier=modifier, total=total)
