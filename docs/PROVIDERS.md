# Provedores de LLM — Comparativo

O Unscripted suporta **três provedores de LLM** desde a Fase 1 da v2 (ADR-044, ADR-045). A escolha é feita pela env var `LLM_PROVIDER`. Cada provedor declara dois modelos (split por agente — ADR-045):

- **`*_MODEL_REASONING`** → `RefereeAgent` (output estruturado via `output_schema=Ruling`).
- **`*_MODEL_NARRATIVE`** → `NarratorAgent` e `NPCActorAgent` (streaming de prosa).
- Se `NARRATIVE` é omitido, faz fallback para `REASONING` (comportamento single-model preservado).

---

## Resumo das recomendações

| Caso de uso | Provider | Modelo REASONING | Modelo NARRATIVE | Custo |
|---|---|---|---|---|
| **Free, alto volume** | `groq` | `llama-3.3-70b-versatile` | `llama-3.1-8b-instant` | $0 |
| Pago, alta qualidade | `openai` | `gpt-4o-mini` | `gpt-4o-mini` | ~$0.001/turno |
| Free, baixo volume / sanity | `gemini_aistudio` | `gemini-2.5-flash` | (fallback) | $0, mas só 20 RPD |

---

## Tabela de modelos Groq — free tier

> Sistema chama **2-3 LLMs/turno** (1 Referee + 1 Narrator + 0-1 NPC).

| Modelo | RPM | RPD | TPM | TPD | Turnos/dia¹ |
|---|---|---|---|---|---|
| `llama-3.1-8b-instant` | 30 | **14.4K** | 6K | 500K | gargalo no Referee² |
| `llama-3.3-70b-versatile` | 30 | 1K | 12K | 100K | **1.000** |
| `qwen/qwen3-32b` | 60 | 1K | 6K | 500K | 1.000 |
| `openai/gpt-oss-120b` | 30 | 1K | 8K | 200K | 1.000 |
| `openai/gpt-oss-20b` | 30 | 1K | 8K | 200K | 1.000 |
| `meta-llama/llama-4-scout-17b` | 30 | 1K | 30K | 500K | 1.000 |

¹ Considerando split por agente.
² Quando combinado com llama-3.3-70b como REASONING (1K RPD); o NARRATIVE não é gargalo.

---

## Resultado do eval set do RefereeAgent (Bloco 3 da Fase 1 da v2)

Eval de 8 casos contra o `output_schema=Ruling` (Pydantic), via Groq + LiteLlm. Comando: `LLM_PROVIDER=groq GROQ_MODEL_REASONING=<modelo> pytest -m eval tests/evals/referee/ --no-cov`.

| Modelo | Passou | Falhou | Observações |
|---|---|---|---|
| **`llama-3.3-70b-versatile`** | **6/8 (75%)** | 2 | ✓ Vencedor. Falhas são opinião do modelo (achou `percepcao_pegadas` e `cura_em_descanso` triviais; debatable). JSON estruturado válido. |
| `qwen/qwen3-32b` | 0/8 | 8 | Groq retorna `tool_use_failed` em todos os casos. Modelo entende a estrutura mas tem typos esporádicos (`objectives_continued` em vez de `objectives_completed`) e o strict schema do Groq rejeita. |
| `openai/gpt-oss-120b` | 0/8 | 8 | Modelo emite "chain of thought" (`"We need to produce JSON Ruling..."`) em vez do JSON direto. Comportamento típico dos modelos `gpt-oss` da Groq — incompatível com `output_schema` sem ajuste de prompt. |
| `openai/gpt-oss-20b` | 0/8 | 8 | Mesmo problema do 120b. |

**Conclusão:** `llama-3.3-70b-versatile` é o **único** modelo Groq do free tier que produz output estruturado válido de forma consistente com a configuração padrão do ADK. Default eleito.

---

## Resultado do eval set do NarratorAgent

Eval de 6 casos contra streaming + regressão grossa (sem regra alucinada, sem meta-fala, sem contradição de lore). Comando: `LLM_PROVIDER=groq pytest -m eval tests/evals/narrator/ --no-cov`.

| Modelo | Passou | Falhou | Observações |
|---|---|---|---|
| **`llama-3.1-8b-instant`** | **6/6 (100%)** | 0 | ✓ Streaming chunked, sem meta-fala detectada, sem números de dado alucinados, sem contradição de lore. Modelo leve e rápido — ideal pra NARRATIVE. |

---

## Validações em smoke fim-a-fim (Bloco 6)

| Provider | Smoke navegador | Notas |
|---|---|---|
| `groq` | ✓ | 1 turno completo (`Caminho até o balcão e cumprimento Grimwald com um aceno discreto`). Referee decidiu trivial; Narrator gerou prosa em streaming; NPC Grimwald reagiu; painel "pensamento do mestre" populou ruling, retrieval (regras + lore), consequência. |
| `gemini_aistudio` | ✓ (via testes) | Regressão zero validada via `test_provider_dispatch.py` + `test_provider_fallback.py` (19/19). `build_model` retorna a mesma string que retornava na v1. |
| `openai` | pendente | Não validado nesta entrega (`OPENAI_API_KEY` não foi provida). Estrutura pronta; basta preencher `.env` e rodar `pytest -m eval`. |

---

## Como mudar de provider

Edite `.env`:

```bash
# Para usar Groq (free, alta quota)
LLM_PROVIDER=groq

# Para usar OpenAI (pago, alta qualidade)
LLM_PROVIDER=openai

# Para usar Gemini (free, baixa quota — só pra sanity)
LLM_PROVIDER=gemini_aistudio
```

Depois reinicie o backend: `docker compose restart backend`.

Cada provider tem sua API key dedicada (`GROQ_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`). Veja [.env.example](../.env.example) para a lista completa de variáveis.

---

## Custo aproximado por provider (1.000 turnos)

| Provider | Modelo | Custo total | Por turno |
|---|---|---|---|
| Groq | qualquer free tier | **$0** | $0 |
| OpenAI | `gpt-4o-mini` | ~$1.00 | ~$0.001 |
| Gemini AI Studio | `gemini-2.5-flash` (free) | **$0** | $0 (mas limitado a 20 turnos/dia) |
| Gemini AI Studio | `gemini-2.5-flash` (pago) | ~$0.30 | ~$0.0003 |

Estimativa baseada em ~2.000 tokens por turno (input rico + output curto do Referee + prosa do Narrator).

---

## Limitações conhecidas

- **`qwen3-32b` e modelos `gpt-oss`** do Groq não funcionam como REASONING com a configuração padrão. Permanecem disponíveis no `.env.example` como referência, mas não são default. Se quiser tentar usar, pode ser necessário relaxar o `output_schema` (vide Plan B no plano da Fase 1).
- **Quota de TPM (Groq)** pode causar rate limit ao rodar evals em sequência. O eval set tem retry automático com backoff específico — ver `tests/evals/referee/test_referee_eval.py`.
- **Falhas semânticas do modelo** (não técnicas) variam por modelo: alguns rulings de borderline são debatable, e o eval set falha alguns casos onde o modelo escolheu uma decisão razoável mas diferente da esperada. Não confundir com problema arquitetural.
