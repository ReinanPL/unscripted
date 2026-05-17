"""Mede a taxa de silencio do paliativo intencao_residual (ADR-051).

## Por que este script existe

O ADR-051 introduz `Ruling.intencao_residual` como paliativo para
quando o jogador declara duas intencoes numa frase. O paliativo
cumpre o papel quando o LLM **ou** preenche o campo **ou** resolve
ambas as intencoes na propria consequencia. Falha quando faz
silencio (nenhum dos dois).

A taxa de silencio determina o status do paliativo:
- 0% (ou muito baixa) → paliativo robusto; Fase 3.6 (acao composta
  nativa) e decisao de produto, nao conserto urgente.
- alta → paliativo nao cumpre; Fase 3.6 vira prioridade.

Tambem fecha um caveat especifico documentado no ADR-051: a
medicao original cobriu OpenAI (10 runs) e Gemini (10 runs), mas
o Groq teve apenas 1 datapoint valido (TPD diario esgotou).
Rodar este script com `LLM_PROVIDER=groq` quando o TPD resetar
fecha o caveat — por isso o script vive no repo, nao foi descartado
depois da medicao inicial.

## O que mede

Para cada caso multi-intencao do `tests/evals/referee/cases.yaml`,
roda N vezes (sampling do LLM tem variancia) e classifica cada
rodada em uma de tres categorias:

  - "residual": `Ruling.intencao_residual` preenchido com texto
    que contem alguma das `intencao_residual_keywords` do caso.
  - "consequencia": campo residual vazio MAS a consequencia
    aplicada cobre a 2a intencao (`new_location` aponta pro destino,
    ou `events_occurred` contem alguma keyword).
  - "silencio": nem um nem outro — a 2a intencao evaporou em
    silencio (e o que motivou o ADR-051).

## Como rodar

Requer `.env` com a chave do provider escolhido. Marcado opt-in
porque consome quota de LLM (sampling × casos):

    LLM_PROVIDER=openai python scripts/measure_residual_fill_rate.py
    LLM_PROVIDER=gemini_aistudio python scripts/measure_residual_fill_rate.py
    LLM_PROVIDER=groq python scripts/measure_residual_fill_rate.py

Ajustar `RUNS_PER_CASE` no topo do arquivo se precisar mais/menos
amostras (default = 3, suficiente pra Groq sem estourar TPD).

## Saida

Lista cada rodada (categoria + ruling.intencao_residual + texto
da consequencia), o total por caso, e um agregado final por
categoria com percentuais. Apresentar no fechamento de qualquer
re-medicao futura.
"""

from __future__ import annotations

import asyncio
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.agents.contracts import Ruling
from app.agents.referee import build_referee_agent
from app.config import Settings
from app.providers.llm import get_llm_provider
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

CASES_PATH = Path(__file__).resolve().parents[1] / "tests/evals/referee/cases.yaml"
RUNS_PER_CASE = 3
APP = "diag-fill-rate"


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _any_keyword(text: str, kws: list[str]) -> bool:
    norm = _strip_accents(text.lower())
    return any(_strip_accents(k.lower()) in norm for k in kws)


def _consequence_text(r: Ruling) -> str:
    cons = r.consequencia or r.consequencia_sucesso or r.consequencia_falha
    if cons is None:
        return ""
    parts = list(cons.events_occurred)
    if cons.new_location is not None:
        parts.extend([cons.new_location.id, cons.new_location.name])
    return " ".join(parts)


def classify(r: Ruling, keywords: list[str]) -> str:
    residual = r.intencao_residual or ""
    if residual and _any_keyword(residual, keywords):
        return "residual"
    if _any_keyword(_consequence_text(r), keywords):
        return "consequencia"
    return "silencio"


async def run_case(runner: Runner, action: str, state_summary: str, run_idx: int) -> Ruling:
    sid = f"run-{run_idx}-{id(action)}"
    delta = {"action": action, "state_summary": state_summary, "rules_context": ""}
    await runner.session_service.create_session(
        app_name=APP, user_id="u", session_id=sid, state=delta
    )
    sess = await runner.session_service.get_session(
        app_name=APP, user_id="u", session_id=sid
    )
    assert sess is not None
    await runner.session_service.append_event(
        sess,
        Event(
            invocation_id="s",
            author="system",
            actions=EventActions(state_delta=delta),
        ),
    )
    msg = types.Content(role="user", parts=[types.Part(text="resolver turno")])
    final = ""
    async for ev in runner.run_async(user_id="u", session_id=sid, new_message=msg):
        if ev.is_final_response() and ev.content and ev.content.parts:
            t = ev.content.parts[0].text
            if t:
                final = t
    return Ruling.model_validate_json(final)


async def main() -> None:
    settings = Settings()  # type: ignore[call-arg]
    provider = get_llm_provider(settings)
    agent = build_referee_agent(provider)
    svc = InMemorySessionService()
    runner = Runner(app_name=APP, agent=agent, session_service=svc)

    cases = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
    multi = [c for c in cases if c["expected"].get("intencao_residual_keywords")]

    print(f"\n=== Taxa de preenchimento ({settings.llm_provider}) — "
          f"{RUNS_PER_CASE} runs por caso ===\n")

    totals = {"residual": 0, "consequencia": 0, "silencio": 0}
    case_results: list[tuple[str, dict[str, int]]] = []

    for case in multi:
        counters = {"residual": 0, "consequencia": 0, "silencio": 0}
        details: list[str] = []
        for i in range(RUNS_PER_CASE):
            try:
                r = await run_case(runner, case["action"], case["state_summary"], i)
            except Exception as e:
                details.append(f"  run {i}: ERRO {type(e).__name__}: {str(e)[:80]}")
                await asyncio.sleep(3)
                continue
            cat = classify(r, case["expected"]["intencao_residual_keywords"])
            counters[cat] += 1
            details.append(
                f"  run {i}: {cat:12s} | residual={r.intencao_residual!r} | "
                f"cons={_consequence_text(r)!r}"
            )
            await asyncio.sleep(3)
        case_results.append((case["name"], counters))
        for k in totals:
            totals[k] += counters[k]
        print(f"[{case['name']}]")
        for d in details:
            print(d)
        print(f"  totais: residual={counters['residual']} "
              f"consequencia={counters['consequencia']} "
              f"silencio={counters['silencio']}\n")

    total_runs = sum(totals.values())
    print(f"=== AGREGADO ({total_runs} runs) ===")
    if total_runs:
        for k, v in totals.items():
            pct = 100 * v / total_runs
            print(f"  {k:12s}: {v}/{total_runs} ({pct:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
