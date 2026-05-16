"""Acumulador de chunks de texto que emite frases completas.

Usado pelo `_stream_agent_text` (ADR-048) para detectar fim de frase
na narração do `NarratorAgent` em tempo real e disparar TTS por frase
em paralelo — em vez de esperar o texto inteiro pra começar a sintetizar.

Detecta como terminador de frase:
- `\\n` (newline / quebra de parágrafo).
- `.`, `!`, `?`, `…` seguidos de whitespace, **exceto quando**:
    - é um decimal (`3.5`): dígito antes e dígito depois do ponto.
    - a palavra anterior é uma abreviação conhecida (`Sr.`, `Dr.`, `etc.`).
- Sequências como `...` ou `?!` fecham só uma vez (no último char).
- Terminador colado a fechadores (`."` , `?)`, `…”`) também fecha quando
  vem whitespace depois dos fechadores.

Terminador no **fim do buffer** (sem nada depois) **não fecha** — espera
o próximo chunk pra confirmar que era fim de frase de verdade.

Função pura: instância nova por stream; sem efeitos colaterais.
"""

from __future__ import annotations

_TERMINATORS = frozenset(".!?…")
# Caracteres que podem aparecer GRUDADOS depois do terminador antes do
# whitespace que de fato fecha a frase. Ex.: 'ele disse "olá." E saiu.'
_CLOSERS = frozenset('")]}»”’')
# Abreviações PT-BR comuns. Lista curta — falsos positivos aqui só
# atrasam o fechamento da frase, não corrompem nada.
_ABBREVIATIONS = frozenset(
    {
        "sr",
        "sra",
        "srta",
        "dr",
        "dra",
        "etc",
        "ex",
        "vs",
        "obs",
        "p",
        "pg",
    }
)


class SentenceBuffer:
    """Stateful: instanciar uma por stream do Narrator/NPC."""

    def __init__(self) -> None:
        self._buf: str = ""

    def push(self, chunk: str) -> list[str]:
        """Acumula `chunk` e devolve as frases completas detectadas."""
        if chunk:
            self._buf += chunk
        out: list[str] = []
        while True:
            end = self._next_sentence_end()
            if end is None:
                break
            sentence = self._buf[:end].strip()
            self._buf = self._buf[end:].lstrip()
            if sentence:
                out.append(sentence)
        return out

    def flush(self) -> str:
        """Devolve qualquer residual sem terminador. Usar ao fim do stream."""
        result = self._buf.strip()
        self._buf = ""
        return result

    def _next_sentence_end(self) -> int | None:
        i = 0
        n = len(self._buf)
        while i < n:
            c = self._buf[i]
            if c == "\n":
                return i + 1
            if c in _TERMINATORS:
                # Sequência de terminadores: pula até o último.
                while i + 1 < n and self._buf[i + 1] in _TERMINATORS:
                    i += 1
                # Anda pelos fechadores grudados (aspas, parênteses).
                j = i + 1
                while j < n and self._buf[j] in _CLOSERS:
                    j += 1
                if j >= n:
                    # Tudo até o fim do buffer — espera próximo chunk.
                    return None
                nxt = self._buf[j]
                if not nxt.isspace():
                    # Decimal: dígito antes e dígito depois (só vale pra `.`).
                    if c == "." and i > 0 and self._buf[i - 1].isdigit() and nxt.isdigit():
                        i += 1
                        continue
                    # Outro caractere grudado — não é fim de frase. Avança.
                    i = j
                    continue
                # nxt é whitespace. Verifica abreviação.
                word = self._word_before(i)
                if word.lower() in _ABBREVIATIONS:
                    i = j
                    continue
                return j + 1
            i += 1
        return None

    def _word_before(self, idx: int) -> str:
        j = idx - 1
        end = idx
        while j >= 0 and self._buf[j].isalpha():
            j -= 1
        return self._buf[j + 1 : end]
