# ARQUITETURA — Documento de Arquitetura Técnica

**Projeto:** Unscripted
**Status:** Planejamento — pré-implementação
**Documentos relacionados:** `PRD.md` (o quê e por quê), `DECISOES.md` (histórico das decisões)

> Este documento descreve **como** o sistema é construído. É a principal referência de implementação. Tudo aqui serve à v1, salvo onde indicado; itens de v2/v3+ aparecem como "ganchos" — pontos onde a arquitetura é preparada para a expansão sem implementá-la.

---

## 1. Visão geral da arquitetura

O Unscripted é uma aplicação web conteinerizada com três grandes blocos:

1. **Frontend** — aplicação web (React/Vite/TypeScript) com as três zonas de interface. Não fala com o LLM diretamente; conversa apenas com o backend.
2. **Backend** — aplicação Python (FastAPI) que expõe a API do jogo, orquestra os agentes de IA (Google ADK), roda o motor de regras determinístico, e faz RAG.
3. **Persistência** — uma única instância de Postgres (com extensão pgvector) que guarda o estado do jogo, as sessões dos agentes, e os vetores do RAG.

Tudo é orquestrado por **Docker Compose**. A única dependência externa é a chamada ao **Gemini 2.5 Flash** via API do Google AI Studio.

```
┌─────────────┐      HTTP/SSE      ┌──────────────────────────────┐
│  Frontend   │ ◄───────────────► │          Backend             │
│ React/Vite  │                   │  FastAPI + ADK + Regras+RAG  │
└─────────────┘                   └──────────┬───────────┬───────┘
                                             │           │
                                   ┌─────────▼──┐   ┌────▼─────────────┐
                                   │ Postgres + │   │ Gemini 2.5 Flash │
                                   │  pgvector  │   │  (AI Studio API) │
                                   └────────────┘   └──────────────────┘
                                  (no Docker Compose)  (única dep. externa)
```

## 2. Princípios de arquitetura

Estes princípios são vinculantes. Toda decisão de implementação deve respeitá-los.

### 2.1. Fronteira determinístico / LLM
É a **tese central** do projeto. As responsabilidades são divididas em duas pilhas:
- **Determinístico (código puro):** rolar dados, calcular dano, rastrear HP, comparar uma rolagem com uma dificuldade, inventário, progressão, qualquer aplicação de regra. É previsível, testável e exige determinismo.
- **LLM:** interpretar a intenção em linguagem livre, arbitrar (definir os *termos* de um teste — qual perícia, por que a dificuldade é alta), narrar, interpretar NPCs, improvisar dentro de um mundo coerente.

Quando uma ação exige os dois, o padrão é: **o LLM propõe (de forma estruturada), o código valida e aplica.** Nunca o LLM mutando estado diretamente. Essa fronteira é também uma defesa de segurança e a base da testabilidade.

Analogia que orienta o design: numa mesa real, **o livro de regras é o motor determinístico; o cérebro do mestre é o LLM**. O mestre consulta o livro e arbitra — ele não *é* o livro.

### 2.2. Complexidade proporcional (anti-over-engineering)
**Cada peça de complexidade precisa pagar o próprio aluguel.** Uma abstração, uma camada, um padrão, uma dependência só entra se resolve um problema que o projeto **realmente tem hoje** — não um problema imaginado para "um dia".

- O princípio **não é** minimizar linhas de código. Contar linhas é métrica ruim. Código seguro e claro às vezes é mais longo.
- O princípio **é**: código proporcional ao problema — tão complexo quanto o problema exige, e nem um pouco mais.
- Teste para qualquer abstração: *"o problema que isto resolve existe hoje, ou estou imaginando que pode existir?"* Se é imaginado, não entra.
- **Segurança e clareza nunca são over-engineering** — pagam o aluguel sempre, porque o código é público e vai para produção.
- A camada de providers (2.4) paga o aluguel: resolve um problema concreto e já identificado. Criar *duas* implementações dela agora "porque um dia" seria over-engineering — cria-se uma, deixa-se a porta aberta.

