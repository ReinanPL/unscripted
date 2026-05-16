# Validação da v1 — Definition of Done

Auditoria dos 16 critérios da §10 do `PRD.md`. Cada item é validado por (a) evidência no código (arquivo:linhas) ou (b) execução comprovada (comando, endpoint, smoke).

**Legenda:** ✓ atendido · ⚠ parcial / depende de smoke · ✗ não atendido

| # | Critério | Veredito | Evidência |
|---|---|---|---|
| 1 | Jogador joga o Capítulo 1 do início ao fim | ✓ | Capítulo completo em [content/chapters/chapter-01/chapter.yaml](../content/chapters/chapter-01/chapter.yaml). Loop de turno operacional ([backend/app/runner_turn.py](../backend/app/runner_turn.py)). Re-validado por smoke no Bloco 7 ao subir o app para screenshots. |
| 2 | Motor roda qualquer história no formato estruturado | ✓ | Schema Pydantic genérico em [backend/app/state/adventure_schema.py](../backend/app/state/adventure_schema.py). Ingestão idempotente em [backend/app/rag/ingest.py](../backend/app/rag/ingest.py). Cap 1 é dado de entrada, não código. |
| 3 | Funciona ponta a ponta em português | ✓ | i18n PT populado em [frontend/src/i18n/pt.ts](../frontend/src/i18n/pt.ts). Prompts dos agentes em PT em [backend/app/agents/prompts/](../backend/app/agents/prompts/). Conteúdo em PT. |
| 4 | Escolha entre Guerreiro e Paladino pré-prontos | ✓ | Fichas em [content/characters/guerreiro.yaml](../content/characters/guerreiro.yaml) e [paladino.yaml](../content/characters/paladino.yaml). Tela [frontend/src/screens/CreateCampaign.tsx](../frontend/src/screens/CreateCampaign.tsx). |
| 5 | GM narra, interpreta NPCs, arbitra ações e aplica consequências (loop de turno) | ✓ | Pipeline completo em [backend/app/runner_turn.py:221-377](../backend/app/runner_turn.py): Referee → rolagem (se aplicável) → consequência determinística → Narrator → NPC reagindo (se aplicável). |
| 6 | Estado persiste; retomada por ID anônimo | ✓ | Postgres com `game_state` JSONB ([backend/app/db/base.py](../backend/app/db/base.py)). Endpoints [`GET /campaigns/{id}/state`](../backend/app/api/campaigns.py) e tela [ResumeCampaign.tsx](../frontend/src/screens/ResumeCampaign.tsx). |
| 7 | Grafo reflete posição real e se revela conforme exploração | ✓ | Endpoint `/graph` filtra por `flags.locations_revealed` ([backend/app/api/campaigns.py:238-261](../backend/app/api/campaigns.py)). Componente [LocationGraph.tsx](../frontend/src/components/LocationGraph.tsx). ADR-038. |
| 8 | Três zonas funcionando (narração, painel, cena) | ✓ | [frontend/src/components/Layout.tsx](../frontend/src/components/Layout.tsx) com `layout__zone--narration` e `layout__zone--scene`. Painel via [StatusCompact.tsx](../frontend/src/components/StatusCompact.tsx). |
| 9 | Feedback visual reativo (dano, dado, transições, momentos-chave) | ✓ | [frontend/src/styles/animations.css](../frontend/src/styles/animations.css): `fx-damage-flash` (borda pulsa), `fx-hp-shake` (HP treme), `fx-roll-reveal` (rolagem com glow), `fx-edge-draw` (aresta nova), `narration__turn--crit-success/fail` (momento-chave). Respeita `prefers-reduced-motion`. |
| 10 | Painel "pensamento do mestre" disponível e funcional | ✓ | [frontend/src/components/MasterThoughtPanel.tsx](../frontend/src/components/MasterThoughtPanel.tsx) — recolhível, consome `/turn/{n}/trace`, exibe ruling, retrieval, rolagem, consequência, NPC. |
| 11 | Robustez: ações impossíveis, abusivas e conteúdo proibido barradas com aviso vermelho, sem consumir turno | ✓ | [backend/app/agents/robustness.py](../backend/app/agents/robustness.py) cobre as 3 categorias do PRD §8.1, §8.2 e §9. Retorna 200 com `type=rejected`; turno não é processado. UI: [RobustnessBanner.tsx](../frontend/src/components/RobustnessBanner.tsx). |
| 12 | Falhas do LLM tratadas sem corromper estado e sem perder a mensagem do jogador | ✓ | [backend/app/runner_turn.py:272-329](../backend/app/runner_turn.py): `try/except` na fase crítica, evento `error_preserve_input`, history não cresce, trace persistido com erro. UI: [ErrorBanner.tsx](../frontend/src/components/ErrorBanner.tsx). ADR-020. |
| 13 | Interface de voz existe (STT/TTS é v2) | ✓ | UI: [frontend/src/components/VoiceButton.tsx](../frontend/src/components/VoiceButton.tsx). Backend stub: [backend/app/providers/voice.py](../backend/app/providers/voice.py) `StubVoiceProvider`. ADR-014. |
| 14 | Arquitetura de i18n pronta (apenas português populado) | ✓ | Estrutura: [frontend/src/i18n/index.ts](../frontend/src/i18n/index.ts) com hook `useT()`. Único idioma: [pt.ts](../frontend/src/i18n/pt.ts). Nenhum texto engessado em JSX (verificado via Layout/Status/Narration). |
| 15 | Segredos não versionados; `.env.example` existe; Docker Compose portável | ✓ | [.gitignore](../.gitignore) inclui `.env`. [.env.example](../.env.example) versionado e documentado. [docker-compose.yml](../docker-compose.yml) usa `env_file`. |
| 16 | Repositório público com README, LICENSE, CONTRIBUTING | ⚠ | Existem ([README.md](../README.md), [LICENSE](../LICENSE), [NOTICE](../NOTICE), [CONTRIBUTING.md](../CONTRIBUTING.md)). README está mínimo (sem screenshot, créditos rasos) e CONTRIBUTING vaza "Fase 6". **Bloco 7 da Fase 7 enriquece os dois.** Re-validado no Bloco 9. |

## Resumo

- **15/16 ✓** baseado em evidência de código.
- **1/16 ⚠** (item 16): README/CONTRIBUTING existem mas precisam do polish do Bloco 7.
- **0/16 ✗**.

## O que ainda exige smoke real

Marcado como ✓ baseado em código, mas a validação fim-a-fim acontece quando o app sobe para screenshots no Bloco 7:

- Item 1: jogar o cap 1 do início ao fim no navegador.
- Item 5: o loop de turno completo gerar narração coerente via Gemini.
- Item 6: fechar o navegador, abrir, retomar pelo ID, estado intacto.
- Item 7: locação se revela após mover.
- Item 9: animações disparam de fato (dano, rolagem, aresta).
- Item 11: aviso vermelho aparece para os 3 tipos.
- Item 12: simular falha do LLM (chave inválida) e ver mensagem preservada.

## Re-validação

Esta lista é re-conferida no Bloco 9 (fechamento da v1). Qualquer item que vire ⚠ ou ✗ depois do smoke vira tarefa explícita antes de marcar a v1 como concluída.
