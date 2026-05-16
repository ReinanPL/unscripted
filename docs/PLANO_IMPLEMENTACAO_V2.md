# PLANO DE IMPLEMENTAÇÃO — v2

**Projeto:** Unscripted
**Documentos relacionados:** `PRD.md` (o quê e por quê), `ARQUITETURA.md` (como), `DECISOES.md` (histórico das decisões), `PLANO_IMPLEMENTACAO.md` (v1 — imutável).

> Este é o **mapa de execução da v2**. A v1 está fechada e publicada (commit `76d03fd`, 16/16 critérios da PRD §10 validados). A v2 evolui aqui sem inflar o documento da v1.
>
> A abertura formal da v2 está em `DECISOES.md` (ADR-044). O método e os princípios são os mesmos da v1.

---

## Princípios que regem este plano (herdados da v1)

1. **Fatias verticais que rodam.** Cada fase termina com algo demonstrável de ponta a ponta — não com uma camada horizontal pela metade.
2. **Uma fase de cada vez.** Não se inicia a próxima sem a anterior concluída e validada.
3. **Cada tarefa = um commit.** Mensagens no padrão (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`). Lint e checagem de tipos via pre-commit.
4. **O que NÃO entra na fase é tão importante quanto o que entra.** Cada fase tem seção "Fora de escopo".
5. **Decisão nova → ADR.** Registra-se em `DECISOES.md` antes de avançar.
6. **Testes proporcionais.** Eval set sistemático para qualquer mudança que toque os agentes.
7. **v2 é acoplamento, não reescrita.** Cada item aproveita um gancho da v1; nenhum item refaz parte do que já existe.

---

## Visão geral da v2

| Fase | Nome | Entrega central | Validação |
|---|---|---|---|
| **1** | **Multi-provider LLM** | Gemini + Groq + OpenAI com split por agente | Eval set passa em pelo menos 2 providers além de Gemini; smoke fim-a-fim nos 3 |
| 2 | Grupo de personagens | Party de 3-4 personagens controlada pelo jogador | Combate típico em equipe rola completo |
| 3 | Criação de personagem | Escolha de raça/classe/atributos | Personagem custom joga capítulo 1 |
| 4 | Descanso e recuperação | Acampar, recuperar HP, repreparar magias | Sessão longa exercita o ciclo |
| 5 | Itens reais | Usar poções, equipar armas que mudam chances | Itens entram nos rulings do Referee |
| 6 | Progressão | XP + subida de nível entre capítulos | Personagem evolui na transição cap 1 → cap 2 |
| 7 | Rolagem transparente | Jogador vê modificadores, bônus, motivo da DC | Painel pensamento + zona de narração |
| 8 | Voz (STT/TTS concreto) | Provider de voz real substitui o stub | Fala-se com o mestre; ouve-se a narração |
| 9 | Inglês | i18n PT + EN com troca de idioma | Joga em EN com mesmo capítulo |
| 10 | Capítulo 2 | Adventure file novo, acoplado ao motor | Cap 2 jogável de ponta a ponta |

A ordem é uma proposta — pode ser revista entre fases. A Fase 1 é fixa (já escolhida).

---

## Fase 1 — Multi-provider LLM (em execução)

**Objetivo.** Implementar Gemini + Groq + OpenAI com split por agente (REASONING + NARRATIVE), seleção por env var, e eval comparativo para escolher modelos default. Resolve a fricção de quota do free tier do Gemini e estabelece a infraestrutura multi-LLM para o resto da v2.

**Tarefas (executadas em Blocos com commit por Bloco):**

| # | Bloco | Entrega |
|---|---|---|
| 1.0 | Enquadramento de versão | PRD §11 e ADR-021 atualizados; ADR-044 (Abertura da v2) e ADR-045 (Multi-provider) registrados; este documento criado |
| 1.1 | Refactor da camada de providers | `litellm>=1.50` em deps; Settings expandido; `LlmProvider` Protocol com `build_model(purpose)`; `GroqProvider` e `OpenAiProvider` implementados; `.env.example` documentado |
| 1.2 | Testes determinísticos | `tests/agents/test_provider_dispatch.py` e `test_provider_fallback.py`; suite default verde, cobertura ≥90% no motor |
| 1.3 | Smoke do Referee com Groq | Eval set rodado contra 4 modelos (`llama-3.3-70b-versatile`, `qwen/qwen3-32b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`); melhor vira default REASONING; resultados em `PROVIDERS.md` |
| 1.4 | Smoke do Narrator com Groq | Eval set rodado contra `llama-3.1-8b-instant`; streaming chunked e regressão grossa validados |
| 1.5 | Smoke do OpenAI | Eval set Referee + Narrator contra `gpt-4o-mini` |
| 1.6 | Smoke fim-a-fim no navegador | 1 turno completo em cada um dos 3 providers (Groq, OpenAI, Gemini); painel pensamento popula; SSE chega chunked |
| 1.7 | Plan B (contingência) | Só se Bloco 1.3 falhar 0/4: parsing manual do Ruling com retry (ADR-046) |
| 1.8 | Documentação | `docs/PROVIDERS.md` (novo); `ARQUITETURA.md` §7 atualizado; `README.md` com seção "Choose your LLM provider"; este documento marca Fase 1 como concluída |
| 1.9 | Fechamento da Fase 1 | `pytest` verde; commits limpos; sem push até confirmação |

**Critério de fase concluída.**
- [ ] `pytest` (sem `-m eval`) → verde, cobertura ≥90% no motor.
- [ ] `LLM_PROVIDER=groq pytest -m eval --no-cov` → Referee e Narrator passam.
- [ ] `LLM_PROVIDER=openai pytest -m eval --no-cov` → Referee e Narrator passam.
- [ ] `LLM_PROVIDER=gemini_aistudio docker compose up` → regressão zero (mantém comportamento da v1).
- [ ] `LLM_PROVIDER=groq docker compose up` → 1 turno joga ponta a ponta no navegador.
- [ ] `LLM_PROVIDER=openai docker compose up` → 1 turno joga ponta a ponta no navegador.
- [ ] `docs/PROVIDERS.md` existe com tabela comparativa preenchida.
- [ ] README tem seção "Choose your LLM provider".
- [ ] ADR-044, ADR-045 registrados; (eventual) ADR-046 se Plan B for ativado.

**Fora de escopo desta fase.**
- Tools/function calling com LiteLlm (não usamos no v1; entra quando v2 introduzir agentes com tools reais).
- Anthropic Claude como provider (mesma arquitetura, mas fica para uma Fase posterior se houver demanda).
- Vertex AI (ADR-008 cobre como v3+).
- Outros itens da v2 (Fases 2-10).
- Push para `origin/main` — usuário decide.

---

## Fases 2-10 — esboço (refinadas no momento certo)

As fases abaixo serão detalhadas como a Fase 1 quando chegar o momento de cada uma. Não antecipar 100% agora — isso seria over-engineering aplicado ao planejamento (mesmo princípio da v1).

- **Fase 2 — Grupo de personagens.** Modelo de estado passa a ter `party: list[Character]` em vez de um único `character`. Loop de turno escolhe qual personagem age. Interface mostra a party.
- **Fase 3 — Criação de personagem.** Substitui a tela `CreateCampaign` por um fluxo de criação. Schema novo em `content/character_options/`.
- **Fase 4 — Descanso e recuperação.** Nova ação determinística no motor. Capítulos passam a definir locais de descanso.
- **Fase 5 — Itens reais.** Schema de `Item` ganha `effects`. Motor consome efeitos em testes de perícia.
- **Fase 6 — Progressão.** XP + level up. Persistência entre capítulos via `flags.objectives_completed`.
- **Fase 7 — Rolagem transparente.** Painel pensamento ganha visualização rica de modificadores; UI mostra a matemática.
- **Fase 8 — Voz STT/TTS.** `VoiceProvider` ganha implementação real (provavelmente OpenAI Whisper + ElevenLabs, ou alternativa free).
- **Fase 9 — Inglês.** `frontend/src/i18n/en.ts` populado; troca de idioma na UI; prompts dos agentes traduzidos.
- **Fase 10 — Capítulo 2.** Novo arquivo em `content/chapters/chapter-02/`. Ingestão automática (já idempotente). Gancho de transição cap 1 → cap 2.

---

## Após a v2

A v3+ muda a natureza do sistema (multi-usuário, contas, plataforma). Cada item dessa lista vira um plano próprio quando o momento chegar. Ver `PRD.md` §11 e `DECISOES.md` ADR-021.