### 2.3. Portabilidade
A aplicação roda **idêntica** em desenvolvimento local e em VPS. O mesmo `docker-compose.yml` sobe nos dois ambientes; só mudam as variáveis de ambiente. Não existe "versão local" e "versão de produção" do código — existe um código portável e dois ambientes de deploy.

### 2.4. Camada de providers para dependências externas
Toda dependência externa (LLM, modelo de embedding, voz) fica **atrás de uma interface** (um "provider"). O resto do código nunca chama o Gemini ou um modelo de embedding diretamente — chama uma função própria (`gerar_narração(...)`, `gerar_embedding(...)`, etc.), e atrás dela há uma implementação selecionável por variável de ambiente.

Consequências:
- Trocar de provedor (ex.: AI Studio → Vertex AI) vira escrever um provider novo e mudar uma variável de ambiente — não tocar no projeto inteiro.
- O loop de turno, os agentes e o RAG não percebem qual provider está ativo.
- É o que destrava, sem custo hoje, os ganchos de v3+ (Vertex AI) e a flexibilidade de evolução.

## 3. Stack tecnológica

| Camada | Tecnologia | Observação |
|---|---|---|
| Linguagem do backend | **Python** | |
| Framework web | **FastAPI** | API do jogo, SSE para streaming da narração |
| Orquestração de agentes | **Google ADK** (Agent Development Kit) | multi-agente, `FunctionTool` |
| LLM | **Gemini 2.5 Flash** | via API do **Google AI Studio** (não Vertex AI) — única dependência externa |
| RAG — busca vetorial | **Postgres + extensão pgvector** | mesmo banco do estado do jogo |
| RAG — embeddings | **modelo de embedding local** | roda no container; custo de API zero |
| Banco de dados | **Postgres** | instância única: estado do jogo + sessões ADK + vetores RAG |
| Frontend | **React + Vite + TypeScript** | |
| Grafo de locações | **SVG** (lib leve de grafo, ex. React Flow) | renderizado a partir dos dados |
| Voz (interface na v1) | provider abstraído | implementação STT/TTS é v2 |
| Infraestrutura | **Docker Compose** | orquestra backend + Postgres |
| Licença do código | **Apache 2.0** | ver `DECISOES.md` ADR-017 |

## 4. Arquitetura de agentes (Google ADK)

### 4.1. Por que ADK e por que `FunctionTool` (não MCP)
O ADK é um framework code-first para orquestração de agentes, otimizado para Gemini mas model-agnostic. As ferramentas dos agentes são implementadas como **`FunctionTool`** do próprio ADK — funções Python que o agente pode chamar. **MCP foi avaliado e descartado** para este projeto (ver `DECISOES.md`, ADR-005): as ferramentas do Mestre (rolar dados, ler/escrever estado, consultar tabelas) são internas ao backend, e `FunctionTool` resolve isso de forma mais simples e direta, sem a sobrecarga de conexões stateful que o MCP introduz. A camada de providers (2.4) já dá a flexibilidade de troca que se poderia querer.

### 4.2. Os agentes
A divisão em múltiplos agentes se justifica por motivos concretos — contratos de saída diferentes, escopo de ferramentas/RAG diferente por agente, e testabilidade — e **não** por "porque o ADK permite". A divisão:

- **GameMaster (orquestrador)** — função Python (`runner_turn.process_turn`), **não** um agente ADK. Recebe a ação do jogador e o estado da sessão, conduz o turno chamando cada agente individualmente e intercalando etapas determinísticas. A decisão de não usar `LlmAgent`/`BaseAgent`/`SequentialAgent` para a orquestração está em `DECISOES.md` (ADR-035): "pular rolagem", "aplicar consequência", "chamar NPC condicionalmente" são decisões de fluxo, não de julgamento — pertencem a código, não a um agente.

- **`RefereeAgent`** (Árbitro) — recebe a ação, consulta as **regras** via RAG, e emite um **ruling estruturado** (objeto tipado, não prosa) — algo como `{precisa_rolagem: bool, perícia: str, dificuldade: int, consequências: {sucesso, falha}}`. Escreve o resultado no estado da sessão.

