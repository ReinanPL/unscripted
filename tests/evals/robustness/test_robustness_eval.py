"""Eval set determinístico do módulo de robustez (PRD §8, §9; ADR-026).

Roda sem LLM (não precisa do marker `eval`). Mede em escala:
    - Precision: das ações válidas, quantas passam (ok=True)?
    - Recall por categoria: das abusivas, quantas são detectadas
      (ok=False) e classificadas corretamente?

Falha o build se qualquer ação claramente válida for barrada ou
qualquer ação claramente abusiva passar despercebida — esses são os
modos de falha que importam para o jogador. Casos borderline são
reportados sem fail.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.agents.robustness import RobustnessCategory, validate_player_input

_THRESHOLD_PRECISION = 1.0  # 100% das válidas devem passar
_THRESHOLD_RECALL = 1.0  # 100% das abusivas devem ser pegas


def _run_valid(cases: list[str]) -> tuple[int, list[str]]:
    failures: list[str] = []
    for text in cases:
        verdict = validate_player_input(text)
        if not verdict.ok:
            failures.append(
                f"  [X] {text!r}\n"
                f"      → barrada como {verdict.category} (matched={verdict.matched!r})"
            )
    return len(cases) - len(failures), failures


def _run_abusive(
    category: RobustnessCategory, cases: list[str]
) -> tuple[int, list[str]]:
    failures: list[str] = []
    for text in cases:
        verdict = validate_player_input(text)
        if verdict.ok:
            failures.append(f"  [X] {text!r}\n      → passou (deveria virar {category})")
        elif verdict.category != category:
            failures.append(
                f"  [~] {text!r}\n"
                f"      → pega como {verdict.category}, esperado {category}"
            )
    return len(cases) - len(failures), failures


def test_robustness_eval_set(load_cases: Callable[..., dict[str, Any]]) -> None:
    cases = load_cases()

    valid_cases: list[str] = list(cases.get("valid") or [])
    abusive: dict[str, list[str]] = cases.get("abusive") or {}
    borderline: list[dict[str, str]] = cases.get("borderline") or []

    report_lines: list[str] = ["", "=== EVAL Robustez ==="]

    # Válidas — precision
    ok_valid, valid_failures = _run_valid(valid_cases)
    precision = ok_valid / len(valid_cases) if valid_cases else 1.0
    report_lines.append(
        f"Válidas:    {ok_valid}/{len(valid_cases)} passaram  ({precision:.0%})"
    )

    # Abusivas — recall por categoria
    recalls: dict[str, float] = {}
    abusive_failures: list[str] = []
    for category, items in abusive.items():
        cat_lit: RobustnessCategory = category  # type: ignore[assignment]
        ok_cat, fails = _run_abusive(cat_lit, items)
        recalls[category] = ok_cat / len(items) if items else 1.0
        report_lines.append(
            f"Abusivas/{category:25s} {ok_cat}/{len(items)} detectadas  "
            f"({recalls[category]:.0%})"
        )
        abusive_failures.extend(fails)

    # Borderline — apenas relatado
    border_misses: list[str] = []
    for item in borderline:
        verdict = validate_player_input(item["text"])
        actual = "ok" if verdict.ok else f"barrada({verdict.category})"
        if (item["expected"] == "ok") != verdict.ok:
            border_misses.append(
                f"  - {item['text']!r}\n"
                f"      esperado={item['expected']}  atual={actual}\n"
                f"      nota: {item.get('note', '')}"
            )
    report_lines.append(
        f"Borderline: {len(borderline) - len(border_misses)}/{len(borderline)} "
        f"como esperado (falsos positivos aceitáveis na v1, ADR-026)"
    )

    # Imprime sempre — captura via -s; útil mesmo quando passa.
    if valid_failures:
        report_lines.extend(["", "Falhas em VÁLIDAS:", *valid_failures])
    if abusive_failures:
        report_lines.extend(["", "Falhas em ABUSIVAS:", *abusive_failures])
    if border_misses:
        report_lines.extend(["", "Borderline divergente (não bloqueia):", *border_misses])
    print("\n".join(report_lines))

    assert precision >= _THRESHOLD_PRECISION, (
        f"Precision {precision:.0%} < {_THRESHOLD_PRECISION:.0%} — "
        f"ações válidas estão sendo barradas indevidamente"
    )
    for category, recall in recalls.items():
        assert recall >= _THRESHOLD_RECALL, (
            f"Recall em {category} {recall:.0%} < {_THRESHOLD_RECALL:.0%} — "
            f"ações abusivas estão escapando"
        )
