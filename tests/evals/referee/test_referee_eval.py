"""Eval set do RefereeAgent contra Gemini real (ADR-043).

Opt-in via marker `eval`. Para rodar:

    GEMINI_API_KEY=... pytest -m eval tests/evals/referee/

Cada caso é uma chamada ao agente. Os checks são estruturais e
tolerantes — pericia via keywords, dificuldade via faixa, presença de
consequências por modo.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
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


_KEY_ATTR_BY_PROVIDER = {
    "gemini_aistudio": "gemini_api_key",
    "groq": "groq_api_key",
    "openai": "openai_api_key",
}


@pytest.fixture(scope="module")
def referee_agent() -> LlmAgent:
    """Constrói o agente uma vez por módulo — economiza setup nos cases.

    O provider ativo é definido por `LLM_PROVIDER` (env). Skip se a
    chave correspondente não estiver no `.env` / `Settings`.
    """
    settings = Settings()  # type: ignore[call-arg]
    attr = _KEY_ATTR_BY_PROVIDER.get(settings.llm_provider)
    if not attr or not getattr(settings, attr, ""):
        pytest.skip(
            f"Chave do provider '{settings.llm_provider}' ausente em .env; "
            f"eval contra LLM real ignorado."
        )
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
    try:
        return Ruling.model_validate_json(final_text)
    except Exception:
        print(f"\n    JSON bruto recebido:\n    {final_text[:500]}\n")
        raise


def _strip_accents(text: str) -> str:
    """Remove acentos para comparação tolerante (Persuasao ↔ Persuasão)."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


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
        pericia_norm = _strip_accents((ruling.pericia or "").lower())
        if kws and not any(_strip_accents(k.lower()) in pericia_norm for k in kws):
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

    residual_kws: list[str] = expected.get("intencao_residual_keywords") or []
    if residual_kws:
        # Dois caminhos válidos (ADR-051): (a) residual preenchido com a
        # intenção pendente; (b) Ruling já processou a 2ª intenção dentro
        # da própria consequência (ex.: new_location, events_occurred).
        # Falha só quando NEM uma nem outra cobre a intenção.
        residual = ruling.intencao_residual or ""
        residual_norm = _strip_accents(residual.lower())
        residual_match = bool(residual) and any(
            _strip_accents(k.lower()) in residual_norm for k in residual_kws
        )

        cons = (
            ruling.consequencia
            or ruling.consequencia_sucesso
            or ruling.consequencia_falha
        )
        consequence_text = ""
        if cons is not None:
            parts = list(cons.events_occurred)
            if cons.new_location is not None:
                parts.append(cons.new_location.id)
                parts.append(cons.new_location.name)
            consequence_text = _strip_accents(" ".join(parts).lower())
        consequence_match = any(
            _strip_accents(k.lower()) in consequence_text for k in residual_kws
        )

        if not (residual_match or consequence_match):
            failures.append(
                f"intencao_residual ausente e consequência não cobre a "
                f"intenção secundária — esperado conter uma de {residual_kws}; "
                f"residual={residual!r}, consequência={consequence_text!r}"
            )
    if expected.get("intencao_residual_ausente") and ruling.intencao_residual:
        failures.append(
            f"intencao_residual deveria ser None, veio {ruling.intencao_residual!r}"
        )

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
        ruling = None
        last_exc: Exception | None = None
        # Retry com backoff específico para rate limit (Groq TPM ~ 12K/min).
        for attempt in range(3):
            try:
                ruling = await _run_once(
                    runner,
                    action=case["action"],
                    state_summary=case["state_summary"],
                    rules_context=case.get("rules_context", ""),
                )
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                if "rate_limit" in msg.lower() or "RateLimitError" in msg:
                    wait_match = re.search(r"try again in ([\d.]+)s", msg)
                    wait_s = float(wait_match.group(1)) + 1 if wait_match else 12
                    print(
                        f"    rate-limit em {name}, attempt {attempt + 1}; "
                        f"aguardando {wait_s:.1f}s e tentando de novo"
                    )
                    await asyncio.sleep(wait_s)
                    continue
                break
        if ruling is None:
            report_lines.append(
                f"[X] {name:35s} - erro de invocacao: {last_exc}"
            )
            failures_total += 1
            # Pausa curta entre cases pra distribuir o consumo de TPM.
            await asyncio.sleep(2)
            continue

        case_failures = _check_case(case, ruling)
        if case_failures:
            failures_total += 1
            report_lines.append(f"[X] {name}")
            for f in case_failures:
                report_lines.append(f"    · {f}")
            report_lines.append(
                f"    ruling: precisa_rolagem={ruling.precisa_rolagem}, "
                f"pericia={ruling.pericia!r}, dificuldade={ruling.dificuldade}"
            )
        else:
            report_lines.append(
                f"[OK] {name:35s} pericia={ruling.pericia!r} dc={ruling.dificuldade}"
            )
        # Pausa entre cases pra distribuir o consumo de TPM (Groq).
        await asyncio.sleep(2)

    report_lines.append("")
    report_lines.append(f"Total: {len(cases) - failures_total}/{len(cases)} passaram")
    print("\n".join(report_lines))

    assert failures_total == 0, f"{failures_total} caso(s) falharam — ver relatório acima"