- **`NarratorAgent`** (Narrador) — lê o ruling + o resultado dos dados + o estado do mundo, consulta o **lore** via RAG, e produz a narração em linguagem natural. Escreve a narração no estado da sessão.

- **`NPCActorAgent`** (Intérprete de NPC) — quando há NPCs na cena que precisam reagir, gera as reações em personagem. A persona do NPC ativo é **injetada do estado** na instrução do agente — um único agente interpreta qualquer NPC, em vez de um agente por NPC (mais barato e escalável).

- **Mutação de estado** — **não é um agente.** É código determinístico. O LLM (via Referee/Narrator) *propõe* mudanças estruturadas; o código as *valida e aplica*. Ver 2.1.

A comunicação entre agentes se dá pelo estado da sessão (`session.state` no ADK) — os agentes leem e escrevem no mesmo contexto de invocação.

### 4.3. Fluxo do loop de turno

```
Ação do jogador (texto livre)
        │
        ▼
┌───────────────────┐
│ Validação de      │  ← determinístico. Barra ações impossíveis,
│ entrada / robustez│    abusivas, conteúdo proibido → aviso vermelho,
└─────────┬─────────┘    turno não consumido (ver PRD §8)
          │ (ação válida)
          ▼
┌───────────────────┐
│  GameMasterAgent  │  orquestra as etapas abaixo
└─────────┬─────────┘
          ▼
┌───────────────────┐
│   RefereeAgent    │  consulta REGRAS via RAG → emite ruling estruturado
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Resolução dados  │  ← determinístico (FunctionTool de dados)
│  (se ruling pede) │    rola, compara com a dificuldade
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Aplicação de      │  ← determinístico. Atualiza HP, inventário,
│ consequências     │    localização, flags. Valida antes de aplicar.
└─────────┬─────────┘
          ▼
┌───────────────────┐
│   NarratorAgent   │  consulta LORE via RAG → narração em linguagem natural
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  NPCActorAgent    │  (se há NPCs reagindo na cena)
└─────────┬─────────┘
          ▼
Resposta ao frontend: narração + estado atualizado + "pensamento do mestre"
```

Cada etapa de LLM e cada decisão determinística é registrada (ver §15, Observabilidade) e alimenta o painel de "pensamento do mestre".

## 5. Motor de regras determinístico

Módulo de código puro, sem nenhuma chamada de LLM, responsável por toda a mecânica do jogo:
- Parsing e rolagem de notação de dados (ex.: `2d6+3`, vantagem/desvantagem).
- Comparação de rolagem contra dificuldade.
- Cálculo de dano, atualização de HP.
- Aplicação de consequências mecânicas.
- Inventário e (v2+) progressão.

Exposto aos agentes como `FunctionTool`(s) do ADK. É a parte mais testável do sistema (ver §16) e a base da fronteira determinístico/LLM.

## 6. RAG (Retrieval-Augmented Generation)

### 6.1. Conceitos — para evitar confusão
- **Embedding** é uma operação: transformar um texto num vetor de números que representa o seu significado. Textos com sentido parecido geram vetores próximos. Quem faz isso é o **modelo de embedding**.
- **RAG** é a técnica completa, em três etapas: (1) **buscar** os trechos relevantes de um corpus, (2) **inserir** esses trechos no prompt, (3) **gerar** a resposta do LLM já com aquele contexto.
- **RAG usa embeddings** — não são sinônimos. Embedding é a peça; RAG é a máquina inteira.
- **pgvector** é a extensão do Postgres que guarda os vetores e calcula a proximidade entre eles — é o *lugar* onde a etapa de busca acontece.

Fluxo: `modelo de embedding transforma texto em vetor → pgvector guarda os vetores e faz a busca por proximidade → os trechos achados entram no prompt → Gemini gera a resposta.`

