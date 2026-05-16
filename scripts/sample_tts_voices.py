"""Gera amostras das vozes do gpt-4o-mini-tts para o dono escolher a default.

Lê o `read_aloud` da `starting_scene` do capítulo 1 ativo (texto real
em PT-BR no estilo do mestre) e gera um MP3 por voz da OpenAI, em
`scripts/voice-samples/`. O diretório está no `.gitignore` — as
amostras não vão para o repositório.

Uso:
    python scripts/sample_tts_voices.py

Requer `OPENAI_API_KEY` no `.env` ou no ambiente. As vozes geradas
são: alloy, sage, echo, coral, shimmer. O dono ouve as 5, escolhe,
e o valor vira default do `OPENAI_TTS_VOICE` no `.env.example` (ADR-049).
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

# Permite rodar do raiz do repo sem instalar o backend como pacote.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import yaml  # noqa: E402

from app.config import Settings  # noqa: E402
from app.providers.tts import OpenAiTtsProvider  # noqa: E402

VOICES = ["alloy", "sage", "echo", "coral", "shimmer"]
OUTPUT_DIR = REPO_ROOT / "scripts" / "voice-samples"
CHAPTER_FILE = REPO_ROOT / "content" / "chapters" / "chapter-01" / "chapter.yaml"


def load_starting_read_aloud() -> str:
    with CHAPTER_FILE.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    chapter = data["chapters"][0]
    starting_id = chapter["starting_scene"]
    scene = next(s for s in chapter["scenes"] if s["id"] == starting_id)
    text: str = scene["read_aloud"]
    return " ".join(text.split())


async def main() -> int:
    text = load_starting_read_aloud()
    print(f"Texto ({len(text)} chars):\n  {text}\n")

    settings = Settings(tts_provider="openai")
    if not settings.openai_api_key:
        print("ERRO: OPENAI_API_KEY ausente no .env. Preencha antes de rodar.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    provider = OpenAiTtsProvider(settings)

    for voice in VOICES:
        print(f"Gerando voz '{voice}'...", end=" ", flush=True)
        audio = await provider.synthesize(text, voice=voice)
        out = OUTPUT_DIR / f"{voice}.mp3"
        out.write_bytes(audio)
        print(f"{len(audio)} bytes -> {out.relative_to(REPO_ROOT)}")

    print(f"\nAmostras em {OUTPUT_DIR.relative_to(REPO_ROOT)}/. Ouça e escolha.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
