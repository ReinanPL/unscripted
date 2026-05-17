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

## Resultado do eval set do RefereeAgent

Eval de 8 casos contra o `output_schema=Ruling` (Pydantic). Comando: `LLM_PROVIDER=<p> <MODEL_REASONING>=<m> pytest -m eval tests/evals/referee/ --no-cov`.

| Provider · Modelo | Passou | Falhou | Observações |
|---|---|---|---|
| **`openai` · `gpt-4o-mini`** | **7/8 (87.5%)** | 1 | ✓ **Melhor resultado.** Única falha: `cura_em_descanso` (modelo achou trivial). Output estruturado robusto, sem rate limit. Latência típica ~3-5s por chamada. |
| **`groq` · `llama-3.3-70b-versatile`** | **6/8 (75%)** | 2 | ✓ **Default Groq.** Falhas: `percepcao_pegadas` e `cura_em_descanso` (modelo achou triviais; debatable). JSON estruturado válido. Rate limit TPM ~12K/min — eval set tem retry com backoff específico. |
| `groq` · `qwen/qwen3-32b` | 0/8 | 8 | Groq retorna `tool_use_failed` em todos os casos. Modelo entende a estrutura mas tem typos esporádicos (`objectives_continued` em vez de `objectives_completed`) e o strict schema do Groq rejeita. |
| `groq` · `openai/gpt-oss-120b` | 0/8 | 8 | Modelo emite "chain of thought" (`"We need to produce JSON Ruling..."`) em vez do JSON direto. Comportamento típico dos modelos `gpt-oss` da Groq — incompatível com `output_schema` sem ajuste de prompt. |
| `groq` · `openai/gpt-oss-20b` | 0/8 | 8 | Mesmo problema do 120b. |

**Conclusão.**
- **`gpt-4o-mini` (OpenAI)** tem o melhor resultado absoluto — recomendado quando há orçamento para uso pago (~$0.001/turno).
- **`llama-3.3-70b-versatile` (Groq free)** é o melhor entre os gratuitos — único modelo Groq do free tier que produz output estruturado válido consistente com a configuração padrão do ADK. Default Groq.

---

## Resultado do eval set do NarratorAgent

Eval de 6 casos contra streaming + regressão grossa (sem regra alucinada, sem meta-fala, sem contradição de lore). Comando: `LLM_PROVIDER=<p> <MODEL_NARRATIVE>=<m> pytest -m eval tests/evals/narrator/ --no-cov`.

| Provider · Modelo | Passou | Falhou | Observações |
|---|---|---|---|
| **`openai` · `gpt-4o-mini`** | **6/6 (100%)** | 0 | ✓ Streaming chunked, narrações ~50% mais longas que o llama-8b (1000-1500 chars), mais detalhe descritivo. Sem regressões grossas. |
| **`groq` · `llama-3.1-8b-instant`** | **6/6 (100%)** | 0 | ✓ Streaming chunked, narrações mais enxutas (600-850 chars). Modelo leve e rápido — ideal pra NARRATIVE em alta quota. |

**Conclusão.** Os dois modelos passaram em 100% dos checks de regressão grossa. Diferença prática: detalhamento da prosa (gpt-4o-mini mais rico) vs custo/quota (llama-3.1-8b grátis e altíssima quota).

---

## Validações em smoke fim-a-fim (Bloco 6)

| Provider | Smoke navegador | Notas |
|---|---|---|
| `groq` | ✓ | 1 turno completo (`Caminho até o balcão e cumprimento Grimwald com um aceno discreto`). Referee decidiu trivial; Narrator gerou prosa em streaming; NPC Grimwald reagiu; painel "pensamento do mestre" populou ruling, retrieval (regras + lore), consequência. |
| `openai` | ✓ | 1 turno completo (`Sento numa das mesas vazias e observo os outros clientes com discrição`). Referee decidiu trivial; Narrator gerou prosa em streaming (mais longa e detalhada que o llama); NPC Grimwald reagiu; painel pensamento populado. Notável: gpt-4o-mini inseriu uma meta-fala fraca ("O que você fará a seguir?") que escapou ao filtro do eval — anotado para refinamento de regex em futuras iterações. |
| `gemini_aistudio` | ✓ (via testes) | Regressão zero validada via `test_provider_dispatch.py` + `test_provider_fallback.py` (19/19). `build_model` retorna a mesma string que retornava na v1. |

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
- **Meta-fala sutil escapa do filtro:** o eval do Narrator usa regex específico para padrões "como mestre", "vou narrar", "agora vamos". Frases mais brandas como "O que você fará a seguir?" passam — observado no smoke do `gpt-4o-mini`. Refinamento do regex é trabalho de iteração futura, não bloqueante.

---

# Voz — STT e TTS

Entregue na Fase 3 da v2 (ADR-046, ADR-047, ADR-048, ADR-049). Substitui o stub `VoiceProvider` unificado da v1 por dois Protocols independentes — `SttProvider` (`backend/app/providers/stt.py`) e `TtsProvider` (`backend/app/providers/tts.py`), selecionáveis por env separada.

## STT — Groq Whisper (`whisper-large-v3-turbo`)

| Característica | Valor |
|---|---|
| Provider default | `STT_PROVIDER=groq` |
| Modelo default | `whisper-large-v3-turbo` |
| Custo | **$0** (free tier) |
| Quota free tier | ~14.4K RPD |
| Latência típica | ~1s para áudio de ~5-10s |
| PT-BR | nativo, sem ajustes |
| Formatos aceitos | webm/opus (MediaRecorder default), mp3, mp4, m4a, ogg, wav, flac |
| Chave | reaproveita `GROQ_API_KEY` do LLM |
| Override de modelo | `GROQ_STT_MODEL` no `.env` |