### 6.2. Implementação
- **Embeddings:** modelo de embedding **local** (open-source, ex. via `sentence-transformers`), rodando dentro do container. Custo de API: **zero**. Mantém a superfície externa do projeto mínima (só o Gemini sai para fora).
- **Busca vetorial:** **Postgres + pgvector**. Não há banco vetorial separado — os vetores ficam no mesmo Postgres que guarda o estado do jogo e as sessões. Uma peça de infraestrutura, não três.
- Tanto o modelo de embedding quanto o LLM ficam atrás da camada de providers (2.4).

### 6.3. Os dois corpora
O RAG serve a duas necessidades distintas, com corpora separados (ou um único store com filtro por metadados):
- **Corpus de regras** — consultado pelo `RefereeAgent`. Conteúdo: as regras do SRD 5.1. Objetivo: que as decisões de regra sejam fundamentadas no texto real, não na memória difusa do modelo (reduz regra alucinada).
- **Corpus de lore** — consultado pelo `NarratorAgent`. Conteúdo: o lore / setting bible da campanha, e o conteúdo dos capítulos. Objetivo: consistência narrativa.

A indexação (chunk + embed) de cada corpus acontece **uma vez** (no setup / ao adicionar conteúdo), não a cada turno. Por turno, só a frase curta do jogador é transformada em vetor para a busca.

## 7. Camada de providers

Interfaces que isolam as dependências externas. Implementações selecionadas por variável de ambiente.

| Provider | Implementação v1 | Implementação v2 (Fase 1) | Ganchos futuros |
|---|---|---|---|
| **LLM** | Gemini 2.5 Flash via AI Studio API | + **Groq** (via LiteLlm) + **OpenAI** (via LiteLlm), com **split por agente** (REASONING / NARRATIVE) — ADR-045 | provider Vertex AI (v3+) |
| **Embedding** | modelo local no container | (sem mudança) | provider de embedding via API (Google etc.) |
| **Voz (STT/TTS)** | interface definida; implementação stub na v1 | (sem mudança — fase futura da v2) | implementação concreta na v2 |

Nenhum código de domínio (loop de turno, agentes, RAG) referencia um provedor concreto.

**Sobre o split por agente (v2 Fase 1).** Cada provider declara dois modelos: `*_MODEL_REASONING` (Referee — output estruturado) e `*_MODEL_NARRATIVE` (Narrator/NPC — streaming de prosa). O método `build_model(purpose)` despacha por propósito. Se `NARRATIVE` é omitido, faz fallback para `REASONING` (comportamento single-model preservado para Gemini/OpenAI). No Groq, o split aproveita as quotas distintas — `llama-3.3-70b-versatile` (1K RPD) para REASONING e `llama-3.1-8b-instant` (14.4K RPD) para NARRATIVE — sem gargalo único. Detalhes em `docs/PROVIDERS.md`.

## 8. Modelo de estado do jogo

O estado de uma partida é uma entidade persistente e **identificável e isolada por sessão** — isso é decisão de arquitetura, e é também o gancho que torna acoplável, no futuro, uma "sala com ID compartilhável" (multiplayer v3+) sem reescrita. Componentes:

- **Sessão / partida:** ID (anônimo na v1), idioma, **história e capítulo atuais** (não só "capítulo" — é o que permite várias histórias coexistirem), timestamps.
- **Personagem:** atributos, HP atual/máximo, nível, perícias, classe (Guerreiro/Paladino na v1).
- **Inventário:** itens possuídos.
- **Localização atual:** nó do grafo de locações onde o personagem está.
- **Flags de progresso:** estado de objetivos/quests, eventos já ocorridos, locações já reveladas.
- **Estado oculto:** informação do mundo que o jogador não vê (ver PRD §2). Vive no estado mas não é exposto ao frontend.
- **Histórico:** o registro do que aconteceu, para coerência narrativa e para retomada de partida.

Persistido no Postgres. As sessões dos agentes ADK também são persistidas (o ADK oferece serviço de sessão com banco de dados) — no mesmo Postgres.

## 9. Grafo de locações

