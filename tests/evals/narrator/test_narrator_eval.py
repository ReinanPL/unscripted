"""Eval set do NarratorAgent contra Gemini real (ADR-043).

Escopo: regressão grossa apenas (D8 do plano). Não persegue nota alta
nem fluência — heurística sobre prosa é ruidosa por natureza. Três
modos de falha são bloqueantes:

  (a) regra alucinada — narração menciona mecânica (números de dado,
      "rolagem", "dificuldade", "perícia", "DC X").
  (b) meta-fala — agente sai do papel ("como mestre", "vou narrar").
  (c) contradição direta de lore — quando o `lore_context` afirma X,
      narração não pode afirmar não-X.

Opt-in via marker `eval`:

    GEMINI_API_KEY=... pytest -m eval tests/evals/narrator/ --no-cov
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

import pytest
from google.adk.agents import LlmAgent
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.narrator import build_narrator_agent
from app.config import Settings
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

_APP_NAME = "unscripted-eval-narrator"
_USER_ID = "eval"

pytestmark = pytest.mark.eval


_KEY_ATTR_BY_PROVIDER = {
    "gemini_aistudio": "gemini_api_key",
    "groq": "groq_api_key",
    "openai": "openai_api_key",
}


@pytest.fixture(scope="module")
def narrator_agent() -> LlmAgent:
    """Constrói o agente uma vez por módulo. Skip se a chave do provider
    ativo (`LLM_PROVIDER`) não estiver presente no `.env` / `Settings`.
    """
    settings = Settings()  # type: ignore[call-arg]
    attr = _KEY_ATTR_BY_PROVIDER.get(settings.llm_provider)
    if not attr or not getattr(settings, attr, ""):
        pytest.skip(
            f"Chave do provider '{settings.llm_provider}' ausente em .env; "
            f"eval contra LLM real ignorado."
        )
    provider = get_llm_provider(settings)
    return build_narrator_agent(provider)


@pytest.fixture(scope="module")
def runner(narrator_agent: LlmAgent) -> Runner:
    return Runner(
        app_name=_APP_NAME,
        agent=narrator_agent,
        session_service=InMemorySessionService(),
    )


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


async def _narrate(runner: Runner, case: dict[str, Any]) -> str:
    """Cria sessão, injeta state, invoca o narrator e devolve a prosa concatenada."""
    session_id = f"case-{id(case['name'])}-{case['name']}"
    state = {
        "action": case["action"],
        "ruling": _serialize(case["ruling"]),
        "roll_outcome": _serialize(case.get("roll_outcome")),
        "consequence_applied": _serialize(case["consequence_applied"]),
        "lore_context": case.get("lore_context", ""),
    }
    await runner.session_service.create_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id, state=state
    )
    session = await runner.session_service.get_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
    )
    assert session is not None
    await runner.session_service.append_event(
        session,
        Event(
            invocation_id="eval-state",
            author="system",
            actions=EventActions(state_delta=state),
        ),
    )
    msg = types.Content(role="user", parts=[types.Part(text="narrar turno")])
    collected = ""
    async for event in runner.run_async(
        user_id=_USER_ID, session_id=session_id, new_message=msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    collected += part.text
    return collected


def _check_narration(case: dict[str, Any], narration: str) -> list[str]:
    """Aplica os checks de regressão grossa. Retorna falhas (vazia = passou)."""
    failures: list[str] = []
    text = narration.lower()

    for pattern in case.get("expected_forbidden") or []:
        if re.search(pattern, text, flags=re.IGNORECASE):
            failures.append(f"narração contém padrão proibido /{pattern}/")

    for contradiction in case.get("lore_contradictions") or []:
        if contradiction.lower() in text:
            failures.append(f"narração contradiz o lore: contém {contradiction!r}")

    if not narration.strip():
        failures.append("narração vazia")

    return failures


async def test_narrator_eval_set(
    load_cases: Callable[..., list[dict[str, Any]] | dict[str, Any]],
    runner: Runner,
) -> None:
    raw = load_cases()
    cases: list[dict[str, Any]] = list(raw) if isinstance(raw, list) else raw["cases"]

    report_lines = ["", "=== EVAL Narrator (regressão grossa) ==="]
    failures_total = 0

    for case in cases:
        name = case["name"]
        try:
            narration = await _narrate(runner, case)
        except Exception as exc:
            report_lines.append(f"[X] {name:45s} — erro de invocação: {exc}")
            failures_total += 1
            continue

        case_failures = _check_narration(case, narration)
        if case_failures:
            failures_total += 1
            report_lines.append(f"[X] {name}")
            for f in case_failures:
                report_lines.append(f"    · {f}")
            preview = narration[:200].replace("\n", " ")
            report_lines.append(f"    preview: {preview!r}")
        else:
            report_lines.append(f"[OK] {name:45s} ({len(narration):>4} chars)")

    report_lines.append("")
    report_lines.append(f"Total: {len(cases) - failures_total}/{len(cases)} passaram")
    print("\n".join(report_lines))

    assert failures_total == 0, f"{failures_total} caso(s) falharam — ver relatório"
