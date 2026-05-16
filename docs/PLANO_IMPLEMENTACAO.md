# PLANO DE IMPLEMENTAÇÃO — v1

**Projeto:** Unscripted
**Documentos relacionados:** `PRD.md` (o quê e por quê), `ARQUITETURA.md` (como), `DECISOES.md` (histórico das decisões).

> Este documento é o **mapa de execução** da v1. Detalha cada fase da seção "Ordem de build" do `ARQUITETURA.md` (§20) em tarefas concretas, com entregas e critérios objetivos de "fase concluída". É um documento vivo — ajustes feitos durante a implementação voltam para cá, e decisões novas viram ADRs no `DECISOES.md`.

---

## Princípios que regem este plano

1. **Fatias verticais que rodam.** Cada fase termina com algo demonstrável de ponta a ponta — não com uma camada horizontal pela metade. Validação de fim de fase é "consigo rodar e ver funcionar", não "compilou".
2. **Uma fase de cada vez.** Não se inicia a próxima sem a anterior **concluída e validada**. Adiar não é fraqueza — é o que torna a v1 um todo coerente.
3. **Cada tarefa = um commit.** Mensagens no padrão (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`). Lint e checagem de tipos via hook de pre-commit.
4. **O que NÃO entra na fase é tão importante quanto o que entra.** Cada fase tem uma seção "Fora de escopo desta fase" para barrar drift.
5. **Decisão nova → ADR.** Surgiu algo não previsto que afeta arquitetura? Registra-se em `DECISOES.md` antes de avançar.
6. **Testes proporcionais.** Testes unitários onde código puro existe (motor de regras, validação de robustez, schemas, parsers). Smoke tests manuais nas fases de integração para validar fatias verticais. Eval set sistemático dos agentes na Fase 7. Não se espalha "testar tudo" sem necessidade.

---

## Visão geral

| Fase | Nome | Entrega central | Validação |
|---|---|---|---|
| 0 | Scaffold | Estrutura, Docker Compose, pre-commit, Postgres+pgvector subindo | `docker compose up` sobe sem erro; pre-commit roda |
| 1 | Esqueleto | Loop turno mínimo: NarratorAgent + sessão em memória | curl → narração via SSE |
| 2 | Persistência | Estado no Postgres, salvar/retomar por ID | Derruba backend, sobe, retoma partida |
| 3 | Motor de regras | Módulo determinístico + FunctionTool + fichas balanceadas | Testes do motor passam; FunctionTools chamáveis isoladamente |
| 4 | RAG | Schema de aventura, embedding local, pgvector, ingestão SRD/capítulo | NarratorAgent consulta lore demonstravelmente |
| 5 | Multi-agente + robustez | Referee/Narrator/NPC/GameMaster + heurística de robustez + erro elegante + capítulo 1 completo | Encontro estilo emboscada (PRD §5) extraído do capítulo 1 roda do início ao fim |
| 6 | Frontend | Três zonas, grafo, identidade visual, feedback reativo, imagens | Jogador joga o capítulo 1 inteiro pelo navegador |
| 7 | Validação e polish | Eval set, README, LICENSE, critérios v1 atendidos | Todos os itens do PRD §10 verdadeiros |

---

## Fase 0 — Scaffold

**Objetivo.** Fundação para começar. Nenhum código de jogo ainda — só a infraestrutura que toda fase seguinte vai usar.

**Tarefas.**

| # | Tarefa | Entrega |
|---|---|---|
| 0.1 | Estrutura de pastas conforme `ARQUITETURA.md` §18 | `backend/app/{api,agents,rules,rag,providers,state,i18n}/`, `frontend/`, `content/{srd,chapters}/`, `tests/{rules,evals}/` criadas com `.gitkeep` onde necessário |
| 0.2 | Arquivos de raiz | `.gitignore` (inclui `.env`), `.env.example` com todas as variáveis previstas, `LICENSE` (Apache 2.0), `NOTICE` (atribuição SRD 5.1 stub), `README.md` mínimo, `CONTRIBUTING.md` stub |
| 0.3 | `docker-compose.yml` | Dois serviços: `backend` e `postgres` (com `pgvector/pgvector:pg16` ou similar). Healthchecks. Volumes nomeados. Sem build do backend ainda |
| 0.4 | `backend/Dockerfile` + `pyproject.toml` | Dependências mínimas: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`. Endpoint `GET /health` que retorna `{"ok": true}`. Dependências de ADK, driver de DB e demais entram na fase em que forem usadas (YAGNI) |
| 0.5 | Linter e type checker | `ruff` configurado, `mypy` configurado (modo estrito proporcional). `make lint` ou script equivalente |
| 0.6 | Hook de pre-commit | `pre-commit` instala e roda ruff + mypy + format check antes de cada commit. Falha = commit não sobe |
| 0.7 | Postgres com pgvector | Migration inicial cria extensão `vector`; teste manual de `CREATE TABLE ... vector(384)` funciona |

**Critério de fase concluída.**
- [ ] `docker compose up -d` sobe ambos os containers sem erro.
- [ ] `curl http://localhost:8000/health` retorna `200 OK`.
- [ ] `psql` no container do Postgres mostra a extensão `vector` ativa.
- [ ] Um commit de teste dispara o pre-commit e ele bloqueia código com erro de lint/tipo.
- [ ] Primeiro commit real da Fase 0 está no repositório.

**Fora de escopo desta fase.**
Nenhum código de agente, motor, RAG, ou frontend. Aqui é só fundação.

---

## Fase 1 — Esqueleto: loop de turno mínimo

**Objetivo.** Provar o **loop de ponta a ponta** do backend: jogador manda texto → agente narra de volta. Um único agente, sessão em memória, zero regras. É o "Hello World" do Unscripted.

**Tarefas.**

| # | Tarefa | Entrega |
|---|---|---|
| 1.1 | Camada de providers — LLM | Adiciona `google-adk` e cliente Gemini ao `pyproject.toml`. Interface `LlmProvider` em `providers/llm.py`. Implementação `GeminiAiStudioProvider` selecionada por env var. Erro elegante e claro se a chave faltar |
| 1.2 | `NarratorAgent` mínimo | `LlmAgent` do ADK com prompt mínimo de Game Master narrador. Sem RAG, sem tools |
| 1.3 | Wiring do Runner ADK | `runner.py` com `Runner` + `InMemorySessionService`. O agente roda |
| 1.4 | Schemas Pydantic da API | `CampaignCreateResponse`, `ActionRequest`, `ActionEvent` |
| 1.5 | `POST /campaigns` | Cria sessão em memória, retorna ID anônimo (UUID). Personagem ainda não importa — coloca Guerreiro fixo |
| 1.6 | `POST /campaigns/{id}/action` | Recebe `{"text": "..."}`, envia ao NarratorAgent, transmite a narração via **SSE** |
| 1.7 | Validação básica de entrada | Tamanho mínimo/máximo, tipo. Validação profunda de robustez é Fase 5 |
| 1.8 | Smoke test via curl | Script `scripts/smoke_phase1.sh` que cria campanha e manda uma ação, mostra a narração no terminal |

**Critério de fase concluída.**
- [ ] `curl -X POST /campaigns` retorna `{"campaign_id": "..."}`.
- [ ] `curl -N -X POST /campaigns/{id}/action` recebe a narração via SSE, palavra por palavra ou chunk por chunk.
- [ ] A narração é coerente e em português (o Gemini está realmente sendo chamado).
- [ ] Se a env var da chave do LLM estiver ausente, o backend dá erro claro e não crasha.
- [ ] Nenhuma chamada ao Gemini fora de `providers/` (busca de código confirma).
- [ ] Lint e tipos passam.

**Fora de escopo desta fase.**
Persistência (Fase 2), motor de regras (Fase 3), RAG (Fase 4), Referee/NPCActor (Fase 5), validação de robustez profunda (Fase 5), frontend (Fase 6), tratamento de erro do LLM (Fase 5).

---

## Fase 2 — Persistência e estado

**Objetivo.** O estado da partida vira **persistente**. Fechar o backend e abrir de novo retoma exatamente a partida.

**Tarefas.**

| # | Tarefa | Entrega |
|---|---|---|
| 2.1 | Modelo de estado | Pydantic models em `state/`: `Session` (incluindo **idioma da partida** — `ARQUITETURA.md` §8/§19), `Character`, `Inventory`, `Location`, `Flags`, `HistoryEntry`, `HiddenState`. Driver de Postgres (`psycopg` ou `asyncpg`) escolhido aqui — registrar a escolha como nota neste plano se for relevante |
| 2.2 | Migrations | Alembic configurado; migration inicial cria as tabelas correspondentes |
| 2.3 | Sessão ADK persistida | Trocar `InMemorySessionService` por `DatabaseSessionService` apontando para o mesmo Postgres |
| 2.4 | Personagens pré-prontos (stub) | `content/characters/guerreiro.yaml` e `paladino.yaml` com **dados-stub mínimos** (atributos e HP suficientes para a estrutura do estado funcionar). **Balanceamento final acontece na Fase 3**, quando o motor existe e dá para balancear contra rolagens reais |
| 2.5 | `POST /campaigns` adaptado | Aceita `{"character": "guerreiro" \| "paladino"}`. Cria registro no DB. Carrega ficha do YAML |
| 2.6 | `POST /campaigns/{id}/action` adaptado | Busca sessão no DB, processa, persiste mudanças (ainda sem mutação de estado real — vem na Fase 3) |
| 2.7 | `GET /campaigns/{id}/state` | Retorna o estado **conhecido** pelo jogador. **Filtra estado oculto** — confere com `mestre-backend` checklist item 6 |
| 2.8 | `GET /campaigns/{id}/log` | Retorna histórico narrativo |
| 2.9 | Smoke test de persistência | Script: cria campanha, faz turno, `docker compose restart backend`, retoma — estado intacto |

**Critério de fase concluída.**
- [ ] `docker compose restart backend` não perde nenhuma partida em andamento.
- [ ] `GET /campaigns/{id}/state` retorna ficha + inventário + localização + objetivos; **não** retorna estado oculto (teste explícito).
- [ ] Posso escolher Guerreiro **ou** Paladino na criação e a ficha correta aparece no state.
- [ ] Smoke test da Fase 1 continua passando.
- [ ] Lint e tipos passam.

**Fora de escopo desta fase.**
Motor de regras (Fase 3), RAG (Fase 4), multi-agente (Fase 5), tratamento de erro do LLM (Fase 5), frontend (Fase 6).

---

## Fase 3 — Motor de regras determinístico

**Objetivo.** A pilha determinística existe, é **testada exaustivamente**, e está **disponível como `FunctionTool` registrado** — pronta para o `RefereeAgent` consumir quando ele nascer na Fase 5. A validação é feita chamando os tools diretamente nos testes, sem envolver agente. Nesta fase, o motor é uma biblioteca acabada; o consumo no fluxo real do loop de turno é da Fase 5.

**Tarefas.**

| # | Tarefa | Entrega |
|---|---|---|
| 3.1 | Parsing de notação de dados | `rules/dice.py` — parser de `2d6+3`, `1d20`, vantagem (`adv`), desvantagem (`dis`). Função pura |
| 3.2 | Rolagem | `roll(notation, *, seed=None)` retorna `RollResult` (Pydantic): dado(s) brutos, modificador, total. Seed para testes |
| 3.3 | Comparação rolagem vs dificuldade | `check(roll, difficulty)` retorna `CheckResult` (success/fail, margem) |
| 3.4 | Aplicação de dano | `apply_damage(character, amount)` retorna novo `Character` com HP atualizado. **Pura** — não muta input |
| 3.5 | Aplicação de consequências | `apply_consequence(state, proposal)` — recebe proposta tipada do LLM e devolve novo estado, **validando antes** (não aceita HP negativo absurdo, item inexistente, etc.) |
| 3.6 | Testes do motor | `tests/rules/` — cobertura completa: rolagens, vantagem/desvantagem, comparações, dano, consequências, propostas inválidas barradas |
| 3.7 | Expor como FunctionTool | `agents/tools.py` — wrappers ADK `FunctionTool` em torno das funções do motor. **Registrados** (prontos para uso); o agente que vai chamá-los no fluxo real só nasce na Fase 5 (`RefereeAgent`) |
| 3.8 | Validação via test suite | `tests/rules/test_function_tools.py` — testes de integração que **chamam os FunctionTools diretamente** (sem agente) e verificam que cada um retorna o resultado esperado. É como o Referee vai consumi-los na Fase 5 |
| 3.9 | Fichas finais balanceadas | Revisar `content/characters/guerreiro.yaml` e `paladino.yaml`: atributos, HP, perícias, equipamento inicial **balanceados** contra o motor real (rolagens, dificuldades típicas) e contra o encontro-padrão do capítulo 1 (Fase 5). Substitui os dados-stub de 2.4 |

**Critério de fase concluída.**
- [ ] `pytest tests/rules/` verde, com cobertura significativa (alvo: ≥90% no módulo de regras).
- [ ] Propostas inválidas do LLM são **rejeitadas** pelo motor (teste explícito).
- [ ] Os FunctionTools são chamáveis e testados isoladamente (sem agente envolvido).
- [ ] Fichas de Guerreiro e Paladino estão balanceadas — uma rolagem típica de dificuldade média tem chance razoável de sucesso para a perícia adequada de cada classe.
- [ ] Nenhuma mutação de estado fora das funções do motor (busca de código confirma).
- [ ] Lint e tipos passam.

**Fora de escopo desta fase.**
Agente consumindo os tools no loop (Fase 5), RAG (Fase 4), Referee separado (Fase 5), validação de robustez (Fase 5), aplicação automática completa de consequências do loop (Fase 5), frontend.

---

## Fase 4 — RAG

**Objetivo.** O jogo consulta **regras** e **lore** por similaridade vetorial, com embedding local rodando no container. O NarratorAgent passa a ser fundamentado em lore. (O Referee usará as regras na Fase 5.)

**Tarefas.**

| # | Tarefa | Entrega |
|---|---|---|
| 4.0 | Schema Pydantic do formato de aventura | Modelos Pydantic em `state/adventure_schema.py` (ou similar): `Adventure`, `Chapter`, `Scene`, `NPC`, `Encounter`, `ImageBriefing`, `Connection`, `HiddenState`, etc., conforme `ARQUITETURA.md` §10. **Registra ADR-025.** Sem isso, "ler o arquivo do capítulo" vira interpretação ad hoc |
| 4.1 | Camada de providers — Embedding | Interface `EmbeddingProvider` em `providers/embedding.py`. Implementação local com `sentence-transformers` (modelo a escolher; dimensão configurada por env) |
| 4.2 | Cliente pgvector | `rag/vector_store.py` — funções `upsert(chunks, corpus, metadata)` e `search(query, corpus, k)` usando pgvector |
| 4.3 | Pipeline de ingestão | `rag/ingest.py` — lê arquivos de `content/`, faz chunking, embeda, insere com metadados (`corpus`, `source`, `chapter_id`, etc.). **Idempotente** |
| 4.4 | Conteúdo: SRD 5.1 | Baixar o subset relevante do SRD 5.1 para `content/srd/` (texto puro). Atribuição no `NOTICE` |
| 4.5 | Conteúdo: capítulo 1 stub | `content/chapters/chapter-01/` no formato estruturado de aventura — **minimamente viável** (uma cena, um NPC com estado oculto, conexões para o grafo, um encontro, gancho), **validado contra o schema Pydantic de 4.0**. Capítulo completo é finalizado na Fase 5. Ver skill `mestre-criacao-de-historia` |
| 4.6 | Ingestão no startup | Hook de startup do FastAPI roda a ingestão (idempotente). Capítulo alimenta corpus de lore; SRD alimenta corpus de regras |
| 4.7 | Wirar lore no NarratorAgent | Antes de gerar narração, o NarratorAgent recebe os top-k chunks de lore relevantes à ação |
| 4.8 | Smoke test de RAG | Ação que referencia um detalhe específico do lore do capítulo 1 → busca recupera o trecho → narração incorpora |

**Critério de fase concluída.**
- [ ] Schema Pydantic do formato de aventura existe, é importável, e está documentado por código (`ADR-025` registrado).
- [ ] Um arquivo de capítulo malformado é **rejeitado** pela validação antes de entrar no banco.
- [ ] `python -m app.rag.ingest` (ou equivalente) popula os dois corpora sem erro.
- [ ] `search("...")` retorna trechos relevantes na ordem certa (teste manual com 3 queries).
- [ ] O NarratorAgent **demonstravelmente** usa o lore: uma pergunta sobre detalhe do capítulo 1 é respondida com fidelidade ao texto do conteúdo, não inventada.
- [ ] Nenhuma chamada de embedding fora de `providers/`.
- [ ] Re-rodar a ingestão não duplica registros.
- [ ] Lint e tipos passam.

**Fora de escopo desta fase.**
Referee separado consultando regras (Fase 5), multi-agente (Fase 5), eval sistemático de retrieval (Fase 7 se necessário).

---

## Fase 5 — Multi-agente, robustez e o loop completo

**Objetivo.** Separar os agentes conforme `ARQUITETURA.md` §4.2-4.3. Implementar **toda** a validação de robustez (PRD §8 e §9) e o tratamento elegante de erro (PRD §7.7). Finalizar o capítulo 1 incluindo um encontro **escrito no padrão da emboscada do PRD §5** — esse encontro é, ao mesmo tempo, conteúdo real do jogo e o **cenário-canônico** que valida o loop de turno completo de ponta a ponta.

**Tarefas.**

| # | Tarefa | Entrega |
|---|---|---|
| 5.1 | `RefereeAgent` | LlmAgent que consulta o corpus de **regras** via RAG e emite um **ruling estruturado** (Pydantic): `precisa_rolagem`, `perícia`, `dificuldade`, `consequências_sucesso`, `consequências_falha` |
| 5.2 | `NPCActorAgent` | LlmAgent genérico — persona do NPC ativo é **injetada do estado** na instrução. Um agente atende a qualquer NPC |
| 5.3 | `NarratorAgent` refatorado | Recebe ruling + resultado de dados + estado, narra. RAG de lore já está integrado (Fase 4) |
| 5.4 | `GameMasterAgent` orquestrador | Começa **simples**: cadeia sequencial (ver `mestre-backend`). Só evolui para `BaseAgent` customizado se a lógica condicional realmente exigir. Documentar a decisão aqui ou via ADR |
| 5.5 | Loop de turno completo | `runner.py` orquestra: validação determinística → GameMaster → Referee (com RAG de regras) → resolução de dados (se ruling pede) → aplicação determinística de consequências → Narrator (com RAG de lore) → NPCActor (se há NPCs reagindo) |
| 5.6 | Validação de robustez determinística | Módulo `agents/robustness.py` — barra ações impossíveis (declaração de resultado), abusivas (injeção de prompt, fora de personagem), conteúdo proibido (PRD §9). Em qualquer um: turno **não consumido**, resposta com aviso vermelho estruturado. **Estratégia: heurística determinística simples (listas de padrões + regex), sem classificador. Registra ADR-026 documentando a escolha e suas limitações conhecidas (falsos positivos/negativos aceitáveis na v1)** |
| 5.7 | Validação da saída do LLM | Todas as propostas do RefereeAgent/NarratorAgent passam por Pydantic + regras do motor antes de tocar o estado |
| 5.8 | Observabilidade | Registro estruturado de cada turno: ruling, retrieval, rolagens, propostas, narração, NPC. Persistido no DB |
| 5.9 | `GET /campaigns/{id}/turn/{n}/trace` | Endpoint que retorna o "pensamento do mestre" do turno — alimenta o painel da Fase 6 |
| 5.10 | Tratamento de falha do LLM | Captura timeout/erro do provider. Resposta: aviso, **turno não consumido, estado intacto, mensagem do jogador devolvida**. Teste explícito |
| 5.11 | Capítulo 1 finalizado | Substitui o stub de 4.5 pelo capítulo 1 **completo** no formato de aventura: todas as cenas, NPCs com estado oculto, conexões para o grafo, encontros, ramificações, itens, condições de progresso, gancho para o cap 2. **Inclui obrigatoriamente um encontro no padrão da emboscada do PRD §5: um NPC com estado oculto relevante (ex.: "veterano, percepção alta"), uma ação que exige rolagem, e consequências distintas de sucesso e falha.** Esse encontro é a base do smoke test em 5.12. Briefings de imagem ficam para 6.19. Re-ingerido no RAG. Ver skill `mestre-criacao-de-historia` |
| 5.12 | Smoke test do cenário-canônico | Reproduz o **encontro estilo emboscada do capítulo 1** (criado em 5.11, no padrão do PRD §5): ação → ruling estruturado → rolagem → consequência → narração → reação do NPC. Loga tudo. O cenário-canônico e o conteúdo real são a mesma coisa |
| 5.13 | Smoke tests de robustez | Casos: declaração de resultado ("eu mato o NPC instantaneamente"), tentativa de injeção, pedido de conteúdo proibido. Cada um → aviso vermelho, turno não consumido |

**Critério de fase concluída.**
- [ ] Capítulo 1 completo está em `content/chapters/chapter-01/`, validado pelo schema, re-ingerido no RAG.
- [ ] O encontro-padrão do capítulo 1 (estilo emboscada, PRD §5) roda completo via curl, sem intervenção manual, com todos os artefatos no trace.
- [ ] Os três casos de robustez retornam aviso estruturado e **não** consumem o turno.
- [ ] `ADR-026` registrado documentando a estratégia de heurística e suas limitações.
- [ ] Falha simulada do LLM (mockando o provider) **não** corrompe estado e devolve a mensagem do jogador.
- [ ] `GET .../turn/{n}/trace` retorna ruling, retrieval, rolagem, proposta, narração — pronto para consumo do frontend.
- [ ] Nenhuma saída de LLM muta estado direto (busca de código confirma).
- [ ] Lint e tipos passam.

**Fora de escopo desta fase.**
Frontend (Fase 6), eval sistemático (Fase 7), briefings de imagem (Fase 6.19).

---

## Fase 6 — Frontend

**Objetivo.** A interface autoral, com identidade temática de RPG, conectada ao backend, permitindo **jogar o capítulo 1 inteiro pelo navegador**. Ver `mestre-frontend` para o princípio inegociável de identidade visual.

> **Sub-organização.** Esta fase é grande. As tarefas estão agrupadas em 4 blocos; cada bloco fecha algo navegável. Manter um commit por tarefa.

### Bloco 6.A — Fundação e fluxo de entrada

| # | Tarefa | Entrega |
|---|---|---|
| 6.1 | Scaffold | React + Vite + TS em `frontend/`. Dockerfile. Integrado ao `docker-compose.yml`. `npm run dev` sobe |
| 6.2 | i18n | Estrutura de textos por idioma (lib leve ou solução autoral). Português populado. Nenhum texto engessado no JSX |
| 6.3 | Layout das três zonas | Grid CSS das três zonas (PRD §6.4). Vazias por enquanto |
| 6.4 | Cliente de API | Funções tipadas para `/campaigns`, `/action` (SSE), `/state`, `/log`, `/turn/{n}/trace` |
| 6.5 | Tela inicial / landing | Tela de entrada do jogo: escolha entre **"Nova partida"** e **"Retomar partida"**. Identidade temática já aplicada (pode ser refinada após 6.6) |
| 6.6 | Tela de criação de partida | Escolha **Guerreiro vs Paladino** com prévia da ficha. Botão "Começar" → chama `POST /campaigns` → entra na tela de jogo. Mostra o ID anônimo da partida e instrui o jogador a salvá-lo |
| 6.7 | Tela de retomada por ID | Input do ID anônimo → chama `GET /campaigns/{id}/state` → se válido, entra na tela de jogo no estado correto; se inválido, mensagem de erro clara |

### Bloco 6.B — Identidade visual e zona de narração

| # | Tarefa | Entrega |
|---|---|---|
| 6.8 | Identidade visual temática | Tipografia serifada, paleta autoral, textura/pergaminho discreto, bordas trabalhadas. **Sem framework de componentes genérico**. Documentar decisões em refinamento da skill `mestre-frontend` |
| 6.9 | Zona de narração | Texto **com ritmo** (streaming SSE renderizado palavra a palavra ou chunk a chunk), fala de NPCs destacada visualmente, campo de entrada com peso editorial |
| 6.10 | Feedback de processamento | Indicador "o mestre está pensando..." durante o turno |

### Bloco 6.C — Painel de estado, grafo, e pensamento do mestre

| # | Tarefa | Entrega |
|---|---|---|
| 6.11 | Painel de estado | HP, nível, inventário, localização, objetivos. Consome `GET /state`. **Não exibe estado oculto** |
| 6.12 | Grafo de locações | SVG (React Flow ou lib leve confirmada na implementação). Nós se revelam progressivamente; posição atual destacada. Derivado dos dados do capítulo |
| 6.13 | Painel "pensamento do mestre" | Recolhível por seta; consome `/turn/{n}/trace`; mostra ruling, retrieval, rolagem, motivação da consequência |

### Bloco 6.D — Reatividade, robustez, voz, imagens

| # | Tarefa | Entrega |
|---|---|---|
| 6.14 | Feedback visual reativo | Pulsação de dano nas bordas; HP que anima a queda e treme em vermelho; rolagem de dado visível (gira antes de revelar); transição entre locações no grafo com peso; destaque de momentos-chave |
| 6.15 | Avisos de robustez | Aviso vermelho destacado quando o backend recusa o turno (ação impossível, abusiva, conteúdo proibido). Turno não é consumido visualmente |
| 6.16 | Tratamento de erro | Em falha do backend/LLM: aviso + **mensagem do jogador preservada na caixa de envio** |
| 6.17 | Provider de voz no backend | Interface `VoiceProvider` em `backend/app/providers/voice.py` + implementação **stub** (responde com sucesso vazio para STT/TTS). É o que a UI consome em 6.18. Implementação concreta é v2 |
| 6.18 | Interface de voz no frontend (stub) | Botão de gravar visível e clicável; chama o provider stub do backend. UI completa; o áudio não vai a lugar nenhum na v1 |
| 6.19 | Briefings de imagem do capítulo 1 | Para cada imagem necessária, briefing escrito no arquivo do capítulo (formato definido pela skill `mestre-criacao-de-historia`) |
| 6.20 | Geração externa das imagens | Briefings → Nano Banana → arquivos em `frontend/public/chapters/01/` ou equivalente. Versionados no Git |
| 6.21 | Integração das imagens | As imagens aparecem na zona de narração nas cenas apropriadas. Mapa continua sendo o grafo, **não** uma imagem |

**Critério de fase concluída.**
- [ ] Consigo entrar pela tela inicial, **criar uma partida** escolhendo personagem, e jogar o capítulo 1 do início ao fim pelo navegador sem usar curl.
- [ ] Consigo **fechar o navegador, abrir de novo e retomar** a partida pelo ID anônimo.
- [ ] As três zonas funcionam: narração com ritmo e fala de NPC destacada, painel de estado atualiza ao vivo, grafo se revela.
- [ ] A identidade visual passa no teste "isto **não** parece um chatbot genérico" (revisão sua).
- [ ] Reação de dano, rolagem visível, transição de locação e destaque de momento-chave estão presentes.
- [ ] Painel de "pensamento do mestre" recolhível e funcional.
- [ ] Os três casos de robustez exibem aviso vermelho destacado.
- [ ] Mensagem do jogador é preservada quando o backend falha (teste com backend mockado em erro).
- [ ] Botão de voz existe e é clicável (stub respondido pelo provider stub do backend).
- [ ] Imagens do capítulo 1 aparecem nas cenas certas; mapa é grafo SVG.
- [ ] Nenhum texto engessado no JSX.
- [ ] Frontend só fala com o backend. Nenhuma chave de LLM no bundle.
- [ ] Lint e tipos do frontend passam.

**Fora de escopo desta fase.**
Implementação concreta de STT/TTS (v2), inglês populado (v2), eval set (Fase 7), criação de personagem (v2).

---

## Fase 7 — Validação, eval set e polish

**Objetivo.** Fechar a v1: avaliar o comportamento dos agentes de forma sistemática, conferir os critérios do PRD §10 um a um, e preparar o repositório para ser público.

**Tarefas.**

| # | Tarefa | Entrega |
|---|---|---|
| 7.1 | Eval set do `RefereeAgent` | `tests/evals/referee/` — conjunto de "ação do jogador → ruling esperado" cobrindo casos típicos (rolagem necessária, rolagem desnecessária, dificuldade alta justificada, etc.). Rodável via avaliação do ADK |
| 7.2 | Eval set do `NarratorAgent` | Sanity checks de tom, fidelidade ao lore, ausência de regra alucinada |
| 7.3 | Eval set de robustez | Casos curados de injeção/abuso/conteúdo proibido vs. ações válidas; mede falso-positivo e falso-negativo |
| 7.4 | Cobertura de testes do motor | Revisão final — tudo importante coberto |
| 7.5 | README final | Visão do projeto, screenshot/GIF, instruções de setup com Docker Compose, link para os documentos, créditos (SRD 5.1) |
| 7.6 | `LICENSE`, `NOTICE`, `CONTRIBUTING.md` | Apache 2.0 confirmada; NOTICE com a atribuição padrão da Wizards of the Coast; CONTRIBUTING com fluxo mínimo |
| 7.7 | Conferência PRD §10 | Checklist item a item da "Definition of Done" da v1. Cada item validado manualmente |
| 7.8 | Revisão final das skills | Conferência das skills `mestre-backend` e `mestre-frontend`. O **refinamento contínuo** dessas skills acontece **ao longo das fases**, conforme cada `[REFINAR APÓS FASE X]` for sendo concluída — esse é o fluxo definido na skill `mestre-fluxo-de-trabalho` e no seu checklist de fim de tarefa. Na Fase 7, só se verifica que **nada ficou pendente** e que as seções refletem o que a prática realmente ensinou |
| 7.9 | Sincronização de documentos | Onde a implementação divergiu, `PRD.md`/`ARQUITETURA.md`/`DECISOES.md` são atualizados. Nada de divergência silenciosa |
| 7.10 | Renomeação Mestre → Unscripted | Substituir o codinome em todos os documentos e identificadores. Última coisa antes de tornar público |

**Critério de fase concluída.**
- [ ] Todos os 16 itens da checklist do PRD §10 estão verdadeiros.
- [ ] `pytest` (motor + evals) verde.
- [ ] README permite que alguém clone, rode `docker compose up` e jogue.
- [ ] `LICENSE`, `NOTICE`, `CONTRIBUTING.md` em forma final.
- [ ] Skills `mestre-backend` e `mestre-frontend` não têm mais `[REFINAR APÓS FASE]`.
- [ ] Documentos refletem a realidade do código.
- [ ] Renomeação para Unscripted concluída.
- [ ] Repositório pronto para ser tornado público.

---

## Após a v1

A v1 é um **todo coerente**. A partir daqui, v2 e v3+ são **acoplamentos**: capítulo 2, grupo de personagens, voz real, inglês, contas, multiplayer, Vertex AI. Ver `PRD.md` §11 e `DECISOES.md` ADR-021.

Cada novo item nasce com a mesma régua: planejar, fatia vertical, decisão registrada, qualidade verificada antes do commit.
