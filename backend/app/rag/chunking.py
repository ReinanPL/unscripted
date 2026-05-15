"""Chunking determinístico de texto para o RAG (ADR-030).

Estratégia: por parágrafo, com tamanho-alvo de aproximadamente `target`
caracteres. Parágrafos curtos consecutivos são agrupados; parágrafos maiores
que `ceil` são divididos em fronteiras de frase.

Função pura, sem efeitos colaterais. Mesma entrada → mesma saída.
"""

from __future__ import annotations

import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _split_paragraph(paragraph: str, ceil: int) -> list[str]:
    """Quebra um parágrafo gigante em pedaços ≤ ceil em fronteira de frase."""
    if len(paragraph) <= ceil:
        return [paragraph]
    sentences = _SENTENCE_BOUNDARY.split(paragraph)
    pieces: list[str] = []
    buffer = ""
    for sent in sentences:
        candidate = f"{buffer} {sent}".strip() if buffer else sent
        if len(candidate) > ceil and buffer:
            pieces.append(buffer)
            buffer = sent
        elif len(candidate) > ceil and not buffer:
            pieces.append(sent[:ceil])
            buffer = sent[ceil:]
        else:
            buffer = candidate
    if buffer:
        pieces.append(buffer)
    return pieces


def chunk_text(
    text: str,
    *,
    target: int = 500,
    floor: int = 100,
    ceil: int = 800,
) -> list[str]:
    """Particiona texto em chunks por parágrafo com tamanho-alvo.

    - Parágrafos curtos consecutivos são agrupados até atingir `floor`.
    - Parágrafos grandes (> `ceil`) são divididos em fronteiras de frase.
    - Sem overlap entre chunks (ADR-030).
    """
    if not text or not text.strip():
        return []
    raw_paragraphs = [_normalize(p) for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for para in raw_paragraphs:
        pieces.extend(_split_paragraph(para, ceil))

    chunks: list[str] = []
    buffer = ""
    for piece in pieces:
        if not buffer:
            buffer = piece
            continue
        if len(buffer) >= floor and len(buffer) + 2 + len(piece) > target:
            chunks.append(buffer)
            buffer = piece
        else:
            buffer = f"{buffer}\n\n{piece}"
    if buffer:
        chunks.append(buffer)
    return chunks