`StubSttProvider` permanece disponível para CI/dev sem chaves (responde com texto vazio). Implementação concreta usa `litellm.atranscription` — mesma camada do split de LLM da Fase 1.

## TTS — OpenAI `gpt-4o-mini-tts`

| Característica | Valor |
|---|---|
| Provider default | `TTS_PROVIDER=openai` |
| Modelo default | `gpt-4o-mini-tts` |
| Voz default | `echo` (escolhida no Bloco 2 após teste das 5 vozes — ADR-049) |
| Custo aprox. | ~$0.015 / 1K caracteres → ~$0.001/turno típico |
| Latência típica | ~1-2s por frase (~100-200 chars) |
| PT-BR | nativo, sem ajustes |
| Formato de saída | MP3 (audio/mpeg) |
| Chave | reaproveita `OPENAI_API_KEY` do LLM |
| Override de modelo/voz | `OPENAI_TTS_MODEL` e `OPENAI_TTS_VOICE` no `.env` |

Vozes disponíveis testadas: `alloy`, `sage`, `echo`, `coral`, `shimmer`. Script `scripts/sample_tts_voices.py` gera amostras com o `read_aloud` da starting_scene do capítulo 1 para escolha local.

`StubTtsProvider` preservado para CI/dev sem chaves.

## Sincronia texto+voz por frase

Quando `tts_enabled=true` na request `/action`, o backend (`_stream_with_audio` em `runner_turn.py`) detecta fim de frase no stream do Narrator/NPC via `SentenceBuffer` puro (regex `[.!?…]\s+` ou `\n`, com tratamento de decimais, abreviações `Sr./Dr./etc.`, reticências, aspas fechantes). A cada frase fechada, dispara `asyncio.create_task(tts.synthesize(frase))` **em paralelo** ao yield dos chunks de texto. Áudios chegam via evento `audio_sentence` (base64 MP3 + `sentence_index`) no mesmo SSE — reordenação garantida pelo backend (frases ficam no buffer até a anterior estar pronta).

**Custo zero quando off.** Default `tts_enabled=false`. Toggle persiste em `localStorage` no frontend (`unscripted.tts_enabled`). Cada turno com TTS on custa ~$0.001 (gpt-4o-mini-tts × ~10-15 frases).

## TTS local descartado

Coqui, Bark e similares **não entram** na arquitetura do projeto. Razão: quebram a portabilidade do `docker compose up` (ADR-010) — modelos grandes, possivelmente GPU, container pesado. O projeto é multi-ambiente (local + VPS comum) e qualquer dependência além de HTTP arranha esse contrato.

## Limites conhecidos

- **Webm/opus do Chrome** atravessa sem conversão. Safari grava `audio/mp4`; também aceito. Outros browsers caem no fallback `webm` por extensão de filename.
- **Latência percebida da 1ª frase** depende do quanto o LLM demora pra fechar a primeira frase. Texto inteiro do mestre tem ~10-15 frases; primeira frase típica fecha em 2-5s e o áudio chega em mais 1-2s.
- **Dedupe defensivo** (ADR-048 + Fix B do pós-smoke): quando o ADK emite um evento final cumulativo gigante que cai no `else` do `_stream_agent_text`, o `_stream_with_audio` evita gerar duplicatas via dedupe de frase com exceção adjacente. Repetição imediata legítima (`"Silêncio. Silêncio."`) passa; repetição não-adjacente é tratada como reprocesso e skipada.
- **Fila de áudio limpa por turno.** Cada novo turno (`handleSubmit`) chama `audioQueue.clear()` antes de enfileirar — descarta áudios pendentes do turno anterior. Tradeoff aceito: se o jogador clicar AGIR no meio do áudio anterior, o áudio para. Comportamento esperado em UI conversacional.

---

## Trabalho futuro relacionado a providers

Itens identificados durante a v2 mas **não executados** — registrados como fases futuras:

- **Fase 1.5 — Suporte a Vertex AI** (ver `PLANO_IMPLEMENTACAO_V2.md`). Adicionar `GeminiVertexProvider` na mesma camada de providers, ativável via `LLM_PROVIDER=gemini_vertex`. Pendente de decisão concreta: só faz sentido se o Unscripted for rodar em produção GCP real. Como projeto de portfólio local/VPS, AI Studio basta. Não bloqueia v2.
- **Fase 2 — Cross-provider por agente** (ver `PLANO_IMPLEMENTACAO_V2.md`). Permitir `LLM_PROVIDER_REASONING=openai` + `LLM_PROVIDER_NARRATIVE=groq` (mistura entre providers). Pendente dos resultados de uso real: só vira necessária se nenhum provider único servir bem em REASONING **e** NARRATIVE. Hoje, OpenAI e Groq cobrem ambos os propósitos satisfatoriamente.
- **Provider alternativo de TTS** (ElevenLabs, Azure Speech). Pode ser bloco futuro se a qualidade do `gpt-4o-mini-tts` desapontar em uso prolongado. Mesmo padrão: nova classe implementando `TtsProvider`, env var nova, sem tocar no resto.
- **Voz por NPC.** Vozes diferentes para narrador vs NPCs específicos. O frontend já recebe `npc_id` no `npc_chunk` — basta o backend escolher a voz por NPC. Fora de escopo da Fase Voz; possível bloco futuro.
- **Cache de TTS por frase.** Frases muito repetidas (`"Você não consegue."`) poderiam ser cacheadas. Otimização de custo, não justifica complexidade hoje.
