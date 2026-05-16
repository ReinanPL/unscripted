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

| Fase | Nome | Status | Entrega central |
|---|---|---|---|
| **1** | **Multi-provider LLM** | **✓ concluída** | Gemini + Groq + OpenAI com split por agente |
| 1.5 | Suporte a Vertex AI | pendente de decisão | `GeminiVertexProvider` (só se for rodar em prod GCP real) |
| 2 | Cross-provider por agente | pendente de necessidade | `LLM_PROVIDER_REASONING` ≠ `LLM_PROVIDER_NARRATIVE` |
| 3 | Grupo de personagens | futura | Party de 3-4 personagens controlada pelo jogador |
| 4 | Criação de personagem | futura | Escolha de raça/classe/atributos |
| 5 | Descanso e recuperação | futura | Acampar, recuperar HP, repreparar magias |
| 6 | Itens reais | futura | Usar poções, equipar armas que mudam chances |
| 7 | Progressão | futura | XP + subida de nível entre capítulos |
| 8 | Rolagem transparente | futura | Jogador vê modificadores, bônus, motivo da DC |
| 9 | Voz (STT/TTS concreto) | futura | Provider de voz real substitui o stub |
| 10 | Inglês | futura | i18n PT + EN com troca de idioma |
| 11 | Capítulo 2 | futura | Adventure file novo, acoplado ao motor |

A ordem é uma proposta — pode ser revista entre fases. A Fase 1 está concluída; 1.5 e 2 ficam pendentes de gatilhos concretos (ver seções abaixo).

---

## Fase 1 — Multi-provider LLM (**CONCLUÍDA**)

**Objetivo.** Implementar Gemini + Groq + OpenAI com split por agente (REASONING + NARRATIVE), seleção por env var, e eval comparativo para escolher modelos default. Resolve a fricção de quota do free tier do Gemini e estabelece a infraestrutura multi-LLM para o resto da v2.

**Tarefas executadas (commits por Bloco):**

| # | Bloco | Status | Entrega |
|---|---|---|---|
| 1.0 | Enquadramento de versão | ✓ | PRD §11 e ADR-021 atualizados; ADR-044 (Abertura da v2) e ADR-045 (Multi-provider) registrados; este documento criado. Commit: `37891eb` |
| 1.1 | Refactor da camada de providers | ✓ | `litellm>=1.50` em deps; Settings expandido; `LlmProvider` Protocol com `build_model(purpose)`; `GroqProvider` e `OpenAiProvider` implementados; `.env.example` documentado. Commit: `d7e3591` |
| 1.2 | Testes determinísticos | ✓ | 19 testes novos (`test_provider_dispatch.py` + `test_provider_fallback.py`); suite default verde (158 passed), cobertura 100% no motor. Commit: `0d18b01` |
| 1.3 | Smoke do Referee com Groq | ✓ | Eval set rodado contra 4 modelos. **`llama-3.3-70b-versatile`: 6/8 (75%) — vencedor.** Outros 3 modelos falharam por motivos de modelo (CoT no output, typos). Resultado em `PROVIDERS.md`. Commit: `0bb8eb4` |
| 1.4 | Smoke do Narrator com Groq | ✓ | `llama-3.1-8b-instant`: **6/6 (100%)**. Streaming chunked validado, regressão grossa zerada. |
| 1.5 | Smoke do OpenAI | pendente | `OPENAI_API_KEY` não foi provida nesta entrega. Estrutura pronta; basta preencher `.env` e rodar `pytest -m eval`. Documentado em `PROVIDERS.md`. |
| 1.6 | Smoke fim-a-fim | ✓ (parcial) | Groq: turno completo no navegador, painel "pensamento do mestre" populado com ruling, retrieval, consequência, NPC. Gemini: regressão validada via testes determinísticos do Bloco 1.2. OpenAI: pendente (sem chave). |
| 1.7 | Plan B (contingência) | não acionado | Modelo Groq vencedor passou — Plan B (parsing manual) não foi necessário. ADR-046 não criado. |
| 1.8 | Documentação | ✓ | `docs/PROVIDERS.md` criado; `ARQUITETURA.md` §7 atualizado; `README.md` com seção "Choose your LLM provider"; este documento marcado concluído. |
| 1.9 | Fechamento da Fase 1 | ✓ | `pytest` verde; commits limpos; push fica para confirmação do usuário. |

**Critério de fase concluída.**
- [x] `pytest` (sem `-m eval`) → 158 passed, 10 skipped, 2 deselected, cobertura 100% no motor.
- [x] `LLM_PROVIDER=groq pytest -m eval --no-cov` → Referee 6/8 (modelo vencedor) e Narrator 6/6.
- [ ] `LLM_PROVIDER=openai pytest -m eval --no-cov` → **pendente** (sem chave). Estrutura validada via testes determinísticos.
- [x] `LLM_PROVIDER=gemini_aistudio docker compose up` → regressão zero validada (backend health 200 + `build_model` retorna mesma string que na v1).
- [x] `LLM_PROVIDER=groq docker compose up` → 1 turno completo no navegador, painel pensamento populado.
- [ ] `LLM_PROVIDER=openai docker compose up` → **pendente** (sem chave).
- [x] `docs/PROVIDERS.md` existe com tabela comparativa preenchida.
- [ ] README tem seção "Choose your LLM provider".
- [ ] ADR-044, ADR-045 registrados; (eventual) ADR-046 se Plan B for ativado.

