"""Testes do `_stream_with_audio` em isolamento (ADR-048).

Não chamam LLM real nem TTS real. Injetam:
- Um runner falso que `run_async()` yielda eventos com partes-texto.
- Um `TtsProvider` falso que `synthesize()` retorna bytes determinísticos
  (ou levanta exceção, para validar tratamento de falha por frase).

Cobrem:
- Texto chega como `narration_chunk` na ordem dos chunks emitidos.
- Com tts_provider, cada frase fechada vira um `audio_sentence` em
  ordem de `sentence_index`.
- Sem tts_provider (None), nenhum `audio_sentence` é emitido — zero
  chamadas TTS.
- Falha de TTS de uma frase NÃO bloqueia as outras: a frase falhada é
  pulada (sem `audio_sentence` para ela), texto segue, `tts_errors`
  acumula a mensagem da falha.
- Reordenação por backend: se a frase N fica pronta antes da N-1,
  espera a N-1 antes de emitir.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.runner_turn import StreamStats, _stream_with_audio


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
    """Runner falso que yielda os chunks pré-definidos."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def run_async(self, **kwargs: Any) -> AsyncIterator[_FakeEvent]:
        for chunk in self._chunks:
            yield _FakeEvent(chunk)


class _FakeTts:
    """TTS falso: synthesize devolve bytes determinísticos por frase."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def synthesize(self, text: str, *, voice: str = "") -> bytes:
        self.calls.append(text)
        # Bytes diferentes por frase pra distinguir nos asserts.
        return text.encode("utf-8")


class _FailingTts:
    """TTS falso que sempre falha — valida ADR-020 estendido."""

    async def synthesize(self, text: str, *, voice: str = "") -> bytes:
        raise TimeoutError(f"timeout simulado para: {text[:20]}")


class _PartialFailingTts:
    """Falha em frases que contêm uma marca; outras OK."""

    def __init__(self, fail_marker: str) -> None:
        self._marker = fail_marker
        self.calls: list[str] = []

    async def synthesize(self, text: str, *, voice: str = "") -> bytes:
        self.calls.append(text)
        if self._marker in text:
            raise RuntimeError(f"falha em: {text[:30]}")
        return text.encode("utf-8")


def _make_stats() -> StreamStats:
    return {"text": "", "next_sentence_index": 0, "tts_errors": []}


@pytest.mark.asyncio
async def test_text_passes_through_without_tts():
    runner = _FakeRunner(["Você caminha. ", "Algo se move. ", "Você para."])
    stats = _make_stats()
    events = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=None,
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        events.append(ev)
    text_events = [e for e in events if e.type == "narration_chunk"]
    audio_events = [e for e in events if e.type == "audio_sentence"]
    assert [e.text for e in text_events] == [
        "Você caminha. ",
        "Algo se move. ",
        "Você para.",
    ]
    assert audio_events == []
    assert stats["text"] == "Você caminha. Algo se move. Você para."
    assert stats["next_sentence_index"] == 0
    assert stats["tts_errors"] == []


@pytest.mark.asyncio
async def test_tts_emits_audio_sentence_in_order():
    runner = _FakeRunner(["Você caminha. ", "Algo se move. ", "Você para."])
    tts = _FakeTts()
    stats = _make_stats()
    audio_events = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=tts,  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_events.append(ev)
    # 3 frases (Você caminha. / Algo se move. / Você para. — a última pelo flush)
    assert [e.sentence_index for e in audio_events] == [0, 1, 2]
    assert tts.calls == [
        "Você caminha.",
        "Algo se move.",
        "Você para.",
    ]
    assert stats["next_sentence_index"] == 3
    assert stats["tts_errors"] == []


@pytest.mark.asyncio
async def test_tts_failure_per_sentence_does_not_block_others():
    runner = _FakeRunner(["Frase um. ", "Frase com bug aqui. ", "Frase tres. "])
    tts = _PartialFailingTts(fail_marker="bug")
    stats = _make_stats()
    audio_indices = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=tts,  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_indices.append(ev.sentence_index)
    # Frase 1 falhou: index 1 pulado, mas 0 e 2 saíram.
    assert audio_indices == [0, 2]
    assert stats["next_sentence_index"] == 3
    assert len(stats["tts_errors"]) == 1
    assert "RuntimeError" in stats["tts_errors"][0]


@pytest.mark.asyncio
async def test_all_tts_failures_yield_no_audio():
    runner = _FakeRunner(["Frase um. ", "Frase dois. "])
    stats = _make_stats()
    audio_events = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=_FailingTts(),  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_events.append(ev)
    assert audio_events == []
    assert len(stats["tts_errors"]) == 2


@pytest.mark.asyncio
async def test_sentence_index_starts_from_offset():
    runner = _FakeRunner(["Apenas uma frase. "])
    stats = _make_stats()
    audio_events = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="npc_chunk",
        npc_id="grimwald",
        tts_provider=_FakeTts(),  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=7,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_events.append(ev)
    assert audio_events[0].sentence_index == 7
    assert stats["next_sentence_index"] == 8


@pytest.mark.asyncio
async def test_reorder_holds_later_audio_until_earlier_ready():
    """Frase 1 termina antes da 0 — backend deve segurar 1 até 0 chegar."""
    runner = _FakeRunner(["Frase um. ", "Frase dois. "])
    completion_order = []

    class _ReverseTts:
        async def synthesize(self, text: str, *, voice: str = "") -> bytes:
            # Frase 1 (a segunda) "termina" antes da 0.
            if "dois" in text:
                await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(0.05)
            completion_order.append(text)
            return text.encode("utf-8")

    stats = _make_stats()
    audio_indices = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=_ReverseTts(),  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_indices.append(ev.sentence_index)
    # Apesar de a frase 1 terminar antes da 0, eventos saíram em ordem.
    assert audio_indices == [0, 1]
    # E a frase "dois" tinha terminado primeiro de fato.
    assert completion_order[0] == "Frase dois."


# ===================== Dedupe de frase (Fix B) =====================
#
# Chave do dedupe = frase normalizada. Frase repetida adjacente (a
# anterior é IGUAL) passa — narrador escrevendo "Silêncio. Silêncio."
# é legítimo. Frase já vista antes mas a anterior é DIFERENTE eh
# tratada como reprocesso do cumulativo gigante e skipada.


@pytest.mark.asyncio
async def test_replayed_sentences_after_other_content_are_skipped():
    """Cenário do "boom" simulado: três frases distintas saem, depois
    um chunk reproduz as mesmas três no fim. Como cada repetição vem
    depois de outra frase diferente, todas batem em "já vista E não-
    adjacente" → todas as repetições são skipadas.
    """
    runner = _FakeRunner(
        [
            "Frase A. ",
            "Frase B. ",
            "Frase C. ",
            # Reprocesso (cenário do bug): mesma sequência de novo.
            "Frase A. Frase B. Frase C. ",
        ]
    )
    tts = _FakeTts()
    stats = _make_stats()
    audio_events: list[Any] = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=tts,  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_events.append(ev)
    # Só as 3 originais saem; o reprocesso inteiro é skipado.
    assert [e.sentence_index for e in audio_events] == [0, 1, 2]
    assert tts.calls == ["Frase A.", "Frase B.", "Frase C."]


@pytest.mark.asyncio
async def test_adjacent_repetition_is_allowed():
    """`"Silêncio. Silêncio."` — repetição imediatamente adjacente é
    caso legítimo do narrador. Ambas saem.
    """
    runner = _FakeRunner(["Silêncio. Silêncio. "])
    tts = _FakeTts()
    stats = _make_stats()
    audio_events: list[Any] = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=tts,  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_events.append(ev)
    # Repetição adjacente legítima → ambas saem.
    assert [e.sentence_index for e in audio_events] == [0, 1]
    assert tts.calls == ["Silêncio.", "Silêncio."]


@pytest.mark.asyncio
async def test_dedupe_is_case_insensitive():
    """Variações de caixa não enganam o dedupe: "Frase." e "FRASE."
    são consideradas a mesma frase.
    """
    runner = _FakeRunner(
        [
            "Frase. ",
            "Outra coisa. ",
            "FRASE. ",  # repetição não-adjacente, case diferente
        ]
    )
    tts = _FakeTts()
    stats = _make_stats()
    audio_events: list[Any] = []
    async for ev in _stream_with_audio(
        runner=runner,  # type: ignore[arg-type]
        campaign_id="c",
        trigger="x",
        text_event_type="narration_chunk",
        npc_id=None,
        tts_provider=tts,  # type: ignore[arg-type]
        tts_voice="echo",
        sentence_index_start=0,
        stats=stats,
    ):
        if ev.type == "audio_sentence":
            audio_events.append(ev)
    # "FRASE." é skipada porque "frase." já está no set e a anterior
    # ("Outra coisa.") não é a mesma → reprocesso.
    assert [e.sentence_index for e in audio_events] == [0, 1]
    assert tts.calls == ["Frase.", "Outra coisa."]


@pytest.mark.asyncio
async def test_repeated_sentence_across_turns_is_allowed():
    """Cada chamada de `_stream_with_audio` tem seu próprio
    `already_synthed` — frases iguais em turnos distintos saem
    normalmente em cada turno.
    """
    for _ in range(2):
        runner = _FakeRunner(["Frase. "])
        tts = _FakeTts()
        stats = _make_stats()
        audio_events: list[Any] = []
        async for ev in _stream_with_audio(
            runner=runner,  # type: ignore[arg-type]
            campaign_id="c",
            trigger="x",
            text_event_type="narration_chunk",
            npc_id=None,
            tts_provider=tts,  # type: ignore[arg-type]
            tts_voice="echo",
            sentence_index_start=0,
            stats=stats,
        ):
            if ev.type == "audio_sentence":
                audio_events.append(ev)
        assert [e.sentence_index for e in audio_events] == [0]
        assert tts.calls == ["Frase."]
