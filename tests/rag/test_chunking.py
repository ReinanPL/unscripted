from app.rag.chunking import chunk_text


def test_empty_text_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   \n  \n ") == []


def test_short_text_returns_single_chunk():
    text = "Um parágrafo curto qualquer."
    chunks = chunk_text(text, target=500, floor=100, ceil=800)
    assert chunks == [text]


def test_two_short_paragraphs_get_merged():
    p1 = "Primeiro parágrafo curto, em torno de cinquenta caracteres."
    p2 = "Segundo parágrafo curto, parecido com o primeiro também."
    text = f"{p1}\n\n{p2}"
    chunks = chunk_text(text, target=500, floor=100, ceil=800)
    assert len(chunks) == 1
    assert p1 in chunks[0]
    assert p2 in chunks[0]


def test_paragraphs_split_when_above_target():
    medium = "x" * 480
    text = f"{medium}\n\n{medium}"
    chunks = chunk_text(text, target=500, floor=100, ceil=800)
    assert len(chunks) == 2
    for ch in chunks:
        assert len(ch) <= 800


def test_huge_paragraph_is_split_on_sentence_boundary():
    sentence = "Esta é uma frase de tamanho razoável que repete várias vezes. "
    huge = sentence * 50
    chunks = chunk_text(huge, target=500, floor=100, ceil=800)
    assert all(len(c) <= 800 for c in chunks)
    for c in chunks[:-1]:
        assert c.rstrip().endswith(".")


def test_chunking_is_deterministic():
    text = (
        "Parágrafo um.\n\nParágrafo dois com mais conteúdo.\n\n"
        "Parágrafo três, ainda mais longo, contendo várias palavras seguidas."
    )
    a = chunk_text(text)
    b = chunk_text(text)
    assert a == b


def test_whitespace_is_normalized_within_paragraph():
    text = "Frase   com    espaços\tmúltiplos\tinternos."
    chunks = chunk_text(text)
    assert chunks == ["Frase com espaços múltiplos internos."]