- Estrutura de dados: nós (locações) + arestas (passagens). **Não** é imagem nem arte.
- **Derivado do formato estruturado de aventura** (§10): ao escrever um capítulo, define-se as locações e suas conexões; o grafo é esses dados renderizados.
- Renderizado no frontend como SVG. Os nós se revelam progressivamente conforme explorados; a posição atual é destacada.
- Não há etapa separada de "criar o mapa" — escrever o capítulo já cria o grafo.

## 10. Formato estruturado de aventura

É a **decisão de design mais central depois da fronteira determinístico/LLM**. Um esquema (YAML ou JSON) que descreve um capítulo de forma estruturada. O sistema *roda* esse formato; o autor (humano, com auxílio de IA) *escreve* nesse formato. Ele é a ponte entre conteúdo, motor e interface.

A anatomia do formato é extraída da anatomia dos módulos de RPG publicados (engenharia reversa de one-shots — ver `DECISOES.md` ADR-018 e a lista de referência abaixo). Campos típicos:

- **Premissa / gancho** — o objetivo da aventura.
- **Background** — o que realmente está acontecendo (informação de Game Master, estado oculto).
- **Locações / cenas** — cada uma com: descrição, texto de abertura (o "ler em voz alta"), o que/quem está presente, e as conexões com outras locações (→ alimenta o grafo).
- **NPCs** — nome, personalidade, motivação, o que sabem, ficha/atributos, estado oculto (ex.: "veterano contra emboscadas").
- **Encontros** — combate ou social, com gatilhos ("quando o jogador entra, X acontece").
- **Itens / tesouro / recompensas.**
- **Ramificações** — o que muda conforme as escolhas do jogador.
- **Condições de progresso** — o que marca o avanço e o gancho para o próximo capítulo.
- **Briefing de imagens** — para cada imagem que o capítulo precisa: descrição da cena, atmosfera, estilo e elementos. O sistema **não gera imagens**; este briefing é o que o autor leva para a ferramenta externa de geração (Nano Banana). Ver §12.

Cada capítulo escrito nesse formato é simultaneamente: conteúdo jogável, fonte do grafo de locações, e conteúdo indexável pelo RAG (corpus de lore).

### 10.1. Ciclo de vida do conteúdo

O motor **não conhece nenhuma história específica** — ele executa qualquer conteúdo escrito no formato de aventura. Histórias e capítulos são dado de entrada, não código. Múltiplas histórias coexistem nativamente; o que muda com o tempo é a quantidade de conteúdo, não o sistema.

O conteúdo segue um modelo híbrido (decisão registrada em `DECISOES.md` ADR-023):

1. **Arquivo versionado é a fonte de verdade.** Cada capítulo é um arquivo (YAML/JSON) em `content/` no repositório — versionado no Git, revisável, parte do projeto open-source.
2. **Ingerido para o Postgres na inicialização.** Um passo de ingestão carrega os arquivos de conteúdo para o banco. Esse passo é o **mesmo momento** em que o RAG indexa o conteúdo no corpus de lore — a etapa de "carregar conteúdo para o sistema" já existe por causa do RAG, e a ingestão de conteúdo a aproveita.
3. **Lido do banco em tempo de execução.** O jogo lê o conteúdo do Postgres durante a partida — rápido, e já prepara o terreno para um eventual editor de aventuras no futuro, sem implementá-lo agora.

Adicionar uma história nova = adicionar arquivos de conteúdo + rodar a ingestão. Zero código novo.

### 10.2. Arquivo do capítulo vs. RAG — papéis distintos

O arquivo do capítulo e o RAG podem conter o mesmo texto, mas resolvem problemas diferentes — **não confunda os papéis:**

- **O arquivo do capítulo é a verdade estruturada do "agora".** É uma estrutura que o motor **executa de forma determinística**: onde o jogador está, o que tem nesta cena, quais as conexões, qual o estado oculto desta locação. O código consome esses campos diretamente, como consome o HP. O motor *navega* o capítulo. É o "tabuleiro do jogo".
- **O RAG é recuperação por relevância de "conhecimento amplo".** Não executa nada — responde "quais trechos são relevantes para esta resposta?". Serve a duas coisas que o arquivo do capítulo não resolve: (a) as **regras** do SRD 5.1, grandes demais para o prompt e válidas para toda história — o `RefereeAgent` busca só os trechos relevantes à ação; (b) o **lore acumulado** que cresce com a campanha — o `NarratorAgent` busca o trecho específico (ex.: o NPC mencionado três capítulos atrás) para manter continuidade sem carregar a história inteira no prompt. É o "índice remissivo da enciclopédia".

