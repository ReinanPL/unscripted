# Contributing

## Pré-requisitos

- Docker + Docker Compose
- Python 3.11+ (para rodar o backend fora do container)
- Node 20+ (para rodar o frontend fora do container)

## Setup local

```bash
cp .env.example .env
# Preencha GEMINI_API_KEY e revise as demais variáveis
docker compose up
```

## Setup das ferramentas de qualidade

```bash
# Python (backend) — instala ruff, mypy e demais deps de dev
pip install ruff mypy fastapi pydantic

# Instala os hooks de pre-commit no repositório local
pip install pre-commit
python -m pre_commit install

# TypeScript (frontend) — só necessário na Fase 6
cd frontend && npm install && cd ..
```

Verificação manual (sem fazer commit):

```bash
python -m pre_commit run --all-files
```

## Fluxo de trabalho

Siga o fluxo descrito em `.claude/skills/mestre-fluxo-de-trabalho/SKILL.md`:

1. Antes de implementar qualquer tarefa, apresente o plano
2. Uma tarefa = um commit (mensagem descritiva)
3. Todo commit passa pelo pre-commit hook (ruff + mypy + format check)
4. Decisões de arquitetura novas vão para `docs/DECISOES.md`

## Padrões de código

- **Python:** `ruff` (linter + formatter), `mypy` em modo estrito proporcional
- **TypeScript:** ESLint + Prettier (configuração no frontend)
- Sem comentários óbvios; docstrings só onde o *porquê* não é evidente pelo código

## Licença

Ao contribuir, você concorda que sua contribuição será licenciada sob Apache 2.0.
O conteúdo de aventura (content/chapters/) deve ser 100% original.
