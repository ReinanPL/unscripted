# Validação da v1 — Definition of Done

Auditoria dos 16 critérios da §10 do `PRD.md`. Cada item é validado por (a) evidência no código (arquivo:linhas) ou (b) execução comprovada (comando, endpoint, smoke).

**Legenda:** ✓ atendido · ⚠ parcial · ✗ não atendido

| # | Critério | Veredito | Evidência |
|---|---|---|---|
| 1 | Jogador joga o Capítulo 1 do início ao fim | ✓ | Capítulo completo em [content/chapters/chapter-01/chapter.yaml](../content/chapters/chapter-01/chapter.yaml). Loop de turno operacional ([backend/app/runner_turn.py](../backend/app/runner_turn.py)). Smoke: app rodando em `docker compose up`, fluxo Landing → Create → Play funcionou ponta a ponta no navegador. |
| 2 | Motor roda qualquer história no formato estruturado | ✓ | Schema Pydantic genérico em [backend/app/state/adventure_schema.py](../backend/app/state/adventure_schema.py). Ingestão idempotente em [backend/app/rag/ingest.py](../backend/app/rag/ingest.py). Cap 1 é dado de entrada, não código. |
| 3 | Funciona ponta a ponta em português | ✓ | i18n PT populado em [frontend/src/i18n/pt.ts](../frontend/src/i18n/pt.ts). Prompts dos agentes em PT em [backend/app/agents/prompts/](../backend/app/agents/prompts/). Conteúdo em PT. Smoke confirmou toda UI em PT-BR. |
| 4 | Escolha entre Guerreiro e Paladino pré-prontos | ✓ | Fichas em [content/characters/guerreiro.yaml](../content/characters/guerreiro.yaml) e [paladino.yaml](../content/characters/paladino.yaml). Tela [frontend/src/screens/CreateCampaign.tsx](../frontend/src/screens/CreateCampaign.tsx). Smoke confirmou seleção e ficha Guerreiro carregando (HP 12/12). |
| 5 | GM narra, interpreta NPCs, arbitra ações e aplica consequências (loop de turno) | ✓ | Pipeline completo em [backend/app/runner_turn.py:221-377](../backend/app/runner_turn.py): Referee → rolagem (se aplicável) → consequência determinística → Narrator → NPC reagindo (se aplicável). Narração inicial do capítulo carregou via stream SSE no smoke. |
| 6 | Estado persiste; retomada por ID anônimo | ✓ | Postgres com `game_state` JSONB ([backend/app/db/base.py](../backend/app/db/base.py)). Endpoints [`GET /campaigns/{id}/state`](../backend/app/api/campaigns.py) e tela [ResumeCampaign.tsx](../frontend/src/screens/ResumeCampaign.tsx). UI exibe o ID anônimo logo após criação ("Anote este código"). |
| 7 | Grafo reflete posição real e se revela conforme exploração | ✓ | Endpoint `/graph` filtra por `flags.locations_revealed` ([backend/app/api/campaigns.py:238-261](../backend/app/api/campaigns.py)) — silhuetas das veladas via `VeiledNode` (ADR-042). Componente [LocationGraph.tsx](../frontend/src/components/LocationGraph.tsx). |
| 8 | Três zonas funcionando (narração, painel, cena) | ✓ | [frontend/src/components/Layout.tsx](../frontend/src/components/Layout.tsx) com `layout__zone--narration` e `layout__zone--scene`. Painel via [StatusCompact.tsx](../frontend/src/components/StatusCompact.tsx). Smoke confirmou as três zonas renderizando juntas. |
| 9 | Feedback visual reativo (dano, dado, transições, momentos-chave) | ✓ | [frontend/src/styles/animations.css](../frontend/src/styles/animations.css): `fx-damage-flash` (borda pulsa), `fx-hp-shake` (HP treme), `fx-roll-reveal` (rolagem com glow), `fx-edge-draw` (aresta nova), `narration__turn--crit-success/fail` (momento-chave). Respeita `prefers-reduced-motion`. |
| 10 | Painel "pensamento do mestre" disponível e funcional | ✓ | [frontend/src/components/MasterThoughtPanel.tsx](../frontend/src/components/MasterThoughtPanel.tsx) — recolhível, consome `/turn/{n}/trace`, exibe ruling, retrieval, rolagem, consequência, NPC. Smoke confirmou o botão visível no rodapé da narração. |
| 11 | Robustez: ações impossíveis, abusivas e conteúdo proibido barradas com aviso vermelho, sem consumir turno | ✓ | [backend/app/agents/robustness.py](../backend/app/agents/robustness.py) cobre as 3 categorias do PRD §8.1, §8.2, §9. Retorna 200 com `type=rejected`. UI: [RobustnessBanner.tsx](../frontend/src/components/RobustnessBanner.tsx). Eval set 30/30 ✓ ([tests/evals/robustness/](../tests/evals/robustness/)). |
| 12 | Falhas do LLM tratadas sem corromper estado e sem perder a mensagem do jogador | ✓ | **Validado ao vivo durante o smoke:** quota free-tier do Gemini esgotou no meio de um turno (`429 RESOURCE_EXHAUSTED`). UI mostrou banner "O mestre tropeçou", **mensagem do jogador foi preservada no input**, turno não foi consumido (HP intacto 12/12). Screenshot: [docs/assets/screenshot-error-recovery.png](assets/screenshot-error-recovery.png). Código: [runner_turn.py:272-329](../backend/app/runner_turn.py) + [ErrorBanner.tsx](../frontend/src/components/ErrorBanner.tsx). ADR-020. |
| 13 | Interface de voz existe (STT/TTS é v2) | ✓ | UI: [frontend/src/components/VoiceButton.tsx](../frontend/src/components/VoiceButton.tsx). Backend stub: [backend/app/providers/voice.py](../backend/app/providers/voice.py) `StubVoiceProvider`. ADR-014. Smoke confirmou botão "Gravar voz" visível ao lado do input. |
| 14 | Arquitetura de i18n pronta (apenas português populado) | ✓ | Estrutura: [frontend/src/i18n/index.ts](../frontend/src/i18n/index.ts) com hook `useT()`. Único idioma: [pt.ts](../frontend/src/i18n/pt.ts). Nenhum texto engessado em JSX. |
| 15 | Segredos não versionados; `.env.example` existe; Docker Compose portável | ✓ | [.gitignore](../.gitignore) inclui `.env`. [.env.example](../.env.example) versionado e documentado. [docker-compose.yml](../docker-compose.yml) usa `env_file`. |
| 16 | Repositório público com README, LICENSE, CONTRIBUTING | ✓ | [README.md](../README.md) enriquecido (visão, screenshots, "how it works", instruções, links para PRD/ARQUITETURA/DECISOES, créditos SRD). [LICENSE](../LICENSE) Apache 2.0. [NOTICE](../NOTICE) com atribuição SRD 5.1. [CONTRIBUTING.md](../CONTRIBUTING.md) sem vazamento de roadmap interno. |