O conteúdo do capítulo alimenta os dois, em papéis diferentes: como **arquivo estruturado**, é o tabuleiro que o motor navega; como **texto indexado no corpus de lore**, é material que o `NarratorAgent` consulta depois, quando aquele conteúdo já é "passado a ser lembrado" e não "o agora".

Teste mental: *"o sistema precisa ler isto de forma exata e previsível, agora?"* → arquivo do capítulo. *"o sistema precisa encontrar isto por semelhança, quando for relevante, dentro de um corpo grande de texto?"* → RAG.

## 11. Camada de API (FastAPI)

O backend expõe a API do jogo. O ADK tem integração FastAPI nativa, mas o projeto envolve endpoints próprios. Endpoints v1:

- `POST /campaigns` — inicia uma nova partida (cria a sessão, retorna o ID anônimo).
- `POST /campaigns/{id}/action` — processa um turno do jogador; transmite a narração via SSE (streaming).
- `GET /campaigns/{id}/state` — retorna o estado conhecido pelo jogador (ficha, inventário, localização, objetivos) — nunca o estado oculto.
- `GET /campaigns/{id}/log` — histórico da partida.
- `GET /campaigns/{id}/graph` — grafo de locações filtrado por `locations_revealed` + silhuetas das cenas ainda não exploradas (ADR-038, ADR-042).
- `GET /campaigns/{id}/turn/{n}/trace` — trace completo do turno N (ruling, retrieval, rolagem, consequência, narração, reação de NPC), consumido pelo painel "pensamento do mestre" (ADR-036).

Requisitos transversais da API: rate limiting, CORS configurado, validação de toda entrada, a chave do LLM nunca trafega para o frontend.

## 12. Frontend

### 12.1. Stack e estrutura
React + Vite + TypeScript. O grafo de locações em SVG (lib leve de grafo). O frontend conversa só com o backend.

### 12.2. As três zonas
Conforme PRD §6.4: zona de narração (centro), painel de estado (lateral), zona de cena/grafo. Mais o painel recolhível de "pensamento do mestre" (PRD §6.7) e o feedback de processamento (PRD §6.8).

### 12.3. Identidade visual
Princípio de design **vinculante**: a interface **não** pode ter cara de "sistema genérico de IA" / chat genérico. Deve ter uma **estética temática de RPG** — textura, um toque old-school de fantasia (pergaminho, tipografia serifada, bordas trabalhadas), com identidade visual derivada da história dos capítulos. React + Vite + TS são a base técnica, mas com uma **camada de design autoral por cima** — sem framework de componentes genérico ditando a aparência.

### 12.4. Feedback visual reativo
Conforme PRD §6.6 — toda a riqueza visual vem da reatividade da interface (CSS e transições leves), **zero assets gráficos**, **zero representação de personagens**. Reação de dano, rolagem de dado visível, transições no grafo, fluxo de texto com ritmo, destaque de momentos-chave.

### 12.5. Imagens dos capítulos
- O sistema **não gera imagens**. A geração é feita externamente pelo autor (ferramenta Nano Banana).
- O papel do projeto: o formato de aventura (§10) inclui um **briefing de imagem** por imagem necessária. O design de cada capítulo entrega esses briefings.
- A implementação das imagens no frontend acontece **junto com o desenvolvimento do frontend** (não numa fase separada no fim) — o capítulo 1 já precisa delas.
- As imagens são ilustração de cena (a taverna, a floresta, o cavaleiro) — **não** são o mapa. O mapa é sempre o grafo SVG derivado dos dados.

