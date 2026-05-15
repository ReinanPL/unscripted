# Unscripted

Single-player tabletop RPG with an AI Game Master.

The AI narrates, arbitrates, and reacts to anything the player tries — in natural language. Rules are enforced deterministically; the LLM handles interpretation, narration, and NPC acting.

> **Status:** v1 in development. See [`docs/PLANO_IMPLEMENTACAO.md`](docs/PLANO_IMPLEMENTACAO.md) for the build plan.

## Architecture

```
unscripted/
├── backend/          # Python · FastAPI · Google ADK · Postgres+pgvector
├── frontend/         # React · Vite · TypeScript
├── content/
│   ├── srd/          # SRD 5.1 rules corpus (CC-BY 4.0)
│   └── chapters/     # Original adventure chapters
├── docs/             # PRD, architecture, decision log, implementation plan
└── tests/
    ├── rules/        # Deterministic rules engine tests
    └── evals/        # Agent eval set
```

Full architecture in [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

## Running locally

```bash
cp .env.example .env
# Fill in GEMINI_API_KEY and review other variables
docker compose up
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:5173`

## Licensing

- **Code** — Apache 2.0 (see [`LICENSE`](LICENSE))
- **Rules layer** — derived from the SRD 5.1 (CC-BY 4.0) — see [`NOTICE`](NOTICE)
- **Adventure content** — original, written for this project

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).
