"""Testes do `_stream_agent_text`.

Runner falso (yielda eventos pré-definidos) cobre a lógica de dedupe
sem chamar LLM real. O caso central é o que motivou o Fix do dedupe:
deltas curtos comuns (' e ', ' de ', ' ao ') chegando depois de o
yielded já conter essas letras em outras palavras — antes do fix
eram descartados pelo ramo `elif text in yielded: continue`; depois,
emitidos corretamente.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.runner_turn import _stream_agent_text


class _FakeEvent:
    """Mimetiza a interface event.content.parts[i].text do ADK."""

    def __init__(self, text: str) -> None:
        self.content = _FakeContent(text)

    def is_final_response(self) -> bool:
        return False


class _FakeContent:
    def __init__(self, text: str) -> None:
        self.parts = [_FakePart(text)]


class _FakePart:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeRunner:
    """Yielda os chunks pré-definidos como eventos com 1 part cada."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def run_async(self, **kwargs: Any) -> AsyncIterator[_FakeEvent]:
        for chunk in self._chunks:
            yield _FakeEvent(chunk)


async def _collect(runner: _FakeRunner) -> list[str]:
    out: list[str] = []
    async for piece in _stream_agent_text(runner, "campaign_id", "trigger"):  # type: ignore[arg-type]
        out.append(piece)
    return out


@pytest.mark.asyncio
async def test_pure_deltas_pass_through_unchanged():
    """Sem cumulativos: cada delta sai como veio, na ordem."""
    runner = _FakeRunner(["Você", " caminha", " pela", " floresta", "."])
    out = await _collect(runner)
    assert out == ["Você", " caminha", " pela", " floresta", "."]
    assert "".join(out) == "Você caminha pela floresta."


@pytest.mark.asyncio
async def test_cumulative_growing_emits_only_suffix():
    """Cumulativo crescente: emite só o sufixo novo a cada evento."""
    runner = _FakeRunner(
        [
            "Você",
            "Você caminha",
            "Você caminha pela",
            "Você caminha pela floresta.",
        ]
    )
    out = await _collect(runner)
    assert out == ["Você", " caminha", " pela", " floresta."]


@pytest.mark.asyncio
async def test_short_delta_e_after_yielded_has_e_is_emitted():
    """REGRESSÃO DO FIX A.

    Cenário medido em campo: ADK emite `" e "` como delta puro depois
    de o yielded já conter outros "e" (em "Você", "se", "encontra"...).
    A versão pré-fix tinha `elif text in yielded: continue` que
    descartava o `" e "` porque `" e " in "...e..."` é True. Resultado:
    "risadas e conversas" virava "risadas conversas" no buffer.

    Pós-fix: o ramo morto sumiu. Deltas curtos legítimos saem.
    """
    runner = _FakeRunner(
        [
            "Você",
            " se",
            " encontra",
            " no salão",
            ",",
            " risadas",
            " e",
            " conversas",
        ]
    )
    out = await _collect(runner)
    assert " e" in out, " e (delta curto) DEVE ser emitido, não descartado"
    full = "".join(out)
    assert full == "Você se encontra no salão, risadas e conversas"
    # Garante explicitamente que a palavra-chave do bug aparece intacta.
    assert "risadas e conversas" in full


@pytest.mark.asyncio
async def test_short_delta_de_after_de_already_in_yielded():
    """Mesmo padrão pra `de` — apareceu em campo como descartado."""
    runner = _FakeRunner(
        [
            "O cheiro",
            " de",
            " cerveja",
            " e",
            " carne",
            " grelhada",
            " preenche",
            " o ar",
            ".",
        ]
    )
    out = await _collect(runner)
    full = "".join(out)
    assert full == "O cheiro de cerveja e carne grelhada preenche o ar."
    # As palavras de uma letra/curtas que o bug pegava saem todas.
    assert " de" in out
    assert " e" in out


@pytest.mark.asyncio
async def test_substring_match_at_end_of_yielded_is_NOT_dropped():
    """Outro cenário do bug antigo: text é sufixo exato do yielded.

    Antes do fix: `text in yielded` retornava True (sufixo é substring)
    e o delta era descartado. Pós-fix: emite normalmente — o ADK pode
    emitir uma palavra que coincide com o final do que já saiu, e isso
    é parte legítima da próxima frase.
    """
    runner = _FakeRunner(["Olá mundo", " mundo"])
    out = await _collect(runner)
    # O segundo " mundo" não é cumulativo (não começa com "Olá mundo"),
    # então sai como delta. O fix garante que não é descartado.
    assert out == ["Olá mundo", " mundo"]


@pytest.mark.asyncio
async def test_empty_parts_are_skipped():
    """Parts com text=None ou "" são ignorados, não quebram nada."""
    runner = _FakeRunner(["Você", "", " caminha"])
    out = await _collect(runner)
    assert out == ["Você", " caminha"]