### 12.6. Interface de voz
A interface de voz (botão de gravar, etc.) existe na v1; a implementação de STT/TTS é v2. Atrás do provider de voz (§7).

## 13. Persistência

- **Postgres único**, no Docker Compose, com a extensão **pgvector**.
- Guarda: estado do jogo (§8), sessões dos agentes ADK, e os vetores do RAG (§6).
- Uma peça de infraestrutura para três necessidades — coerente com o princípio de complexidade proporcional.

## 14. Infraestrutura e portabilidade

- **Docker Compose** orquestra: o container do backend (Python/FastAPI/ADK + motor de regras + RAG + modelo de embedding local) e o container do Postgres+pgvector.
- O mesmo `docker-compose.yml` roda em desenvolvimento local e em VPS. Diferença entre ambientes: apenas variáveis de ambiente.
- Única comunicação para fora do ambiente: a chamada ao Gemini 2.5 Flash (AI Studio API).

## 15. Segurança

O código é público e roda em VPS. Requisitos:

- **Segredos:** chaves de API e afins **nunca** versionados. `.env` no `.gitignore`; `.env.example` versionado, documentando as variáveis necessárias sem valores reais.
- **Chave do LLM:** vive só no backend. O frontend nunca a recebe nem a usa.
- **Injeção de prompt como vetor de ataque real:** toda entrada do jogador é texto livre destinado a um LLM. Mitigação em duas frentes: (a) validação determinística de entrada antes de chegar aos agentes (barra ações abusivas — PRD §8.2), e (b) instruções de robustez nos prompts dos agentes (o Game Master se mantém no papel e no escopo).
- **Saída do LLM validada e sanitizada** antes de qualquer aplicação ao estado. O LLM **propõe** mudanças estruturadas; o código determinístico **valida e aplica** — nunca o LLM mutando estado direto. Isso é a fronteira determinístico/LLM funcionando como defesa de segurança.
- **Rate limiting** nos endpoints.
- **CORS** configurado corretamente.
- **Estado nunca corrompido:** falha de dependência externa (LLM) não pode deixar o estado do jogo num estado inválido (ver §17 e PRD §7.7).
- Quando contas de usuário entrarem (v3+), autenticação e proteção de dados pessoais passam a ser requisitos de segurança explícitos e adicionais.

## 16. Observabilidade e logs

- O sistema registra as decisões dos agentes: o ruling do Referee, o resultado das rolagens, o que cada agente retornou, e os trechos recuperados pelo RAG.
- Esses registros alimentam o **painel de "pensamento do mestre"** no frontend (PRD §6.7) e servem de base para depuração.
- Para um sistema de IA, conseguir ver *por que* o Game Master decidiu algo é metade do trabalho de debug. É barato de implementar e é boa prática de AI Engineering.

## 17. Estratégia de testes

Duas frentes, correspondendo à fronteira determinístico/LLM:
- **Testes determinísticos convencionais** para o motor de regras: rolagem, cálculo de dano, aplicação de consequências, transições de estado. É a parte mais testável do sistema.
- **Eval set para os agentes:** um conjunto de casos "ação do jogador → ruling esperado" para testar o comportamento do `RefereeAgent` de forma sistemática. O ADK oferece suporte a avaliação. Demonstrar avaliação sistemática de comportamento de agente é um diferencial de portfólio.
- Tratamento de erro (falha do LLM, timeout) também é coberto: o estado não corrompe, a mensagem do jogador não se perde, o turno não é consumido.

## 18. Estrutura de pastas

Separação clara entre backend e frontend, com estrutura interna padronizada — o suficiente para consistência, sem burocracia. Esboço de referência:

