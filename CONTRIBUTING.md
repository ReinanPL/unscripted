# Contributing

Thanks for considering a contribution. Before sending non-trivial changes, please open an issue so we can align on direction — the project prioritizes coherence over feature count.

The repo is bilingual in practice: the code, README, and contribution guides are in English; the game content and prompts are in Portuguese. Issues and PRs in either language are welcome.

## Prerequisites

- Docker + Docker Compose
- Python 3.11+ (for running the backend outside the container)
- Node 20+ (for the frontend outside the container)

## Setup

```bash
cp .env.example .env
# Fill in GEMINI_API_KEY and review other variables
docker compose up
```

This brings up the backend, frontend, and Postgres+pgvector. First boot ingests the SRD and the chapter content into pgvector.

## Local development tooling

```bash
# Backend deps + dev tools (ruff, mypy, pytest)
pip install -e "backend/[dev]"

# Pre-commit hooks (ruff + format + mypy + eslint + tsc)
pip install pre-commit
python -m pre_commit install

# Frontend deps
cd frontend && npm install && cd ..
```

Manual run of all hooks against the tree:

```bash
python -m pre_commit run --all-files
```

## Tests

```bash
pytest                     # default: 139 tests, ~6s, 100% coverage on the rules engine
pytest -m eval --no-cov    # opt-in: evals the agents against the real Gemini (costs API calls)
```

The default suite is free of API calls. Eval sets are skipped when `GEMINI_API_KEY` is missing — safe to run anywhere.

## Coding conventions

- **Python:** `ruff` (linter + formatter), `mypy` in pragmatic strict mode.
- **TypeScript:** ESLint + Prettier (configured under `frontend/`).
- Comments only where the *why* is non-obvious. No obvious docstrings; no "added for X" notes that age badly.
- One task = one commit. Commit prefixes: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`. Imperative mood.

## Architectural decisions

Substantial design choices are recorded as ADRs in [`docs/DECISOES.md`](docs/DECISOES.md). If your change is structural — a new dependency, a different way to wire the agents, a schema shift — add an ADR alongside the PR. Format follows the existing ones: context, options considered, decision, consequences.

## License

By contributing, you agree your contribution is licensed under Apache 2.0. Adventure content (`content/chapters/`) must be 100% original — no material derived from third-party published modules.