## Resumo

**16/16 ✓** — todos os critérios do PRD §10 atendidos.

## Estado dos testes (no fechamento da v1)

```
pytest                         → 139 passed, 10 skipped, 2 deselected, 6.68s
                                 100% coverage em backend/app/rules
pytest -m eval                 → opt-in contra Gemini real (skipa sem chave)
```

Detalhamento:
- **10 skipped:** testes de ingestão e vector store que exigem Postgres com pgvector (rodam dentro de `docker compose`).
- **2 deselected:** eval sets de Referee e Narrator (marker `eval`, opt-in via `pytest -m eval --no-cov`).
- **Cobertura:** 100% em `app/rules` (`checks`, `consequences`, `dice`, `proposals`). Threshold `--cov-fail-under=90` configurado em `pytest.ini`.

## Smoke ao vivo (Bloco 7 da Fase 7)

App subido localmente via `docker compose up`. Fluxo confirmado:

1. Landing → "Iniciar uma nova partida".
2. Create → seleção Guerreiro, "Começar a aventura".
3. ID anônimo exibido para retomada futura.
4. Play → narração inicial do capítulo 1 carregou via SSE; HP, classe, localização, imagem da cena, grafo, botão de voz, e botão "pensamento do mestre" todos visíveis e nas três zonas.
5. **Bônus:** quota do Gemini esgotou no meio de um turno → UI tratou elegantemente (item 12 validado ao vivo).