**Fora de escopo desta fase.**
- Tools/function calling com LiteLlm (não usamos no v1; entra quando v2 introduzir agentes com tools reais).
- Anthropic Claude como provider (mesma arquitetura, mas fica para uma Fase posterior se houver demanda).
- Vertex AI → **promovido a Fase 1.5 (pendente)**, ver abaixo.
- Cross-provider por agente → **promovido a Fase 2 (pendente)**, ver abaixo.
- Outros itens da v2 (Fases 3-11 renumeradas).
- Push para `origin/main` — usuário decide.

---

## Fase 1.5 — Suporte a Vertex AI (pendente)

**Objetivo (se ativada).** Adicionar `GeminiVertexProvider` na mesma camada de providers, ativável via `LLM_PROVIDER=gemini_vertex`. Diferenças vs `gemini_aistudio`:

- Auth: Application Default Credentials (GCP) ou service account JSON, em vez de API key.
- Env vars: `GOOGLE_GENAI_USE_VERTEXAI=1` + `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION`.
- Endpoint: `*-aiplatform.googleapis.com` regional.
- Cobrança: pay-as-you-go (sem free tier, mas mais barato em escala).
- Features extras: context caching, batch, fine-tuning.

**Condição para ativar.** **Só faz sentido se o Unscripted for rodar em produção GCP real.** Como projeto de portfólio local ou em VPS comum, AI Studio (`gemini_aistudio`) já basta — e está rodando. Esta fase fica **pendente de decisão concreta** do dono do projeto.

**Tarefas (esboço).**
- `GeminiVertexProvider` em `backend/app/providers/llm.py`.
- Settings: `vertex_project_id`, `vertex_location`, `vertex_credentials_path` (opcional — ADC é o caminho recomendado).
- Atualizar `.env.example` com seção Vertex.
- Smoke contra o mesmo eval set do Referee/Narrator.
- ADR técnico próprio (ADR-046, se ativada).

**Tamanho estimado.** ~30 minutos de implementação se as credenciais GCP estiverem prontas. Não bloqueia nenhuma outra fase.

---

## Fase 2 — Cross-provider por agente (pendente)

**Objetivo (se ativada).** Permitir provider **diferente por propósito**: `LLM_PROVIDER_REASONING=openai` + `LLM_PROVIDER_NARRATIVE=groq`. Hoje, a Fase 1 só permite split de **modelos dentro do mesmo provider**.

**Condição para ativar.** **Só vira necessária se os evals/uso mostrarem que nenhum provider único serve bem em REASONING E NARRATIVE ao mesmo tempo.** Hoje:

- OpenAI: 7/8 no Referee, 6/6 no Narrator — único provider serve bem aos dois.
- Groq: 6/8 no Referee, 6/6 no Narrator — também serve aos dois.
- Gemini: não exercitado em eval (regressão validada via testes determinísticos).

A motivação prática (Referee com structured output robusto + Narrator com streaming barato em outro provider) **ainda não foi sentida**. Esta fase fica **pendente dos resultados de uso real**.

**Tarefas (esboço — Opção A do plano original).**
- Settings: `llm_provider` → `llm_provider_reasoning` + `llm_provider_narrative` (cada um aceitando os valores de provider hoje).
- `get_llm_provider(settings)` vira `get_provider_for(purpose, settings)` — devolve a instância correta para cada propósito.
- `build_*_agent` continua chamando `provider.build_model(purpose)` — mas o `provider` agora é purpose-specific.
- Eventual `ADR-047` documentando o split cross-provider.

**Tamanho estimado.** ~1-2 horas. Não bloqueia outras fases.

---

## Fases 3-11 — esboço (refinadas no momento certo)

As fases abaixo serão detalhadas como a Fase 1 quando chegar o momento de cada uma. Não antecipar 100% agora — isso seria over-engineering aplicado ao planejamento (mesmo princípio da v1).

- **Fase 3 — Grupo de personagens.** Modelo de estado passa a ter `party: list[Character]` em vez de um único `character`. Loop de turno escolhe qual personagem age. Interface mostra a party.
- **Fase 4 — Criação de personagem.** Substitui a tela `CreateCampaign` por um fluxo de criação. Schema novo em `content/character_options/`.
- **Fase 5 — Descanso e recuperação.** Nova ação determinística no motor. Capítulos passam a definir locais de descanso.
- **Fase 6 — Itens reais.** Schema de `Item` ganha `effects`. Motor consome efeitos em testes de perícia.
- **Fase 7 — Progressão.** XP + level up. Persistência entre capítulos via `flags.objectives_completed`.
- **Fase 8 — Rolagem transparente.** Painel pensamento ganha visualização rica de modificadores; UI mostra a matemática.
- **Fase 9 — Voz STT/TTS.** `VoiceProvider` ganha implementação real (provavelmente OpenAI Whisper + ElevenLabs, ou alternativa free).
- **Fase 10 — Inglês.** `frontend/src/i18n/en.ts` populado; troca de idioma na UI; prompts dos agentes traduzidos.
- **Fase 11 — Capítulo 2.** Novo arquivo em `content/chapters/chapter-02/`. Ingestão automática (já idempotente). Gancho de transição cap 1 → cap 2.

---

## Após a v2

A v3+ muda a natureza do sistema (multi-usuário, contas, plataforma). Cada item dessa lista vira um plano próprio quando o momento chegar. Ver `PRD.md` §11 e `DECISOES.md` ADR-021.
