"""Testes do `SentenceBuffer` (ADR-048).

Cobrem os casos chatos que motivam a existência do buffer:
- Frase quebrada entre chunks: precisa acumular.
- Terminador no fim de buffer: NÃO fecha — espera próximo chunk.
- Decimais (`3.5`): ponto entre dígitos não fecha.
- Reticências `...` ou `…`: fecham só no último char.
- Abreviações comuns (`Sr.`, `Dr.`, `etc.`): não fecham.
- Aspas/parênteses fechantes grudados (`."`, `?)`): fecham se houver
  whitespace depois.
- Newline (`\\n`) fecha sempre.
- Múltiplas frases no mesmo chunk: emite todas.
"""

from __future__ import annotations

from app.agents.sentence_buffer import SentenceBuffer


def test_no_terminator_holds_everything():
    b = SentenceBuffer()
    assert b.push("Você caminha pela floresta") == []


def test_terminator_with_space_closes():
    b = SentenceBuffer()
    assert b.push("Você caminha. ") == ["Você caminha."]


def test_terminator_at_buffer_end_holds():
    """Sem whitespace depois do terminador, espera o próximo chunk."""
    b = SentenceBuffer()
    assert b.push("Você caminha.") == []
    assert b.push(" Algo se move. ") == ["Você caminha.", "Algo se move."]


def test_multiple_sentences_in_one_chunk():
    b = SentenceBuffer()
    out = b.push("Você caminha. Algo se move. Você para de andar.")
    assert out == ["Você caminha.", "Algo se move."]
    # "Você para de andar." fica pendente (sem space depois).
    assert b.flush() == "Você para de andar."


def test_sentence_split_across_many_chunks():
    b = SentenceBuffer()
    assert b.push("Você ") == []
    assert b.push("caminha pela ") == []
    assert b.push("floresta. ") == ["Você caminha pela floresta."]


def test_decimal_dot_does_not_close():
    b = SentenceBuffer()
    assert b.push("São 3.5 metros. ") == ["São 3.5 metros."]


def test_decimal_pt_br_comma_is_irrelevant():
    """Vírgula nunca é terminador; deixa passar."""
    b = SentenceBuffer()
    assert b.push("Sobram 3,5 metros até a porta. ") == [
        "Sobram 3,5 metros até a porta."
    ]


def test_ellipsis_three_dots_close_separately():
    """Reticências fecham frase — cada pausa vira áudio TTS próprio."""
    b = SentenceBuffer()
    out = b.push("Talvez... Sim. ")
    assert out == ["Talvez...", "Sim."]


def test_ellipsis_three_dots_split_across_chunks():
    b = SentenceBuffer()
    assert b.push("Talvez..") == []
    assert b.push(". ") == ["Talvez..."]


def test_ellipsis_single_char_closes():
    b = SentenceBuffer()
    assert b.push("Talvez… Sim. ") == ["Talvez…", "Sim."]


def test_abbreviation_sr_does_not_close():
    b = SentenceBuffer()
    assert b.push("O Sr. Grimwald observa. ") == ["O Sr. Grimwald observa."]


def test_abbreviation_dr():
    b = SentenceBuffer()
    assert b.push("O Dr. Salviano chega. ") == ["O Dr. Salviano chega."]


def test_abbreviation_etc():
    b = SentenceBuffer()
    out = b.push("Espadas, escudos, etc. são caros. ")
    assert out == ["Espadas, escudos, etc. são caros."]


def test_newline_closes():
    b = SentenceBuffer()
    assert b.push("Linha um\nLinha dois.") == ["Linha um"]
    assert b.flush() == "Linha dois."


def test_question_mark_closes():
    b = SentenceBuffer()
    assert b.push("O que você faz? Não sei. ") == [
        "O que você faz?",
        "Não sei.",
    ]


def test_exclamation_closes():
    b = SentenceBuffer()
    out = b.push("Cuidado! Atrás de você! ")
    assert out == ["Cuidado!", "Atrás de você!"]


def test_double_exclamation_closes_once():
    b = SentenceBuffer()
    assert b.push("Cuidado!! Atrás. ") == ["Cuidado!!", "Atrás."]


def test_terminator_with_closing_quote():
    b = SentenceBuffer()
    out = b.push('Ele disse "olá." Outro caso. ')
    assert out == ['Ele disse "olá."', "Outro caso."]


def test_terminator_with_closing_paren():
    b = SentenceBuffer()
    assert b.push("(uma nota aqui.) Texto. ") == ["(uma nota aqui.)", "Texto."]


def test_flush_returns_residual():
    b = SentenceBuffer()
    b.push("frase sem fim")
    assert b.flush() == "frase sem fim"
    assert b.flush() == ""


def test_flush_strips_whitespace():
    b = SentenceBuffer()
    b.push("   palavra   ")
    assert b.flush() == "palavra"


def test_decimal_at_end_then_space():
    """Decimal seguido de espaço e mais texto não fecha no `.5`."""
    b = SentenceBuffer()
    assert b.push("São 3.5 metros") == []
    assert b.push(". Próxima frase. ") == ["São 3.5 metros.", "Próxima frase."]


def test_consecutive_terminators_in_split_chunks():
    """Sequência de terminadores entre chunks: o último char define."""
    b = SentenceBuffer()
    assert b.push("Não!?") == []
    assert b.push(" Mas sim. ") == ["Não!?", "Mas sim."]


def test_empty_chunk_safe():
    b = SentenceBuffer()
    assert b.push("") == []
    assert b.push("Você caminha. ") == ["Você caminha."]


def test_only_whitespace_chunk_safe():
    b = SentenceBuffer()
    assert b.push("Frase pendente.") == []
    assert b.push("   ") == ["Frase pendente."]
