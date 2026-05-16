"""Testes do `GroqWhisperProvider`.

Os testes puros (sem rede) cobrem:
- Mapping mime → extensão de filename (Whisper exige extensão correta).
- Áudio vazio é tratado localmente (sem hit na API).

O eval opt-in (`@pytest.mark.eval`) só roda quando `GROQ_API_KEY` está
no env. Gera um WAV mínimo (silêncio 1s, 16kHz mono) e confere que a
chamada à API completa sem exception — não validamos o conteúdo do
texto reconhecido, só o caminho de integração (auth, formato, decode).
"""

from __future__ import annotations

import io
import os
import wave

import pytest

from app.config import Settings
from app.providers.stt import GroqWhisperProvider, _filename_for


@pytest.mark.parametrize(
    ("mime", "expected"),
    [
        ("audio/webm", "audio.webm"),
        ("audio/webm; codecs=opus", "audio.webm"),
        ("audio/ogg", "audio.ogg"),
        ("audio/mp4", "audio.mp4"),
        ("audio/m4a", "audio.m4a"),
        ("audio/mpeg", "audio.mp3"),
        ("audio/mp3", "audio.mp3"),
        ("audio/wav", "audio.wav"),
        ("audio/x-wav", "audio.wav"),
        ("audio/flac", "audio.flac"),
        ("", "audio.webm"),
        ("audio/desconhecido", "audio.webm"),
    ],
)
def test_filename_for_mime(mime: str, expected: str) -> None:
    assert _filename_for(mime) == expected


@pytest.mark.asyncio
async def test_transcribe_empty_audio_short_circuits() -> None:
    """Audio vazio não vale uma chamada à API."""
    settings = Settings(stt_provider="groq", groq_api_key="test-groq")
    provider = GroqWhisperProvider(settings)
    text = await provider.transcribe(b"", mime_type="audio/webm")
    assert text == ""


def _silent_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    """Gera um WAV PCM mono 16-bit em silêncio. Whisper aceita; retorna
    texto vazio ou onomatopéia — não importa, o teste só confere o pipe.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


@pytest.mark.eval
@pytest.mark.asyncio
async def test_groq_whisper_end_to_end() -> None:
    """Eval opt-in: roda contra Groq Whisper de verdade.

    Não asserta nada sobre o conteúdo — apenas que a chamada não levanta.
    """
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY ausente; eval contra Groq Whisper ignorado.")
    settings = Settings(stt_provider="groq", groq_api_key=os.environ["GROQ_API_KEY"])
    provider = GroqWhisperProvider(settings)
    text = await provider.transcribe(_silent_wav(), mime_type="audio/wav")
    assert isinstance(text, str)