```
unscripted/
├── README.md
├── LICENSE                     # MIT ou Apache 2.0
├── CONTRIBUTING.md
├── .env.example                # variáveis documentadas, sem valores reais
├── .gitignore                  # inclui .env
├── docker-compose.yml
├── docs/
│   ├── PRD.md
│   ├── ARQUITETURA.md
│   └── DECISOES.md
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── app/
│       ├── main.py             # entrypoint FastAPI
│       ├── api/                # rotas + schemas (Pydantic)
│       ├── agents/             # GameMaster, Referee, Narrator, NPCActor
│       │   └── prompts/        # templates de instrução dos agentes
│       ├── rules/              # motor de regras determinístico
│       ├── rag/                # ingestão (chunk+embed) e retrieval
│       ├── providers/          # camada de providers: llm, embedding, voz
│       ├── state/              # modelo de estado do jogo
│       ├── runner.py           # wiring do Runner ADK + serviço de sessão
│       └── i18n/               # infraestrutura de internacionalização
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   └── src/
│       ├── components/         # zonas de interface, painel, grafo
│       ├── styles/             # identidade visual temática de RPG
│       └── i18n/               # textos por idioma (só pt na v1)
├── content/
│   ├── srd/                    # regras SRD 5.1 (CC-BY 4.0) — corpus de regras
│   └── chapters/
│       └── chapter-01/         # capítulo 1 no formato estruturado de aventura
└── tests/
    ├── rules/                  # testes determinísticos do motor de regras
    └── evals/                  # eval set dos agentes
```

## 19. Internacionalização

- A **arquitetura** de i18n entra na v1: nenhum texto de interface ou de sistema fica engessado no código; tudo passa por uma camada de textos por idioma.
- Na v1, só o **português** é populado. O **inglês** e a troca de idioma são v2 — popular outro idioma é trabalho de conteúdo que não exige mudança arquitetural.
- O idioma é parte do estado da sessão (§8).
- A camada de regras referencia o SRD 5.1 (texto oficial em inglês); narração e conteúdo de aventura são no idioma da partida.

## 20. Ordem de build (fases)

Construir em **fatias verticais que sempre rodam** — nunca uma camada horizontal inteira de cada vez.

1. **Esqueleto** — FastAPI + Runner ADK + um único `NarratorAgent` com sessão em memória. O jogador manda texto e recebe narração. Sem regras, sem RAG, sem multi-agente. Prova o loop de ponta a ponta.
2. **Persistência e estado** — Postgres no Docker Compose, modelo de estado, sessão persistida, salvar/retomar por ID.
3. **Motor de regras** — o módulo determinístico (dados, HP, consequências) exposto como `FunctionTool`.
4. **RAG** — ingestão do SRD e do conteúdo do capítulo 1; embedding local; busca via pgvector; retrieval ligado aos agentes.
5. **Multi-agente** — separar em `RefereeAgent` → resolução → aplicação → `NarratorAgent` → `NPCActorAgent`, com o `GameMasterAgent` orquestrando. Regras de robustez e validação de entrada.
6. **Frontend** — as três zonas, o grafo, o painel de "pensamento do mestre", o feedback visual reativo, a identidade visual temática, a interface de voz (stub), as imagens do capítulo 1 (briefings → geração externa → integração).
7. **Validação e polish** — eval set dos agentes, tratamento de erros, critérios de aceitação da v1 (PRD §10), README/LICENSE/CONTRIBUTING.

Depois da v1 fechada e validada, os próximos capítulos e as funcionalidades de v2 são **acoplados** ao sistema-base — não exigem reescrita, porque a v1 é um todo coerente.

## 21. Licenciamento (resumo técnico)

Detalhamento e justificativa no `DECISOES.md` (ADR-017). Resumo:
- **Código** → **Apache 2.0**.
- **Camada de regras** → derivada do **SRD 5.1**, sob **Creative Commons CC-BY-4.0**: uso livre, inclusive comercial, inclusive em repo público, exigindo a declaração de atribuição padrão da Wizards of the Coast (incluída no README e num arquivo `NOTICE`).
- **Conteúdo de aventura** (capítulos, história, locações, NPCs) → **original**, escrito para o projeto. Repositório fica livre de dependências de licença de terceiros para conteúdo.
- **Sites de RPG de referência** → usados apenas como **estudo de estrutura** e material de teste **privado** durante o desenvolvimento; o conteúdo deles **não** é versionado nem embutido no produto. Lista em `DECISOES.md` ADR-018.
