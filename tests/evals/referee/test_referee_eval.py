"""Eval set do RefereeAgent contra Gemini real (ADR-043).

Opt-in via marker `eval`. Para rodar:

    GEMINI_API_KEY=... pytest -m eval tests/evals/referee/

Cada caso é uma chamada ao agente. Os checks são estruturais e
tolerantes — pericia via keywords, dificuldade via faixa, presença de
consequências por modo.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import pytest
from google.adk.agents import LlmAgent
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.contracts import Ruling
from app.agents.referee import build_referee_agent
from app.config import Settings
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

_APP_NAME = "unscripted-eval-referee"
_USER_ID = "eval"

pytestmark = pytest.mark.eval


@pytest.fixture(scope="module")
def referee_agent() -> LlmAgent:
    """Constrói o agente uma vez por módulo — economiza setup nos cases."""
    import os

    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY ausente; eval contra LLM real ignorado.")
    settings = Settings()  # type: ignore[call-arg]  # carregado do ambiente
    provider = get_llm_provider(settings)
    return build_referee_agent(provider)


@pytest.fixture(scope="module")
def runner(referee_agent: LlmAgent) -> Runner:
    service = InMemorySessionService()
    return Runner(app_name=_APP_NAME, agent=referee_agent, session_service=service)


async def _run_once(
    runner: Runner,
    *,
    action: str,
    state_summary: str,
    rules_context: str,
) -> Ruling:
    """Cria uma sessão, injeta state, invoca o agente e devolve o Ruling."""
    session_id = f"case-{id((action, state_summary))}"
    await runner.session_service.create_session(
        app_name=_APP_NAME,
        user_id=_USER_ID,
        session_id=session_id,
        state={
            "action": action,
            "state_summary": state_summary,
            "rules_context": rules_context,
        },
    )
    # `state_delta` no Event garante persistência igual ao DatabaseSessionService.
    session = await runner.session_service.get_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
    )
    assert session is not None
    await runner.session_service.append_event(
        session,
        Event(
            invocation_id="eval-state",
            author="system",
            actions=EventActions(
                state_delta={
                    "action": action,
                    "state_summary": state_summary,
                    "rules_context": rules_context,
                }
            ),
        ),
    )

    msg = types.Content(role="user", parts=[types.Part(text="resolver turno")])
    final_text = ""
    async for event in runner.run_async(
        user_id=_USER_ID, session_id=session_id, new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text
            if text:
                final_text = text
    assert final_text, "RefereeAgent não retornou conteúdo"
    return Ruling.model_validate_json(final_text)


def _check_case(case: dict[str, Any], ruling: Ruling) -> list[str]:
    """Aplica os checks do caso. Retorna lista de falhas (vazia = passou)."""
    expected = case["expected"]
    failures: list[str] = []

    if ruling.precisa_rolagem != expected["precisa_rolagem"]:
        failures.append(
            f"precisa_rolagem: esperado {expected['precisa_rolagem']}, "
            f"veio {ruling.precisa_rolagem}"
        )

    if expected.get("precisa_rolagem"):
        kws: list[str] = expected.get("pericia_keywords") or []
        pericia = (ruling.pericia or "").lower()
        if kws and not any(k.lower() in pericia for k in kws):
            failures.append(
                f"pericia {ruling.pericia!r} não contém nenhuma de {kws}"
            )

        d = ruling.dificuldade
        d_min = expected.get("dificuldade_min")
        d_max = expected.get("dificuldade_max")
        if d is None:
            failures.append("dificuldade ausente (precisa_rolagem=True)")
        else:
            if d_min is not None and d < d_min:
                failures.append(f"dificuldade {d} < min {d_min}")
            if d_max is not None and d > d_max:
                failures.append(f"dificuldade {d} > max {d_max}")

        if expected.get("consequencia_sucesso") and ruling.consequencia_sucesso is None:
            failures.append("consequencia_sucesso ausente")
        if expected.get("consequencia_falha") and ruling.consequencia_falha is None:
            failures.append("consequencia_falha ausente")
    else:
        if expected.get("consequencia") and ruling.consequencia is None:
            failures.append("consequencia ausente (precisa_rolagem=False)")

    return failures


async def test_referee_eval_set(
    load_cases: Callable[..., list[dict[str, Any]] | dict[str, Any]],
    runner: Runner,
) -> None:
    raw = load_cases()
    cases: list[dict[str, Any]] = list(raw) if isinstance(raw, list) else raw["cases"]

    report_lines = ["", "=== EVAL Referee ==="]
    failures_total = 0

    for case in cases:
        name = case["name"]
        try:
            ruling = await _run_once(
                runner,
                action=case["action"],
                state_summary=case["state_summary"],
                rules_context=case.get("rules_context", ""),
            )
        except Exception as exc:
            report_lines.append(f"✗ {name:35s} — erro de invocação: {exc}")
            failures_total += 1
            continue

        case_failures = _check_case(case, ruling)
        if case_failures:
            failures_total += 1
            report_lines.append(f"✗ {name}")
            for f in case_failures:
                report_lines.append(f"    · {f}")
            report_lines.append(
                f"    ruling: precisa_rolagem={ruling.precisa_rolagem}, "
                f"pericia={ruling.pericia!r}, dificuldade={ruling.dificuldade}"
            )
        else:
            report_lines.append(
                f"✓ {name:35s} pericia={ruling.pericia!r} dc={ruling.dificuldade}"
            )

    report_lines.append("")
    report_lines.append(f"Total: {len(cases) - failures_total}/{len(cases)} passaram")
    print("\n".join(report_lines))

    assert failures_total == 0, f"{failures_total} caso(s) falharam — ver relatório acima"
