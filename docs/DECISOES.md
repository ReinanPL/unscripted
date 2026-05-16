# DECISÕES — Registro de Decisões de Arquitetura (ADR)

**Projeto:** Unscripted
**Documentos relacionados:** `PRD.md` (o quê e por quê), `ARQUITETURA.md` (como)

> Este documento preserva **o raciocínio**, não só as conclusões. Cada entrada registra o contexto, as alternativas consideradas, a decisão tomada e suas consequências. É a memória do projeto — serve para que, semanas depois, ninguém reabra uma discussão já encerrada nem esqueça por que algo foi decidido. Novas decisões, tomadas durante a implementação, devem ser adicionadas aqui.

**Formato de cada entrada:** Contexto · Opções consideradas · Decisão · Consequências.

---

## ADR-001 — Gênero: RPG narrativo textual, não CRPG

**Contexto.** Era preciso definir que tipo de jogo o Unscripted é. Havia a dúvida de over-engineering: usar IA para algo que um motor de regras determinístico faria melhor e mais barato.

**Opções consideradas.**
- Um CRPG: navegação por grid, menus de ação fixos, combate com opções pré-definidas — resolvido por um motor de regras determinístico, com pouca ou nenhuma IA.
- Um RPG narrativo textual: o jogador descreve livremente o que tenta fazer, e a IA arbitra e narra.

**Decisão.** RPG narrativo textual — um "livro-jogo conversacional". A IA ocupa o papel de Game Master (árbitro-narrador).

**Consequências.** É o único gênero em que a IA é o motor do jogo e não um enfeite. RPG de mesa é nativamente um meio textual; construir nesse meio é usar a tecnologia onde ela é forte. Decisões decorrentes: o visual é modesto e textual (ADR-016), e o esforço de engenharia se concentra na orquestração de IA, que é o ponto do portfólio.

---

## ADR-002 — O Game Master como árbitro-narrador multi-agente

**Contexto.** Definir o que o "Game Master" é, conceitual e tecnicamente.

**Opções consideradas.**
- Um único LLM bem promptado fazendo tudo.
- Um sistema multi-agente com papéis especializados.

**Decisão.** Sistema multi-agente: um orquestrador (`GameMasterAgent`) coordenando um Árbitro (`RefereeAgent`), um Narrador (`NarratorAgent`) e um Intérprete de NPC (`NPCActorAgent`). A mutação de estado **não** é um agente — é código determinístico.

**Consequências.** A divisão se justifica por motivos concretos: contratos de saída diferentes (ruling estruturado vs. prosa), escopo de ferramentas/RAG diferente por agente, e testabilidade. **Não** se justifica por "porque o framework permite" — esse seria cargo cult. Risco reconhecido: multi-agente é o ponto onde mora o risco de over-engineering; a mitigação é começar simples (orquestrador como coordenador sequencial) e só adicionar complexidade condicional quando ela for necessária.

---

## ADR-003 — Fronteira determinístico / LLM

**Contexto.** Decidir o que é resolvido por código e o que é resolvido por LLM. É a questão que decide se o projeto é bem-feito ou over-engineered.

**Opções consideradas.**
- Deixar o LLM cuidar de tudo, inclusive cálculo e estado.
- Separar: motor de regras determinístico para a mecânica, LLM para julgamento e narração.

**Decisão.** Fronteira explícita. **Determinístico:** rolar dados, calcular dano, rastrear HP, comparar rolagem com dificuldade, inventário, progressão — toda aplicação de regra. **LLM:** interpretar intenção livre, arbitrar os termos de um teste, narrar, interpretar NPCs, improvisar dentro de um mundo coerente. Quando os dois se aplicam: o LLM **propõe** de forma estruturada, o código **valida e aplica**.

**Consequências.** É a tese central do projeto e o que demonstra senioridade — a habilidade não é "chamar um LLM", é saber o que **não** entregar a ele. É também a base da testabilidade e uma defesa de segurança. Analogia que guia o design: o livro de regras é o motor; o cérebro do mestre é o LLM.

---

## ADR-004 — Stack base: Python + FastAPI + Google ADK

**Contexto.** Escolher a stack do backend. O projeto começou da vontade de usar Google ADK, FastAPI e (inicialmente) Vertex AI.

**Opções consideradas.** A stack foi amplamente definida pelo objetivo de portfólio do autor. (Nota: durante a conversa, transcrição por voz gerou "PyPi" e "Fetch API" — entende-se **Python** e **FastAPI**.)

**Decisão.** Backend em **Python**, framework web **FastAPI**, orquestração de agentes com **Google ADK**, usando `FunctionTool` para as ferramentas dos agentes.

**Consequências.** Stack coerente com o objetivo de portfólio. O ADK dá a orquestração multi-agente; o FastAPI dá a API e o streaming (SSE). Ver ADR-005 sobre a não-adoção de MCP.

---

## ADR-005 — MCP descartado; `FunctionTool` adotado

**Contexto.** O projeto inicialmente considerou usar MCP (Model Context Protocol) para as ferramentas dos agentes (rolar dados, ler/escrever estado).

**Opções consideradas.**
- MCP: um servidor (ex. FastMCP) expondo as ferramentas via protocolo, com os agentes como clientes.
- `FunctionTool` do ADK: as ferramentas como funções Python chamadas diretamente pelos agentes.

**Decisão.** Descartar MCP. Usar `FunctionTool` do ADK.

**Consequências.** As ferramentas do Unscripted são internas ao backend; não há serviço externo a integrar. MCP introduziria conexões stateful e sobrecarga de infraestrutura sem resolver um problema que o projeto tem. `FunctionTool` é mais simples e direto. A flexibilidade de troca que se poderia querer já é dada pela camada de providers (ADR-009). Decisão alinhada ao princípio de complexidade proporcional (ADR explícito em `ARQUITETURA.md` §2.2).

---

## ADR-006 — RAG com pgvector e modelo de embedding local

**Contexto.** O sistema precisa de RAG para fundamentar as decisões de regra (no texto real do SRD) e a narração (no lore). Era preciso decidir onde fazer a busca vetorial e como gerar os embeddings — com atenção a custo e ao desejo de manter a superfície externa mínima.

**Opções consideradas.**
- Busca vetorial: banco vetorial dedicado vs. Postgres + extensão pgvector.
- Embeddings: API de embedding do Google vs. modelo de embedding open-source rodando localmente.
- (Considerado e descartado: Vertex AI RAG Engine — ver ADR-008.)

**Decisão.** Busca vetorial com **Postgres + pgvector** (mesmo banco do estado do jogo). Embeddings com **modelo local** rodando no container.

**Consequências.** Custo de API de embedding: zero. A única dependência externa do projeto passa a ser a chamada do LLM. Uma só peça de infraestrutura de dados em vez de três. Tanto o modelo de embedding quanto o LLM ficam atrás da camada de providers (ADR-009), então trocar para uma API de embedding no futuro é um provider novo, não uma reescrita. Esclarecimento registrado: RAG ≠ embedding — RAG é a técnica completa (buscar, inserir, gerar), embedding é a peça que viabiliza a busca; pgvector é o lugar onde a busca acontece.

---

## ADR-007 — Banco de dados: uma instância única de Postgres

**Contexto.** O sistema tem três necessidades de persistência: estado do jogo, sessões dos agentes ADK, e vetores do RAG.

**Opções consideradas.**
- Bancos separados para cada necessidade.
- Uma instância única de Postgres (com pgvector) para as três.

**Decisão.** **Postgres único**, com a extensão pgvector, no Docker Compose.

**Consequências.** O ADK tem serviço de sessão com banco de dados, que aponta para o mesmo Postgres. pgvector cobre os vetores. Uma peça de infraestrutura, coerente com complexidade proporcional e com portabilidade (sobe junto no Docker Compose).

---

## ADR-008 — LLM: Gemini 2.5 Flash via AI Studio; Vertex AI adiada

**Contexto.** O LLM é o coração do loop de turno. Inicialmente cogitou-se Vertex AI — inclusive como item de portfólio para LinkedIn. Surgiram dúvidas sobre necessidade real, custo, e o desejo de rodar tudo de forma portável/local.

**Opções consideradas.**
- Gemini via Vertex AI (plataforma gerenciada do Google Cloud).
- Gemini via API do Google AI Studio (chave de API direta).

**Decisão.** **Gemini 2.5 Flash via API do Google AI Studio.** Vertex AI fica como **evolução futura mapeada** (v3+), implementável como um provider adicional na camada de abstração.

**Consequências.** Para o objetivo de portfólio, a Vertex AI adicionaria a *mesma* chamada de LLM e o *mesmo* embedding por um caminho diferente — não muda a arquitetura nem a parte difícil, e adiciona custo. O que demonstra senioridade no projeto (loop de turno, fronteira determinístico/LLM, RAG, multi-agente) não fica melhor com Vertex AI. Como a camada de providers (ADR-009) deixa "adicionar um provider Vertex AI" como exercício pequeno e isolado, isso vira um item de portfólio *melhor* no futuro ("sei abstrair provedores e implementei os dois") do que casar o projeto com a Vertex AI agora. Custo: o Gemini Flash é o único custo recorrente e é o modelo barato da linha; para desenvolvimento e demonstração, fica em poucos dólares, possivelmente dentro do tier gratuito do AI Studio.

---

## ADR-009 — Camada de providers para dependências externas

**Contexto.** O autor quer melhorar o sistema continuamente e poder trocar de provedores (ex.: migrar para Vertex AI antes de publicar, ou trocar o embedding). Era preciso decidir como evitar acoplar o código a um provedor concreto.

**Opções consideradas.**
- Chamar Gemini / embedding / voz diretamente no código de domínio.
- Isolar cada dependência externa atrás de uma interface ("provider"), selecionável por variável de ambiente.

**Decisão.** **Camada de providers** como princípio de arquitetura central. O código de domínio (loop de turno, agentes, RAG) chama funções próprias; atrás delas, implementações trocáveis. Providers na v1: LLM (AI Studio), embedding (local), voz (interface definida, implementação stub).

**Consequências.** Trocar de provedor vira escrever um provider novo + mudar uma variável de ambiente. Destrava sem custo hoje os ganchos de evolução (Vertex AI, embedding via API, voz). **Não é over-engineering:** resolve um problema concreto e já identificado. Seria over-engineering criar *duas* implementações agora "porque um dia" — cria-se uma, deixa-se a porta aberta.

---

## ADR-010 — Portabilidade via Docker Compose (não "aplicação local")

**Contexto.** O autor mencionou "rodar tudo localmente". Esclareceu-se depois que a intenção é rodar localmente durante o desenvolvimento e depois mover para uma VPS — ou seja, portabilidade, não "local para sempre".

**Opções consideradas.** Tratar o projeto como uma aplicação local; ou como uma aplicação portável conteinerizada.

**Decisão.** **Aplicação portável e conteinerizada.** O mesmo `docker-compose.yml` roda idêntico em desenvolvimento local e em VPS; só mudam as variáveis de ambiente.

**Consequências.** Não existe "versão local" e "versão de produção" do código — existe um código portável e dois ambientes de deploy. É o motivo de existir do Docker Compose no projeto. Toda a documentação usa "portável", não "local".

---

## ADR-011 — Escopo v1: single-player; multiplayer adiado

**Contexto.** Surgiu a ideia de jogar em grupo (ex.: 4 pessoas), inclusive online com salas por ID.

**Opções consideradas.**
- Implementar multiplayer (estado compartilhado em tempo real, sincronização, websockets, gestão de turnos) na v1.
- v1 single-player; multiplayer como evolução futura.

**Decisão.** **v1 é single-player.** Multiplayer local fica para v2; multiplayer online com sala/ID fica para v3+.

**Consequências.** Multiplayer é o maior salto de complexidade do projeto, e essa complexidade é encanamento de sistemas distribuídos — a parte que **menos** demonstra a habilidade central de AI Engineering. Implementá-lo na v1 deslocaria o esforço para longe do ponto do portfólio e arriscaria não terminar nada. Gancho de arquitetura registrado (ADR-013 e `ARQUITETURA.md` §8): o estado de jogo nasce como entidade identificável e isolada por sessão, o que torna uma futura "sala com ID" acoplável sem reescrita — sem implementar nada agora.

---

## ADR-012 — Personagem: pré-prontos na v1; criação adiada

**Contexto.** Definir como o jogador obtém um personagem.

**Opções consideradas.** Tela de criação de personagem na v1; ou personagens pré-prontos.

**Decisão.** Na v1, **dois personagens pré-prontos: Guerreiro e Paladino**, com fichas completas definidas no conteúdo. Criação de personagem (escolher raça, classe, distribuir atributos) é v2.

**Consequências.** Criação de personagem é um subsistema inteiro que não demonstra nada de IA e adiaria o que importa. Pré-prontos destravam o jogo imediatamente. A criação é fiel ao gênero e entra na v2 ("a mesa completa").

---

## ADR-013 — Autenticação: anônima por ID na v1; contas adiadas

**Contexto.** "Salvar e continuar" exige identificar o jogador. O autor inicialmente considerou contas com login importantes para o usuário salvar o progresso.

**Opções consideradas.**
- Contas de usuário com login (cadastro, senha/OAuth, recuperação) na v1.
- Identificação anônima por ID de sessão na v1.

**Decisão.** **Anônima por ID de sessão na v1.** Sem cadastro, sem e-mail, sem senha. Contas de usuário com login vão para v3+ ("a plataforma").

**Consequências.** Distinção esclarecida: o que o jogador *precisa* é **retomar o progresso** (o fim); "login" é apenas *um meio*. Anônimo-por-ID entrega o mesmo fim — o jogo gera um ID, o jogador retoma por ele. Conta de usuário adiciona armazenamento de dados pessoais (LGPD, política de privacidade) e uma superfície de ataque de autenticação inteira — peso real num repo público mantido por uma pessoa. Adiar não é "pensar baixo": é fazer a feature de conta **bem**, na hora certa, em vez de empurrá-la para a v1 sob pressão de "parecer mais completo". A v1 não coleta nenhum dado pessoal.

---

## ADR-014 — Voz: interface na v1; implementação na v2

**Contexto.** O autor quer comando de voz (jogador fala o turno; o mestre pode narrar em áudio). Discutiu-se se isso seria fase futura ou implementado junto com o backend.

**Opções consideradas.**
- Implementação completa de STT/TTS na v1.
- Apenas a interface de voz na v1, implementação na v2.
- (Sub-decisão: STT/TTS local vs. via API.)

**Decisão.** **Interface de voz na v1** (o provider de voz é desenhado, a UI de gravação existe); **implementação concreta de STT/TTS na v2.** Dá para jogar digitando enquanto isso.

**Consequências.** A capacidade entra na v1 via camada de providers; a implementação completa pode começar a v2 sem prejuízo, porque o jogo é jogável por texto. Mesmo padrão de ADR-015: a arquitetura da capacidade entra cedo, a implementação completa pode esperar.

---

## ADR-015 — Internacionalização: arquitetura na v1; só português populado

**Contexto.** O autor quer que a aplicação não fique engessada em português — deseja seleção de idioma (português, inglês).

**Opções consideradas.** Implementar múltiplos idiomas completos na v1; ou apenas a arquitetura de i18n na v1, com um idioma populado.

**Decisão.** **Arquitetura de i18n na v1** (nenhum texto engessado no código). Na v1, **só o português** é populado. Inglês e a troca de idioma são v2.

**Consequências.** Popular um segundo idioma é trabalho de conteúdo que não exige mudança arquitetural — logo, não bloqueia o jogo e pode esperar. O idioma é parte do estado da sessão. A camada de regras referencia o SRD 5.1 (texto oficial em inglês); narração e conteúdo de aventura são no idioma da partida.

---

## ADR-016 — Sem representação de personagem; feedback visual reativo na v1

**Contexto.** O autor levantou a ideia de elementos visuais: um "boneco" do Game Master, e animações de combate (personagens 2D lutando, efeitos de poder). A preocupação real e legítima: que a tela não fique "morta" e sem graça.

**Opções consideradas.**
- Representação visual de personagens e animação de combate 2D.
- Nenhum elemento visual além de texto.
- Feedback visual reativo via animação de UI, sem representação de personagens.

**Decisão.** **Sem "boneco" do Game Master** (ele não é um personagem — é a narração; representá-lo seria desenhar "o narrador" de um livro). **Sem sprites de personagem e sem animação de combate 2D/3D.** Em vez disso, **feedback visual reativo na v1**: a interface inteira reage ao estado do jogo via animação de UI (CSS e transições leves) — reação de dano, rolagem de dado visível, transições no grafo, fluxo de texto com ritmo, destaque de momentos-chave.

**Consequências.** Animação de combate exigiria assets gráficos (o autor não é designer), arrastaria licenciamento de assets, e exigiria um motor de jogo 2D com estado visual — deslocando o esforço para a parte que **não** demonstra AI Engineering. É o mesmo padrão do multiplayer (ADR-011). "Sem animação de personagem" **não** significa "tela morta": o espaço entre "boneco 2D lutando" e "tela parada" é exatamente o feedback visual reativo, que é barato, não depende de assets, e dá uma tela viva. Um terminal de ficção interativa bem-feito e reativo é mais elegante — e melhor num portfólio — que um RPG 2D meia-boca. Reconsideração só faria sentido numa versão muito amadurecida com orçamento de design real; horizonte distante, não escopo.

---

## ADR-017 — Licenciamento: SRD 5.1 (CC-BY) para regras; conteúdo original; MIT/Apache para o código

**Contexto.** O projeto será público e o autor quer poder usá-lo/comercializá-lo. Era preciso entender o que pode ser usado como base. Confusão a desfazer: dar crédito não é o que concede o direito de uso — a licença concede, e às vezes exige crédito como condição.

**Opções consideradas.**
- Usar aventuras gratuitas de sites de RPG como base/conteúdo.
- Usar o SRD para regras e escrever conteúdo de aventura original.

**Decisão.**
- **Código** → **Apache 2.0**. Escolhido sobre a MIT por ter cláusula explícita de concessão de patentes (protege o autor e os usuários de surpresas relacionadas a patentes) e por ser o padrão da indústria para projetos sérios de software, inclusive na área de IA — o que comunica profissionalismo num portfólio. A MIT seria mais curta, mas brevidade não é vantagem relevante aqui.
- **Camada de regras** → derivada do **SRD 5.1**, que está sob **Creative Commons CC-BY-4.0** (uso livre, inclusive comercial, inclusive em repo público, exigindo a declaração de atribuição padrão da Wizards of the Coast). É o "chão seguro" para as regras.
- **Conteúdo de aventura** (capítulos, história, locações, NPCs) → **100% original**, escrito para o projeto.

**Consequências.** Distinção central: **o SRD é um sistema de regras, não contém aventuras** — não tem história, masmorra pronta nem NPCs nomeados. As aventuras gratuitas de sites são "grátis para baixar e jogar", o que **não** é "livre para redistribuir ou comercializar"; cada uma tem licença própria, a maioria não permite embutir o conteúdo num produto. Escrever conteúdo original deixa o repositório livre de dependências de licença de terceiros, permite qualquer licenciamento, e é uma demonstração de habilidade mais forte. O único crédito de terceiro necessário no projeto final é a atribuição do SRD 5.1 (no README e num arquivo `NOTICE`). Estrutura e mecânica não são protegidas por copyright; texto específico é.

---

## ADR-018 — Conteúdo de aventura: curado e escrito, não gerado proceduralmente; sites como referência de estudo

**Contexto.** Era preciso decidir como o conteúdo de aventura é produzido, e qual o papel dos sites de RPG pesquisados.

**Opções consideradas.**
- Geração procedural de capítulos por IA.
- Conteúdo escrito e curado, usando os módulos publicados como referência de estrutura.

**Decisão.** Conteúdo de aventura **escrito e curado** (pelo autor, com auxílio de IA), seguindo o **formato estruturado de aventura** (`ARQUITETURA.md` §10). A anatomia desse formato é obtida por **engenharia reversa** de módulos publicados. Os sites de RPG são usados **apenas como estudo de estrutura e material de teste privado** — seu conteúdo não é versionado nem embutido no produto.

**Sites de referência (estudo de estrutura, não fonte de assets):**
- **Nat 1 Gaming** — coletânea de mais de 120 aventuras gratuitas, organizadas por nível/tier.
- **1Shot Adventures** — aventuras gratuitas acompanhadas do *design* por trás delas (útil para entender o porquê das escolhas estruturais).
- **Kassoon** — módulos gratuitos e geradores procedurais de one-shots.
- **Kobold Press ("Prepared!")** — coletânea de one-shots curtos para vários ambientes e níveis.
- **Lost Mine of Phandelver** (Wizards of the Coast) — aventura clássica, construída para ensinar a estrutura de um módulo.

**Consequências.** Geração procedural sem revisão foge ao controle de qualidade e contradiz a curadoria desejada. Os módulos publicados ensinam a *anatomia* de uma boa one-shot (premissa, background, locações com conexões, NPCs, encontros, itens, ramificações, condições de progresso) — e essa anatomia define os campos do formato de aventura, o data model do estado, e o conjunto de funcionalidades do jogo. O grafo de locações cai de graça desse formato. Aviso de licença registrado em ADR-017.

---

## ADR-019 — Regras de robustez do Game Master e política de conteúdo sensível

**Contexto.** O jogador escreve texto livre que vai para um LLM. É preciso lidar com: ações impossíveis / que quebram o jogo, tentativas abusivas / de injeção de prompt / fora de personagem, e tentativas de levar a narrativa para conteúdo proibido.

**Opções consideradas.** Deixar o LLM lidar com tudo via prompt; ou ter regras explícitas de robustez com validação e resposta de interface definidas.

**Decisão.** Seção de **regras de robustez do Game Master** (PRD §8) e **política de conteúdo sensível** (PRD §9). Em todos os três casos (ação impossível, tentativa abusiva, conteúdo proibido): o turno **não é consumido**, e a interface exibe um **aviso vermelho destacado** explicando o motivo; o jogador pode jogar de novo. Implementado em duas frentes — validação determinística de entrada e instruções de robustez nos prompts dos agentes.

**Consequências.** "O mundo resiste" — o Game Master nunca concede um resultado só porque foi pedido, e se mantém no papel e no escopo aconteça o que acontecer. Conteúdo permitido: violência de fantasia de livro de aventura. Proibido: gore gratuito, violência em nível muito alto, conteúdo sexual, temas pesados com necessidade de aviso. Conecta com a fronteira determinístico/LLM (o LLM propõe, o código valida) e com segurança (injeção de prompt como vetor de ataque real).

---

## ADR-020 — Tratamento de falhas externas sem perder a jogada

**Contexto.** O LLM é dependência externa e pode falhar, demorar ou exceder limites enquanto o jogador está num turno.

**Opções consideradas.** Deixar o erro propagar; ou tratar explicitamente preservando o turno e a entrada.

**Decisão.** Em caso de falha do LLM: a aplicação informa o jogador ("tivemos um problema no processamento, tente novamente"), **não consome o turno**, **não corrompe o estado**, e **não perde a mensagem (ou áudio) do jogador** — devolve ao estado anterior com a entrada preservada na caixa de envio.

**Consequências.** Pensar pelo lado do jogador: uma falha de infraestrutura não pode custar a jogada da pessoa. Coberto também pela estratégia de testes.

---

## ADR-021 — Roadmap organizado em três temas

**Contexto.** Muitas funcionalidades foram conscientemente adiadas. Era preciso uma forma de organizar o que entra em cada versão, em vez de listas soltas. Preocupação do autor: não "pensar baixo", mas também não estourar o escopo da v1.

**Opções consideradas.** Lista solta de "coisas futuras"; ou roadmap organizado por temas com identidade clara por versão.

**Decisão.** Roadmap em **três temas** (detalhado no PRD §11):
- **v1 — "O sistema-base jogável":** todo o sistema para um jogador, um personagem, um capítulo. Um jogo completo e jogável.
- **v2 — "A mesa completa":** aprofunda a fidelidade ao RPG de mesa, mantendo a natureza single-player e a arquitetura da v1 — multi-provider LLM com split por agente (ADR-044, ADR-045 — primeira entrega), grupo de múltiplos personagens, criação de personagem, descanso/recuperação, inventário com uso de itens, progressão entre capítulos, rolagem transparente, voz, segundo idioma, capítulo 2+.
- **v3+ — "A mesa compartilhada e a plataforma":** o que muda a natureza do sistema — contas de usuário, multiplayer online com sala/ID, suporte a Vertex AI, capítulos contínuos.

**Decisão de método associada:** a régua para decidir se algo é v1 é uma pergunta única — *"sem isto, dá para jogar o capítulo 1 do início ao fim?"* Se não, é v1; se sim, é v2+.

**Consequências.** Adiar com decisão **documentada** é planejamento sério, não "pensar baixo" — um escopo enxuto e terminado comunica mais senioridade que um escopo grande e pela metade. Cada salto de versão tem um tema claro, o que comunica capacidade de sequenciar um produto. A v2 inteira é "aprofundar sem mudar a natureza"; a v3+ é onde a natureza muda. É isso que torna a expansão "só acoplar": a v1 é um todo coerente e fechado.

---

## ADR-022 — Estrutura de três documentos

**Contexto.** O autor quer documentar tudo "como uma aplicação real sendo produzida" — requisitos, e o contexto/decisões da conversa de planejamento.

**Opções consideradas.** Um documento; dois documentos; três documentos.

**Decisão.** **Três documentos**, com públicos e ritmos de mudança diferentes:
- **`PRD.md`** — Documento de Requisitos do Produto: o quê e o porquê, agnóstico de implementação. Documento vivo, cresce a cada versão.
- **`ARQUITETURA.md`** — Documento de Arquitetura Técnica: o como. Principal referência de implementação.
- **`DECISOES.md`** — este documento: registro de decisões no formato ADR — contexto, alternativas, decisão, consequências.

**Consequências.** "PRD" é o termo padrão da indústria, não jargão. O `DECISOES.md` é o que preserva o raciocínio (não só a conclusão) e protege o projeto de reabrir discussões encerradas. Fluxograma: não é documento à parte — diagramas (loop de turno, fluxo do RAG) vivem dentro do `ARQUITETURA.md`. Novas decisões tomadas durante a implementação são adicionadas a este documento.

---

## ADR-023 — Ciclo de vida do conteúdo: arquivo versionado como fonte de verdade, ingerido para o banco

**Contexto.** Era preciso decidir onde o conteúdo de aventura (histórias, capítulos) mora — e confirmar que a arquitetura permite incrementar histórias e capítulos novos sem reescrita. Surgiu a dúvida: conteúdo no código-fonte ou no banco de dados?

**Opções consideradas.**
- **A — conteúdo versionado no repositório:** capítulos como arquivos YAML/JSON no Git. Simples, versionado, revisável; mas adicionar conteúdo exige deploy.
- **B — conteúdo no banco de dados:** capítulos como registros no Postgres. Adicionar conteúdo sem deploy, caminho para um editor; mas mais complexo agora e conteúdo deixa de ser naturalmente versionado.
- **C — híbrido:** arquivo no repositório como fonte de verdade, ingerido para o banco na inicialização; runtime lê do banco.

**Decisão.** **Opção C.** O conteúdo é arquivo versionado em `content/` (fonte de verdade), ingerido para o Postgres na inicialização — no **mesmo passo** em que o RAG indexa o conteúdo no corpus de lore. Em runtime, o jogo lê do banco.

**Consequências.** A etapa de "carregar conteúdo para o sistema" já existe por causa do RAG; a Opção C a aproveita, custando pouco a mais que a A e fechando menos portas. Ganha-se conteúdo versionado e revisável (bom para projeto público e para revisão com IA) **e** disponível no banco em runtime (rápido, e prepara terreno para um eventual editor de aventuras, sem implementá-lo agora). Confirmação importante: como o motor executa **qualquer** conteúdo no formato de aventura, múltiplas histórias e capítulos novos são **capacidade nativa** — adicionar história = adicionar arquivos + rodar a ingestão, zero código novo. A "história e capítulo atuais" passam a ser parte do estado da sessão (não só "capítulo"). Distinção relacionada, registrada no `ARQUITETURA.md` §10.2: o arquivo do capítulo é estrutura que o motor *executa* de forma determinística (o "tabuleiro"); o RAG é busca semântica por relevância (o "índice remissivo") — papéis distintos, não devem ser confundidos.

---

## ADR-024 — Skills do Claude Code como camada de método, complementar aos documentos

**Contexto.** Os três documentos podem ser grandes; há risco de a IA, na implementação, perder informação ou implementar de forma inconsistente. Surgiu a ideia de criar skills para o Claude Code.

**Opções consideradas.**
- Transformar o conteúdo dos documentos em skills.
- Não criar skills; confiar só nos documentos.
- Criar skills como uma camada **separada e complementar** aos documentos.

**Decisão.** Criar skills como **camada de método**, complementar — não substituta — dos documentos. **Os documentos descrevem o projeto (o quê); as skills descrevem o método (o como); as skills apontam para os documentos.** Cinco skills:
- `mestre-principios-do-projeto` — os princípios inegociáveis e as regras de "pare e cheque". A bússola contra drift. **Completa.**
- `mestre-fluxo-de-trabalho` — o ritmo de cada ciclo de implementação: planejar antes de codar, validar antes de commitar, commit por tarefa, lint e checagem de tipos via hook de pre-commit, registro de ADRs, atualização dos documentos e refinamento das skills de esqueleto. **Completa.**
- `mestre-criacao-de-historia` — método para escrever capítulos no formato de aventura. **Completa.**
- `mestre-backend` — método para o lado Python/FastAPI/ADK. **v0.1 esqueleto** — seções marcadas para refinar após as fases de build.
- `mestre-frontend` — método para o lado React/Vite/TS, com foco em identidade visual. **v0.1 esqueleto** — refinar após a Fase 6.

**Consequências.** Jogar o conteúdo dos documentos dentro de skills só duplicaria informação e criaria dois lugares para sincronizar — pior, não melhor. Skills boas são acionáveis e verificáveis, não redação motivacional. As duas skills cujo material é a conversa de planejamento (princípios e criação de história) nascem completas; as duas que dependem de aprendizado da implementação (backend e frontend) nascem como esqueleto sólido com seções explícitas de "refinar após a fase X" — assim não se perde o contexto atual nem se congela uma skill no escuro. Skills boas são destiladas de tropeço, não só de planejamento; os refinamentos devem ser preenchidos ao longo das fases e registrados aqui quando relevantes.

---

## ADR-025 — Schema do formato estruturado de aventura como modelo Pydantic

**Contexto.** O `ARQUITETURA.md` §10 descreve o formato estruturado de aventura conceitualmente (premissa, background, locações com conexões, NPCs com estado oculto, encontros com gatilhos, ramificações, condições de progresso, briefings de imagem). Mas o fato de o motor **executar** esse formato de forma determinística (e não interpretá-lo livremente — ver `ARQUITETURA.md` §10.2) exige um schema técnico concreto. Sem ele, "ler o arquivo do capítulo" vira interpretação ad hoc no código — cada lugar que toca o conteúdo precisa inventar como ler, e validar capítulos malformados se torna trabalho manual.

**Opções consideradas.**
- **A — JSON Schema puro:** define os campos e tipos num documento `.json`, valida com biblioteca externa.
- **B — Modelo Pydantic:** define os campos como classes Pydantic; validação automática; tipagem nativa no Python.
- **C — Schemaless (YAML/JSON livre):** o motor lê os campos por nome sem validação prévia.

**Decisão.** **Opção B — modelo Pydantic.** Cada elemento do formato (`Adventure`, `Chapter`, `Scene`, `NPC`, `Encounter`, `ImageBriefing`, `Connection`, `HiddenState`, etc.) é uma classe Pydantic. O conteúdo continua vivendo em arquivos YAML/JSON em `content/` (fonte de verdade, conforme ADR-023); a ingestão para o banco passa por validação Pydantic na carga.

**Consequências.**
- O backend já usa Pydantic para tudo (schemas de API, modelo de estado, ruling do Referee) — manter a mesma ferramenta para o formato de aventura é coerência, não complexidade nova.
- A validação automática na ingestão **barra capítulos malformados antes de entrarem no banco** — falha alto, falha cedo. Capítulo quebrado nunca chega ao motor em tempo de execução.
- A tipagem dá ao motor acesso direto e seguro aos campos, sem `dict[str, Any]` espalhado.
- O schema fica auto-documentado pelas próprias classes. Mudar o formato é uma decisão de código consciente e versionada, não silenciosa.
- O schema concreto (lista final de campos) é entregue na **Tarefa 4.0** do `PLANO_IMPLEMENTACAO.md`, antes do primeiro capítulo ser escrito. A skill `mestre-criacao-de-historia` aponta para esse schema como o contrato do que um capítulo precisa conter.

---

## ADR-026 — Validação de robustez por heurística determinística (sem classificador)

**Contexto.** O `PRD.md` §8 e §9, e a `mestre-principios-do-projeto`, exigem validação determinística da entrada do jogador **antes** de a ação chegar aos agentes. Três categorias precisam ser barradas: ações impossíveis (declarações de resultado, "eu mato o cavaleiro instantaneamente"), tentativas abusivas (injeção de prompt, tirar o LLM do papel, fora de personagem) e tentativas de levar a narrativa para conteúdo proibido (gore gratuito, sexual, temas pesados — `PRD.md` §9). Era preciso decidir **como** essa validação é implementada na v1.

**Opções consideradas.**
- **A — Heurística determinística simples:** listas de padrões, regex, regras estáticas em código (`agents/robustness.py`).
- **B — Classificador pequeno (ML local):** modelo de classificação de intenção/toxicidade treinado e mantido localmente.
- **C — LLM dedicado de moderação:** chamada extra a um LLM (separada da chamada de jogo) apenas para classificar a entrada.

**Decisão.** **Opção A — Heurística determinística simples.**

**Consequências.**
- **Por que não classificador (B):** introduzir um classificador exigiria escolher modelo, montar/curar dataset, definir parâmetros, e mantê-lo ao longo do tempo — uma cadeia inteira de decisões e operações para um problema cuja solução base **ainda não foi exercida**. Viola complexidade proporcional (`ARQUITETURA.md` §2.2). Antes de chamar ML, prova-se que regras simples não bastam — e essa prova só vem do uso real.
- **Por que não LLM de moderação (C):** soma latência e custo a cada turno, e usa LLM para uma tarefa onde o LLM é também o **vetor de ataque** que estamos tentando proteger. Defesa em profundidade pede uma camada determinística **separada** do LLM — não um LLM moderando outro LLM.
- **Limitação conhecida e aceita na v1:** a heurística terá **falsos positivos** (barra uma ação legítima que se parece com padrão proibido) e **falsos negativos** (deixa passar uma tentativa que devia barrar). Isso é **aceitável** na v1 pelas três defesas em camadas:
  1. **Segunda linha de defesa nos prompts** dos agentes — instruções de robustez fazem o Game Master se manter no papel mesmo se a heurística falhar (`PRD.md` §8, `ARQUITETURA.md` §15).
  2. **Impacto do falso positivo é apenas reapresentar o aviso vermelho** ao jogador; o estado não corrompe, o turno não é consumido, a mensagem é preservada (ADR-020). Custo: um aviso indevido que o jogador pode contornar reescrevendo a ação.
  3. **Impacto do falso negativo é mitigado** pelos prompts dos agentes e, sobretudo, pela validação determinística da **saída** do LLM antes de tocar o estado (fronteira determinístico/LLM, ADR-003). Mesmo se uma entrada abusiva passa, a saída ainda é validada.
- **Limitações conhecidas e aceitas explicitamente:**
  - Padrões baseados em palavras-chave em PT-BR — jogador escrevendo em outro idioma escapa (v1 só popula PT, ADR-015 — risco baixo).
  - Não detecta injeção semântica sofisticada que evita as palavras-chave conhecidas (ex.: roleplay elaborado para tirar o GM do papel).
  - Não detecta conteúdo proibido descrito de forma indireta ou eufemística.
- A heurística é **refinada continuamente durante a implementação**: cada falso positivo ou negativo encontrado vira uma regra. Esse refinamento não bloqueia a v1 — ele acompanha o uso.
- Em **v2+, se necessário, pode-se promover** a estratégia para classificador ou LLM dedicado, **com base em dados reais de uso** (categorias de FP/FN observadas), não em especulação.
- A localização da implementação é `backend/app/agents/robustness.py`.

---

## ADR-027 — Driver de Postgres: asyncpg + SQLAlchemy async

**Contexto.** A Fase 2 introduz persistência real. Era preciso escolher o driver de Postgres e a estratégia de acesso ao banco. O plano previa essa decisão explicitamente como "a registrar na Fase 2".

**Opções consideradas.**
- `psycopg3` async: driver moderno da psycopg family, suporta múltiplos backends de protocolo.
- `asyncpg` + SQLAlchemy 2.0 async: driver async puro para Postgres, amplamente adotado no ecossistema FastAPI/SQLAlchemy.

**Decisão.** `asyncpg` como driver de runtime + SQLAlchemy 2.0 com `create_async_engine`. URL: `postgresql+asyncpg://user:password@host:port/db`. Um único driver — sem driver síncrono paralelo. O ADK `DatabaseSessionService` recebe a mesma URL.

**Consequências.** Todas as queries do app usam async — coerente com FastAPI e ADK. Alembic usa asyncio no `env.py` com `create_async_engine` + `connection.run_sync(do_run_migrations)`, eliminando a necessidade de um segundo driver síncrono para migrations. Trocar para psycopg3 no futuro seria substituir uma linha de DSN e reinstalar o driver — a camada SQLAlchemy abstrai o resto.

---

## ADR-028 — Game state storage: JSONB por campanha (não tabelas normalizadas)

**Contexto.** O estado do jogo (`Character`, `Inventory`, `Location`, `Flags`, `History`, `HiddenState`) é uma estrutura hierárquica que evolui ao longo das fases (Fase 3 adiciona mutação de HP, Fase 4 adiciona flags de lore, etc.). Era preciso decidir como persistir esse estado no Postgres.

**Opções consideradas.**
- **Tabelas normalizadas:** `characters`, `inventory_items`, `locations`, `flags` — cada entidade em sua tabela, JOINs para montar o estado completo.
- **JSONB por campanha:** um campo `game_state JSONB NOT NULL` na tabela `campaigns`, com o modelo `GameState` Pydantic serializado inteiro.

**Decisão.** **JSONB por campanha.**

**Consequências.** A justificativa central é o **padrão de acesso real do projeto**: o estado é sempre lido e escrito **inteiro**, por uma **única campanha** — nunca há queries cross-campanha sobre campos internos do estado (ex.: "todas as campanhas com HP < 10" não existe no domínio). O motor de regras (Fase 3) recebe `GameState` inteiro, aplica funções puras, devolve `GameState` novo — o ORM persiste o JSONB atualizado. Tabelas normalizadas exigiriam múltiplos JOINs num padrão de acesso onde o JOIN nunca agrega valor: é complexidade sem contrapartida. Evolução do modelo Pydantic (novos campos no estado) não exige migration de colunas — só migration quando o campo `game_state` em si mudar de tipo (não ocorre na v1). Busca por campos internos do estado (não prevista na v1) é possível via operadores JSONB do Postgres sem schema change.

---

## ADR-029 — Estratégia de migrations: Alembic real desde a Fase 2

**Contexto.** A alternativa `Base.metadata.create_all` no lifespan do FastAPI entregaria o mesmo resultado na Fase 2, mas geraria dívida: na Fase 3+, quando mutations de schema ocorrerem (novas colunas, índices, tabelas para motor de regras e RAG), Alembic precisaria "adotar" um banco já existente sem histórico de migration — reconciliação manual e propensa a erro.

**Opções consideradas.**
- `Base.metadata.create_all` no lifespan: simples agora, problemático depois.
- Alembic desde a Fase 2: custo de configuração antecipado, sem dívida de reconciliação.

**Decisão.** **Alembic configurado e rodando desde a Fase 2.** O entrypoint do container executa `alembic upgrade head` antes de `uvicorn`. A migration `001_create_campaigns` é a primeira entrada versionada. `Base.metadata.create_all` não entra no lifespan do FastAPI.

**Consequências.** O custo de configurar Alembic agora é menor que o custo de reconciliar depois. Cada fase que alterar schema gera uma migration nova — historicamente auditável, segura em produção. `alembic upgrade head` no entrypoint é idempotente: se o schema está na versão atual, é no-op. O `depends_on: postgres: condition: service_healthy` no `docker-compose.yml` já garante que o Postgres está pronto antes do backend iniciar, então a migration roda contra um banco disponível. Detalhe de implementação: Alembic usa asyncio no `env.py` com `create_async_engine` + `connection.run_sync` — sem segundo driver síncrono (ver ADR-027).

---

## ADR-030 — Estratégia de chunking do RAG: por parágrafo com tamanho-alvo

**Contexto.** O RAG (`ARQUITETURA.md` §6) precisa dividir o conteúdo em "chunks" antes de embedar e indexar. Há um espectro de estratégias: tamanho fixo com janela deslizante e overlap (forte em recall, fraco em semântica e sintaxe), por seção semântica via cabeçalhos (forte em docs muito estruturados, fraco em texto corrido), por parágrafo (equilibra os dois lados em conteúdo de tom narrativo). A escolha precisa servir aos dois corpora — regras do SRD em Markdown estruturado e capítulos com texto corrido em PT-BR.

**Opções consideradas.**
- **A — Tamanho fixo com overlap (~500 chars, overlap ~100):** simples; recall um pouco maior; mas corta frases no meio, gera chunks artificiais sem identidade semântica.
- **B — Por seção (cabeçalhos Markdown):** ótimo para o SRD; ruim para o texto corrido dos capítulos.
- **C — Por parágrafo com tamanho-alvo:** quebra por `\n\n` (parágrafo natural), junta parágrafos curtos consecutivos até um alvo (~500 chars), corta parágrafos gigantes em fronteira de frase. Sem overlap.

**Decisão.** **Opção C — por parágrafo com tamanho-alvo.** Parâmetros iniciais: alvo ≈500 chars, piso 100, teto 800. Função pura em `backend/app/rag/chunking.py`, sem dependência de configuração para a v1.

**Consequências.**
- Funciona razoavelmente para os dois corpora: o SRD tem parágrafos curtos que serão agrupados em chunks com identidade temática; os capítulos têm parágrafos médios que já correspondem a unidades narrativas.
- Cada chunk mantém **frases inteiras** — embedding e retrieval lidam com unidades de sentido, não com cortes arbitrários.
- Sem overlap → não há duplicação de tokens; reduz ruído no top-k. Risco aceitável: uma informação dividida exatamente na fronteira pode "escapar" ao retrieval; mitigado pelo alvo de 500 chars (suficientemente grande para conter o contexto da maioria das ideias).
- A estratégia é **simples o suficiente para ser auditada por leitura**: ler 10 chunks aleatórios mostra se o particionamento faz sentido.
- **Refinamento previsto na Fase 7:** se o eval de retrieval mostrar problema concreto (não especulação), as opções de evolução são: voltar para overlap, ou tratar SRD e capítulos com estratégias distintas. Não otimizar agora.

---

## ADR-031 — `NarratorAgent` consome o RAG por prefetch determinístico, não por FunctionTool

**Contexto.** A `Tarefa 4.7` exige que o `NarratorAgent` seja "fundamentado em lore". Há duas formas de fazer um agente do ADK consumir o RAG: (a) **FunctionTool** — o agente decide quando chamar um `retrieve_lore(query)` durante a resposta, idiomático ADK; (b) **prefetch determinístico** — o código do `runner.py` faz a busca antes de invocar o agente, e injeta os trechos no contexto da sessão (`session.state`).

**Opções consideradas.**
- **A — FunctionTool:** o agente é "soberano" sobre quando consultar. Custos: pelo menos uma chamada de tool extra por turno (latência), o agente pode entrar em loop de tool-calling, custo de tokens maior, comportamento não-determinístico ("às vezes ele esquece de consultar").
- **B — Prefetch determinístico:** o `runner.py` faz `vector_store.search(corpus="lore", query=ação_do_jogador, k=top_k)` antes de chamar o agente; injeta o resultado em `session.state["lore_context"]`; a instrução do agente referencia `{lore_context}` (substituição do ADK). Uma chamada de embedding + uma query SQL a cada turno — previsível, barato, debugável.
- **C — Híbrido:** prefetch sempre + tool opcional. Maior superfície, maior custo, raramente compensa.

**Decisão.** **Opção B — prefetch determinístico** no `runner.py` para o `NarratorAgent` na Fase 4.

**Consequências.**
- **Determinismo:** todo turno passa pela mesma busca; comportamento previsível, fácil de testar e logar.
- **Latência e custo:** uma busca por turno; o agente vê o contexto já montado e não gasta tokens decidindo se "deve buscar".
- **Observabilidade:** o painel "pensamento do mestre" (Fase 5/6) recebe o retrieval do turno em campo conhecido; nada escondido em chamadas internas de tool.
- **Coerência com o princípio determinístico/LLM** (ADR-003): a decisão "buscar lore" é fluxo de pipeline, não decisão de LLM. O LLM **usa** o que recebeu; ele não decide se deve buscar.
- **Escopo aberto para o Referee:** a Fase 5 reabre a questão para o `RefereeAgent`. Lá, o agente pode ter que decidir **qual** regra buscar com base em raciocínio sobre a ação — caso onde FunctionTool pode passar a pagar o aluguel. Decisão de Fase 5, registrada se mudar.
- **Trade-off conhecido:** o agente não pode "pedir mais contexto" se o top-k recuperado for irrelevante; a mitigação na v1 é instrução de prompt ("se contexto irrelevante, narre genericamente sem inventar fatos do mundo"). Eval de retrieval na Fase 7.

---

## ADR-032 — Idempotência da ingestão: delete-por-source antes do insert

**Contexto.** A `Tarefa 4.6` exige que a ingestão de conteúdo no RAG seja **idempotente** — rodar duas vezes não duplica registros — e que o conteúdo possa **mudar** ao longo da v1 (correções, expansão do capítulo 1 na Fase 5). Sem estratégia explícita, opções comuns levam a problemas: `INSERT` direto duplica; `INSERT ... ON CONFLICT DO NOTHING` deixa órfãos quando um arquivo encolhe (menos chunks) ou quando os chunks reordenam.

**Opções consideradas.**
- **A — `ON CONFLICT DO UPDATE` por `(corpus, source, chunk_index)`:** atualiza in-place, mas deixa chunks órfãos quando o número de chunks diminui.
- **B — Delete-por-source antes do insert (em transação):** apaga todos os chunks com `(corpus, source)` igual, insere os novos. Transacional, simples, sem órfãos.
- **C — Hash do arquivo inteiro como chave:** evita re-trabalho se o arquivo não mudou; combinável com B.

**Decisão.** **B + C.** Chave de identidade dos chunks: `(corpus, source, chunk_index)` (unique). Cada `source` (= um arquivo de conteúdo) tem um `content_hash` agregado armazenado por chunk (ou em metadados). Na ingestão: se o hash do conteúdo atual difere do hash do conteúdo já indexado para aquele `source`, faz **DELETE** dos chunks daquele `source` e **INSERT** dos novos, dentro de uma transação. Se o hash bate, é **skip** silencioso (idempotência rápida).

**Consequências.**
- **Sem órfãos:** o `source` é a unidade de re-indexação; arquivos que encolhem não deixam chunks fantasmas.
- **Transacional:** o cliente que faz `search` durante a re-ingestão nunca vê o `source` parcialmente atualizado.
- **Re-ingestão sem mudança é barata:** comparação de hash, sem embedding, sem escrita.
- **`source` é nome de identificador estável:** caminho relativo do arquivo dentro de `content/` (ex.: `srd/perícias.md`, `chapters/chapter-01/chapter.yaml`). Renomear um arquivo é um "delete + insert" implícito — aceitável.
- **Hash é por chunk** (auditoria) e também agregado por source via metadados — permite tanto skip rápido quanto inspeção fina.

---

## ADR-033 — Modelo de embedding inicial: multilíngue desde o início

**Contexto.** A v1 ingere conteúdo em **português brasileiro** (capítulos do jogo) e em **inglês via SRD em PT-BR traduzido**. O `EMBEDDING_MODEL` padrão precisa servir esse conteúdo. A escolha inicial no `.env.example` era `sentence-transformers/all-MiniLM-L6-v2`, modelo treinado primariamente em inglês.

**Opções consideradas.**
- **A — `all-MiniLM-L6-v2` (EN-only, 384 dim):** menor, mais rápido, mas embeddings em PT-BR ficam menos discriminativos.
- **B — `paraphrase-multilingual-MiniLM-L12-v2` (multilíngue, 384 dim):** treinado em 50+ línguas, **mesma dimensão**, ligeiramente maior em disco/RAM (~120MB vs ~80MB), ligeiramente mais lento na inferência.
- **C — Manter EN-only agora, trocar depois se necessário:** especular sobre "se vamos precisar", carregar dívida.

**Decisão.** **Opção B — `paraphrase-multilingual-MiniLM-L12-v2` desde o início.**

**Consequências.**
- **Custo de mudança hoje:** zero — mesma dimensão (384), mesma migration, mesma camada de provider, apenas um valor no `.env.example` muda.
- **Custo de mudança depois:** alto — trocar modelo de embedding exige **re-ingestão completa** dos dois corpora (todos os vetores precisam ser regerados). Conforme o conteúdo cresce, o custo só aumenta.
- **Não é especulação:** o conteúdo do projeto **já é em PT-BR** (ADR-015). Escolher modelo apropriado ao conteúdo que já existe é proporcional, não over-engineering.
- **Risco aceito:** o modelo é um pouco maior (~120MB vs ~80MB) e marginalmente mais lento; nenhum dos dois afeta a v1 (cache via `HF_HOME` em volume; inferência ainda é rápida para os volumes da v1).
- **Refinamento Fase 7:** se o eval de retrieval mostrar problema concreto (não especulação), pode-se promover para um modelo maior (ex.: `paraphrase-multilingual-mpnet-base-v2`, 768 dim — exige nova migration). Não fazer agora.

---

## ADR-034 — Política de falha na ingestão: granularidade entre estrutural e conteúdo

**Contexto.** A `Tarefa 4.6` integra a ingestão do RAG ao `lifespan` do FastAPI: na subida do backend, o conteúdo de `content/` é validado, chunkado, embedado e indexado. Decisão pendente: **o que deve derrubar o startup, e o que deve apenas ser logado e ignorado?** Uma política única para os dois casos é ruim: derrubar o startup por qualquer erro torna o sistema frágil (uma vírgula errada no capítulo 1 trava todo o backend); deixar tudo passar mascara problemas reais (modelo de embedding não carrega, banco indisponível).

**Opções consideradas.**
- **A — Tudo derruba startup:** robusto contra esquecer um erro, mas frágil em ambiente real onde conteúdo evolui constantemente.
- **B — Tudo é skipado e logado:** sistema sobe mesmo quebrado; problemas estruturais ficam invisíveis até o primeiro turno falhar.
- **C — Granularidade:** falhas **estruturais** derrubam startup; falhas de **conteúdo individual** são logadas como erro estruturado e skipadas; cada arquivo é processado em try/except próprio; ao final, um `IngestReport` resume o que entrou e o que falhou.

**Decisão.** **Opção C — granularidade.**

**Definições.**
- **Falha estrutural** (propaga, derruba startup): modelo de embedding não carrega, dependência ausente, banco indisponível, schema do banco desalinhado, migration pendente, erro de programação na ingestão (ex.: `AttributeError` no código). São sintoma de problema operacional que **não pode** ser ignorado.
- **Falha de conteúdo** (capturada, logada, skipada): YAML inválido, capítulo malformado (`ValidationError` do Pydantic), `FileNotFoundError` de um arquivo individual, `UnicodeDecodeError`, erro de parsing de um arquivo isolado. São conteúdo defeituoso — outros arquivos ainda servem ao jogo.

**Consequências.**
- A ingestão envolve cada arquivo em try/except próprio. Falha estrutural é deixada propagar; falha de conteúdo é capturada e registrada em `IngestReport.falhas: list[{source, error_type, message}]`.
- O log de startup termina com `Ingestão: {processados} ok, {skipados} sem mudança, {len(falhas)} falhas: [...]` — visibilidade alta em qualquer ambiente.
- **Robustez operacional:** um erro de digitação em um capítulo nunca derruba o backend. Os outros capítulos e o SRD continuam servindo o jogo; o operador corrige o arquivo na próxima oportunidade.
- **Sem mascarar problemas reais:** o `report.falhas` é parte visível do log; problemas estruturais ainda derrubam o startup. Não há "quase tudo funcionando em silêncio".
- **Coerência com ADR-020:** já tratamos falha do LLM sem corromper estado e sem perder a jogada. ADR-034 é a contrapartida para a camada de ingestão.
- **Teste explícito:** um teste de `ingest_all` com um arquivo válido + um malformado verifica que (a) o válido entra, (b) o malformado fica em `report.falhas`, (c) **nenhuma exceção propaga**.

---

## ADR-035 — GameMaster orquestrador em Python, não como agente ADK

**Contexto.** A `Tarefa 5.4` define o `GameMasterAgent` como orquestrador do loop de turno: coordena `RefereeAgent` → resolução de dados (determinística) → aplicação de consequências (determinística) → `NarratorAgent` → `NPCActorAgent` (condicional). A arquitetura recomenda começar simples (cadeia sequencial) e só evoluir para `BaseAgent` customizado se a lógica condicional exigir (`ARQUITETURA.md` §4.2). Decisão pendente: onde mora essa orquestração de fato?

**Opções consideradas.**
- **A — `SequentialAgent` nativo do ADK** encadeando Referee → Narrator → NPCActor. Idiomático no framework. Limitação: pulos condicionais (pular rolagem quando não é necessária, pular NPCActor quando nenhum NPC reage) viram workarounds — o `SequentialAgent` puro executa todo mundo na ordem. Etapas determinísticas (rolar dados, aplicar consequência) não cabem nele.
- **B — `BaseAgent` customizado** com `run_async` próprio: chama os sub-agentes na ordem que quiser, intercala etapas determinísticas. Funciona, mas duplica o que Python já resolve diretamente. O `ARQUITETURA.md` §4.2 explicitamente diz "só evolui para `BaseAgent` quando a lógica condicional exigir" — não é o caso ainda.
- **C — Função Python em `runner.py`** orquestrando: validação → prefetch → `Runner.run_async(referee)` → (rolagem determinística) → `apply_consequence` → `Runner.run_async(narrator)` → (NPCActor condicional) → persistir trace. Cada agente ADK é invocado individualmente; a glue é Python.

**Decisão.** **Opção C — orquestração em Python no `runner.py`.**

**Consequências.**
- **Coerência com ADR-003:** o fluxo do turno (incluindo "pular rolagem", "chamar NPC se há NPC reagindo") é decisão determinística — não julgamento. Pertence a código, não a um agente. Um `BaseAgent` que faz `if ruling.precisa_rolagem: ...` é uma função Python disfarçada.
- **Simplicidade:** menos camadas, menos abstração ADK por cima do necessário (princípio de complexidade proporcional, ADR-009 estende-se a frameworks).
- **Etapas determinísticas convivem naturalmente:** `roll_dice`, `apply_consequence` (que são código puro, não agentes) entram no fluxo como chamadas Python normais. Em `SequentialAgent`/`BaseAgent`, teriam que ser envolvidas em wrappers.
- **Testabilidade:** o orquestrador é uma função `async def stream_turn(...)` — testável com mocks dos agentes individuais e dos providers, sem subir o ADK Runner inteiro.
- **`Runner` do ADK continua usado** para cada agente individualmente — não estamos abandonando o ADK, só não usando seus primitivos de composição.
- **Trade-off conhecido:** perdemos algumas conveniências do ADK (ex.: tracing nativo entre agentes do mesmo `SequentialAgent`). Mitigação: `TurnTrace` (ADR-036) registra explicitamente o pipeline; não dependemos de tracing implícito do framework.
- **Limite de extração:** se o orquestrador `stream_turn` passar de ~50 linhas com lógica condicional, extrai-se para módulo `runner_turn.py`. O `runner.py` segue dono do init de `Runner`/sessões/providers.
- **Refinamento futuro:** se a v2 (grupo de personagens, descanso, progressão) introduzir lógica de turno realmente ramificada e custosa de manter em Python (ex.: máquina de estados de combate por iniciativa), reabrir para Opção B. Não fazer agora.

---

## ADR-036 — Trace de turno em tabela própria, separado de HistoryEntry

**Contexto.** A `Tarefa 5.8` exige observabilidade estruturada de cada turno (ruling do Referee, trechos recuperados pelo RAG, rolagem, proposta de consequência, narração, reação de NPC) para alimentar o **painel "pensamento do mestre"** (PRD §6.7) e servir de base de depuração. `GameState.history` já existe como lista de `HistoryEntry(turn, player_action, narration, timestamp)` no JSONB da campanha. Decisão pendente: onde guardar o trace?

**Opções consideradas.**
- **A — Campo `trace: dict | None` dentro de cada `HistoryEntry`.** Menos tabelas. Mas mistura dois conceitos: a história jogável (turno do jogador, narração que ele leu) e o pensamento do mestre (logs de pipeline). `GET /log` passa a carregar trace inteiro mesmo quando o frontend só quer renderizar a história; trace cresce muito (top-k de retrieval, ruling completo, eventos do ADK), inflando o JSONB da campanha.
- **B — Tabela própria `turn_traces`** com `(id, campaign_id, turn_number, trace: JSONB, created_at)` + índice `(campaign_id, turn_number)`. `HistoryEntry` permanece enxuto.
- **C — Não persistir trace.** Calcular sob demanda re-rodando o turno? Inviável (não-determinístico do LLM) e dispendioso.

**Decisão.** **Opção B — tabela própria `turn_traces`.**

**Consequências.**
- **Separação de responsabilidades:** história jogável (`HistoryEntry`) é leve, fica no JSONB da campanha e alimenta `GET /log`. Trace de observabilidade fica numa tabela própria, alimenta `GET /campaigns/{id}/turn/{n}/trace` consultado sob demanda pelo painel recolhível (PRD §6.7).
- **Performance:** `GET /log` continua barato; trace só é lido quando o jogador clica para abrir o painel.
- **Schema do trace evolui sem migration do JSONB principal:** o `trace JSONB` aceita campos novos (versão do prompt, latência, custo) sem tocar em `campaigns.game_state`.
- **Chave de consulta natural:** `(campaign_id, turn_number)` casa com a URL `/campaigns/{id}/turn/{n}/trace`. Índice garante leitura O(log n).
- **Retenção e poda futuras:** se um dia quisermos arquivar traces antigos para reduzir volume, é DELETE numa tabela; não toca em estado de partida.
- **Coerência com ADR-007:** ainda é o mesmo Postgres único — uma tabela a mais não viola "uma peça de infraestrutura". O custo é uma migration nova (Alembic, ADR-029).
- **Migration de transição:** primeira partida com a feature já grava trace; partidas antigas (sem trace) simplesmente não têm linhas em `turn_traces` — `GET .../trace` retorna 404 com mensagem clara, sem corromper nada.

---

## ADR-037 — Stack do frontend v1: Vite/React/TS, fetch+EventSource, state-driven, CSS vanilla, i18n autoral

**Contexto.** O backend está pronto e expõe API REST + SSE (`POST /campaigns`, `POST /campaigns/{id}/action`, `GET /state`, `GET /log`, `GET /turn/{n}/trace`). A `ARQUITETURA.md` §3/§12 já fixou **React + Vite + TypeScript** como base técnica e definiu que o frontend conversa **apenas** com o backend. Faltam as escolhas internas da camada do app — HTTP client, parser de SSE, roteamento entre as 4 telas (landing, criação, retomada, jogo), gerenciamento de estado global (`campaign_id`, `state`), i18n e abordagem de estilo. Cada uma dessas escolhas é, na prática, uma porta para uma dependência adicional. Decisão pendente: o que entra agora, o que fica de fora.

**Opções consideradas.**
- **A — Stack "padrão de mercado": axios + React Router + Zustand/Redux + react-i18next + Tailwind / styled-components.** Familiar, abundante na comunidade, decisões pré-tomadas. Mas (1) cada dependência paga aluguel próprio em superfície de bug, peso de bundle, e curva de aprendizado para futuros contribuidores; (2) Tailwind e bibliotecas de componentes empurram a interface para o visual genérico de "chat com IA" — exatamente o que a skill `mestre-frontend` proíbe ("não pode ter cara de sistema genérico de IA"); (3) react-i18next é projetado para múltiplos idiomas com fallback/plurais/interpolação complexa — overkill para a v1 que só popula PT (`ADR-015`).
- **B — Stack "complexidade proporcional": fetch nativo + EventSource + state-driven routing + Context+hooks + i18n autoral simples + CSS vanilla com variáveis CSS.** Cada peça resolve um problema que o projeto **realmente tem hoje**, sem antecipar problemas que pode vir a ter. Mais código autoral, menos depend­ência externa.
- **C — Misto:** algumas escolhas autorais (CSS, i18n), outras de prateleira (React Router, axios). Reduz risco em pontos específicos. Mas multiplica decisões sem ganho claro — se `fetch` resolve, axios não paga aluguel; se 4 telas cabem em state-driven, React Router não paga aluguel.

**Decisão.** **Opção B — stack mínima e autoral.** Em concreto:

- **HTTP:** `fetch` nativo. Sem axios.
- **SSE:** `EventSource` nativo. Sem `eventsource` polyfill (Chrome/Edge/Firefox modernos bastam para a v1).
- **Roteamento:** state-driven (um state `screen: "landing" | "create" | "resume" | "play"` em um Context). Sem React Router.
- **Estado global:** React Context + hooks customizados (`useCampaign`, `useT`). Sem Zustand/Redux.
- **i18n:** módulo autoral leve — um objeto `pt: { ... }` + hook `useT(key)` que faz lookup. Sem react-i18next.
- **Estilo:** CSS vanilla com variáveis CSS para o tema (paleta, tipografia serifada, espaçamento, sombras/bordas). Sem Tailwind/styled-components/CSS-in-JS.
- **Dependências runtime mínimas:** `react`, `react-dom`. Dev: `vite`, `@vitejs/plugin-react`, `@types/*`, e o ESLint/TS que já existem.

**Consequências.**
- **Coerência com o princípio de complexidade proporcional (`ARQUITETURA.md` §2.2):** cada escolha tem um problema concreto que resolve hoje. As que não resolvem nada hoje não entram. Trocar depois é local: se a v2 tiver muitas telas e a state-driven começar a doer, troca-se por React Router em um único componente raiz.
- **Identidade visual sob controle:** sem framework de componentes ditando o visual, a camada de design autoral (skill `mestre-frontend`) tem o palco que precisa. Tipografia serifada + paleta autoral + texturas/bordas trabalhadas vivem em CSS vanilla com variáveis — sem brigar com uma biblioteca que tem opiniões fortes sobre como botão deve parecer.
- **Bundle pequeno:** `react` + `react-dom` + código próprio. Tempo de build e tempo de download mínimos.
- **Coerência com `ADR-015`:** i18n autoral é exatamente "arquitetura na v1, só PT populado". Quando o inglês entrar na v2, ou se popula mais um objeto (`en: { ... }`) ou se troca por react-i18next — decisão informada pelo problema real.
- **Coerência com `ADR-013`:** state-driven routing combina com autenticação por ID anônimo — não há URL pública para compartilhar (a v1 não tem deep linking; o jogador retoma pelo ID, não pela URL).
- **Trade-off conhecido — código autoral vs. lib:** mais código de glue (parser SSE, hook de tradução, transições de tela) — mas é código simples, testável, e que protege contra "dependência de prateleira que precisou ser reescrita". Trade-off explícito: trocamos peso de dependência por linhas autorais legíveis.
- **Limites de extração:** se o parser SSE passar de ~80 linhas, ou se i18n ganhar plurais/interpolação complexa, ou se aparecer uma 5ª/6ª tela, **reabrir** a opção C para o componente específico. Não fazer agora.

---

## ADR-038 — Endpoint `/graph` com filtragem de revelação no backend

**Contexto.** O grafo de locações é uma das três zonas de interface (`ARQUITETURA.md` §9 e §12.2). Cada capítulo declara cenas (nós) com `connections` (arestas) — o cap 1 atual tem 5 cenas. O grafo é **derivado dos dados do capítulo**, e os nós devem se revelar **progressivamente** conforme exploração (PRD §6.4). O estado do jogo já tem `flags.locations_revealed: list[str]` para isso. Decisão pendente: como o frontend obtém os dados do grafo, e onde acontece o filtro de revelação.

**Opções consideradas.**
- **A — Frontend lê `chapter.yaml` estático.** O conteúdo do capítulo é servido como arquivo estático junto do bundle, e o frontend filtra contra `flags.locations_revealed` (vindo de `/state`). Mais simples na superfície, mas viola dois princípios duros: (1) **frontend só fala com backend** (`ARQUITETURA.md` §1) — o conteúdo passa a ser servido por dois lugares (backend ingerindo + frontend lendo); (2) duplica os dados do capítulo (cópia no frontend que pode divergir do backend); (3) e — fatal — **o conteúdo do capítulo inclui `hidden_state` por NPC e notas de Game Master** (`adventure_schema.py`). Servir o YAML inteiro ao frontend é o equivalente a expor as notas do mestre para o jogador. Inviável.
- **B — Expandir `GET /state` para incluir `available_connections` da cena atual e a lista de nós revelados.** Reduz endpoints, mas: (1) força o payload de `/state` (lido a cada turno) a carregar dados que mudam pouco; (2) acopla o contrato do painel de ficha ao contrato do grafo — duas zonas de interface compartilhando schema é forçado; (3) ainda é o frontend que faz a montagem das arestas, então cada cliente que consumir a API repete a lógica.
- **C — Novo endpoint `GET /campaigns/{id}/graph` que retorna o **subgrafo já filtrado** no backend.** Apenas nós em `flags.locations_revealed` e arestas entre eles. Nada de `revealed: true/false` no payload — nós ocultos **não trafegam**.

**Decisão.** **Opção C — endpoint próprio com filtragem no backend.** Schema: `GraphResponse { nodes: [{id, name, position: {x, y}}], edges: [{from, to}], current: str }`. O conjunto de nós retornado é exatamente `flags.locations_revealed`; arestas são as conexões do capítulo cujas duas pontas estão em `locations_revealed`. Nada além disso.

**Consequências.**
- **Estado oculto nunca trafega — invariante mais importante da fase.** Ao não enviar nós com flag `revealed: false`, o cliente **não pode** vazar dados ocultos por engano (CSS errado, renderização condicional invertida, decompilação do bundle). O servidor não conta o que o jogador não conhece.
- **Separação de responsabilidades:** `/state` continua sendo "ficha + localização atual + flags"; `/graph` é "subgrafo visível". Cada zona da interface tem o endpoint que precisa, com o payload que precisa.
- **Coerência com o princípio `frontend só fala com backend`:** uma fonte de verdade — o backend. O `chapter.yaml` continua no repositório como código-fonte do conteúdo, mas é ingerido e servido pelo backend.
- **Custo barato:** o capítulo já está ingerido no Postgres (ADR-023). Construir o subgrafo é uma operação O(N+E) em memória sobre a `Adventure` carregada da campanha, sem nova migration.
- **Testabilidade direta:** o filtro é uma função pura sobre `(adventure, locations_revealed) -> GraphResponse`. Testável sem agente, LLM ou banco.
- **Teste de invariante obrigatório antes do commit:** criar campanha com `locations_revealed=["taverna_interior"]`, chamar `/graph`, e asserter que **apenas** `taverna_interior` aparece e nenhuma outra cena do capítulo é mencionada. Esse teste protege o invariante mais importante da Fase 6 contra regressões futuras (alguém adicionando um campo "preview do próximo nó" sem perceber o que está vazando).
- **Posições dos nós:** o backend retorna `position: {x, y}` por nó. Vêm de onde? Resposta no ADR-039 (são campos no `chapter.yaml`, autorais, determinísticos). Aqui só registra-se que o endpoint **expõe** esses dados; quem define vem do ADR-039.
- **Evolução futura:** se a v2 introduzir "pistas sobre nós não-revelados" (ex.: "você vê uma estrada ao norte mas não sabe para onde leva"), modela-se como nó próprio com nome genérico (`"estrada_norte_pista"`) e o jogador descobre o nome real ao explorar. Não como flag de revelação parcial no payload. Mantém o invariante.

---

## ADR-039 — Grafo de locações em SVG autoral com posições explícitas no YAML do capítulo

**Contexto.** O endpoint `/graph` (ADR-038) devolve `nodes: [{id, name, position: {x, y}}, ...]`. Falta decidir **de onde vêm as coordenadas**. O grafo do cap 1 tem 5 nós; capítulos futuros terão um pouco mais. A skill `mestre-frontend` proíbe visual de "chat genérico" — o grafo é uma das peças mais visíveis da identidade temática e não pode parecer um diagrama UML auto-gerado. Decisão pendente: como o autor controla o layout?

**Opções consideradas.**
- **A — Algoritmo dinâmico de layout (força/elástico/radial) no frontend.** Zero metadados no YAML. Mas: (1) o resultado de algoritmos físicos é **não-determinístico entre runs** (semente variável) e **muda quando um nó é revelado** — o grafo "salta" no meio da partida, quebrando a sensação de mapa estável; (2) a estética sai genérica — o autor não tem onde colocar a intenção ("a clareira fica longe, na ponta direita; a cozinha é um beco lateral"); (3) algoritmos físicos competem com a identidade visual autoral.
- **B — Algoritmo determinístico simples (BFS / árvore radial a partir do `starting_scene`).** Resolve o "salta" da opção A (determinístico — mesmo input, mesmo layout) e não pede nada do autor. Mas a estética ainda é mecânica: nós em níveis equidistantes, sem hierarquia narrativa. Bom como **fallback** — não como padrão.
- **C — Coordenadas `position: {x, y}` declaradas em cada `Scene` do YAML, como parte do formato de aventura.** O autor decide onde cada locação fica. Cap 1 tem 5 cenas — meio minuto de trabalho. O layout é parte do design do capítulo, como o `read_aloud` é.

**Decisão.** **Opção C como padrão, com Opção B como fallback.** Concretamente:

- Adiciona-se `ScenePosition { x: float, y: float }` em `adventure_schema.py`. Campo `position: ScenePosition | None = None` em `Scene`.
- Cap 1 preenche `position` em todas as 5 cenas.
- O endpoint `/graph` retorna a `position` declarada. Se uma cena revelada não tiver `position`, o backend aplica o **fallback determinístico (BFS por nível, espaçamento fixo)** para *aquela cena* — não derruba a resposta, mas registra um warning estruturado. (Capítulos novos podem nascer sem layout autoral; o fallback dá um grafo legível enquanto o autor não preenche.)
- **Espaço de coordenadas:** sistema lógico `viewBox` SVG, sem unidade física fixa. O frontend escolhe o `viewBox` final (ex.: `0 0 800 500`) e aplica `preserveAspectRatio` para responsividade. Valores típicos: `x ∈ [80, 720]`, `y ∈ [80, 420]`. Sem grade rígida — o autor compõe livremente.

**Consequências.**
- **Identidade visual sob controle autoral.** Locações importantes podem ocupar posições visualmente importantes (a clareira na ponta de tensão, a cozinha como apêndice lateral). É design, não auto-layout.
- **Layout estável durante a partida.** Revelar um nó não rearranja os outros — apenas o nó novo aparece na posição que ele já tinha no plano. Coerência visual entre turnos.
- **Custo de autoria proporcional.** 5 cenas no cap 1 = 5 pares de coordenadas. Para capítulos maiores (15+ cenas) ainda é trabalho menor que escrever a `description` de uma cena. O fallback evita bloquear um capítulo novo enquanto o layout ainda não foi pensado.
- **Coerência com `ADR-038`:** o endpoint continua devolvendo só o subgrafo revelado. As coordenadas vão junto com `id` e `name` — o frontend nunca enxerga uma posição de cena oculta.
- **Validação:** o schema do capítulo valida que `x` e `y` são números finitos. O `Adventure.model_validate` rejeita YAMLs com `position: x: "foo"`. Sem coordenadas malformadas chegando ao endpoint.
- **Trade-off conhecido — Layout não responsivo a densidade.** Se o autor concentrar 8 cenas perto demais, o frontend não rebalanceia. Aceitável na v1; se virar problema, adiciona-se `viewBox` por capítulo no YAML como evolução do mesmo padrão (mesma opção C, em escala).
- **Sem dependência de lib de grafo.** O frontend desenha SVG diretamente (linhas, círculos, glyphs) — sem React Flow / d3-force. Cumpre o princípio "complexidade proporcional" e mantém a identidade temática sem brigar com a opinião visual de uma lib.

---

## ADR-040 — Placeholder de imagem estilizado, coerente com a estética RPG

**Contexto.** O capítulo 1 tem 3 `image_briefings` em `chapter.yaml`. Esses briefings são prompts para uma ferramenta externa (Nano Banana) gerar os arquivos `.webp` que vivem em `frontend/public/chapters/01/` — trabalho **manual** do autor, fora do ciclo de código (`ARQUITETURA.md` §12.5). Realidade da v1: as imagens podem não existir ainda quando o jogador entra na cena. Decisão pendente: o que aparecer enquanto a imagem real está ausente.

**Opções consideradas.**
- **A — Nada.** Se a imagem não carrega, a região fica em branco. Quebra a composição visual da tela, parece "página em construção".
- **B — Ícone de "imagem não encontrada" do navegador.** Cria sensação de site quebrado — exatamente o que a skill `mestre-frontend` proíbe ("não pode parecer um sistema genérico").
- **C — Imagem genérica de stock (silhueta de espada/escudo).** Substitui assets gráficos do projeto (proibido por ADR-016) e ainda assim parece preenchimento de e-commerce.
- **D — Placeholder SVG ornamentado autoral, gerado a partir do briefing.** Borda trabalhada em dourado/bronze, título da cena em serifada, atmosfera do briefing como subtítulo em itálico. Visualmente um "selo" — fica em primeira pessoa com a identidade do resto. Sem asset externo, sem stock.

**Decisão.** **Opção D — placeholder SVG ornamentado autoral.**

Concretamente: componente `SceneImage` que tenta carregar `/chapters/{chapter}/{image_id}.webp`; em falha (`onError`), renderiza um `<svg>` inline com:
- moldura retangular com cantoneiras decorativas em traço dourado;
- título da cena em fonte `display` (Cinzel), versalete;
- atmosfera do briefing (campo `atmosphere`) em itálico (EB Garamond), abaixo;
- fundo com gradiente sutil de pergaminho/couro coerente com o resto da paleta.

Quando o autor sobe a imagem real para `frontend/public/chapters/01/{id}.webp`, ela aparece automaticamente — o placeholder é overlay-of-fallback, não estado persistente.

**Consequências.**
- **A tela com placeholders fica boa o suficiente para não bloquear nenhum commit.** Era o critério do plano: "placeholder feio o suficiente para querer pausar = a gente perdeu a vantagem". A versão estilizada paga o aluguel.
- **Coerência com ADR-016 (sem representação gráfica de personagem).** O placeholder é tipografia ornamentada — não desenho de cena, não silhueta de NPC.
- **Coerência com ARQUITETURA §12.5.** O sistema continua *não gerando* imagens; ele apenas degrada com elegância quando a imagem real não chegou.
- **Substituição transparente.** Trocar o placeholder pela imagem real é arrastar um arquivo. Sem mudança de código, sem flag.
- **Trade-off conhecido — placeholder não atende a quem não tem acesso ao briefing.** A atmosfera vem do `image_briefings[].atmosphere` do capítulo. Cenas sem briefing (futuras) terão fallback ainda mais sóbrio (só título). Aceitável.
- **Sem novo endpoint.** O frontend conhece o `id` da locação atual via `/state` e usa convenção de caminho `/chapters/01/{location_id}.webp` (ou o id do briefing — alinhado ao cap 1 onde `image_briefings[].scene == scene.id` na maioria). Mapeamento futuro mais sofisticado entra com um endpoint próprio se preciso.

## ADR-041 — Campos de apresentação cartográfica no schema de aventura

**Contexto.** O mapa de locações ganhou textura de pergaminho (ADR-040 trata do placeholder de cena; aqui é o canvas do grafo) e precisa, para virar de fato uma "carta cartográfica" e não um diagrama, de três elementos visuais: título caligráfico da região, rosa-dos-ventos e ícones temáticos por nó. A rosa-dos-ventos é decoração pura (cabe no frontend). Mas título e ícone são **conteúdo** — variam por capítulo. Risco real: hardcodar `"Estrada do Norte"` e um dicionário `taverna_interior → caneca` no frontend funciona para o cap 1 e quebra no cap 2 (Pedra-Cinza, outras locações). Cada capítulo novo passaria a exigir edição simultânea de YAML *e* frontend para o mapa ficar correto. Quebra do princípio "conteúdo de aventura é dado, não código" (ARQUITETURA §3.3).

**Opções consideradas.**
- **A — Hardcodar no frontend.** Simples, custa 1 hora a menos hoje. Mas vira dois pontos de hardcode (título + ícones) que toda nova locação morde. Resgate caro depois.
- **B — `map_title` em Adventure (compartilhado entre capítulos).** Razoável quando a aventura inteira se passa em uma região coerente. Mas o cap 1 desta aventura é "Estrada do Norte" e o cap 2 já será "Pedra-Cinza" (segundo `hook_next` do YAML do cap 1) — outra geografia. Forçaria reescrita do título a cada transição.
- **C — `map_title` em Chapter + `icon` em Scene.** Cada capítulo declara sua região; cada cena declara seu glifo cartográfico. Frontend lê do dado vindo via `/graph`.

**Decisão.** **Opção C — campos de apresentação cartográfica no schema de Chapter e Scene.**

Concretamente:
- `Chapter.map_title: str | None = None` — título caligráfico da região do capítulo. Opcional para retrocompatibilidade com capítulos antigos; quando ausente, o frontend simplesmente não renderiza o título.
- `Scene.icon: str | None = None` — chave aberta (não `Literal`/enum) que mapeia para um glifo SVG no frontend. Vocabulário inicial do cap 1: `tavern`, `interior`, `square`, `road`, `clearing`. `interior` é deliberadamente genérico — reusável em biblioteca, quarto, adega — para evitar inflar o catálogo a cada cena nova.
- Endpoint `/graph` passa a incluir `title` em `GraphResponse` e `icon` em cada `GraphNode`. O filtro de revelação de `build_graph_response` continua intacto — `icon` só viaja para nós que estão no resultado, então estado oculto não vaza por essa via.
- Frontend tem dicionário `glyph_by_icon_name → <g> SVG`. Quando `icon` é `null` ou desconhecido, o nó cai no **pip dourado** atual (fallback elegante, nunca quebra).

**Por que `map_title` em `Chapter` e não em `Adventure`.** Aventura pode atravessar regiões geográficas distintas em capítulos diferentes (caso do cap 1 → cap 2 deste mesmo conteúdo). Localizar o título no capítulo dá flexibilidade sem custo. **Se uma campanha futura quiser título compartilhado entre capítulos**, evolui pra campo opcional em `Adventure` que `Chapter` pode sobrescrever (mesmo padrão de fallback que já usamos em outras decisões). Não implementar agora — só não fechar a porta.

**Por que chave aberta para `icon` (não enum).** Capítulos futuros vão querer adicionar glifos novos (porto, torre, mina, cripta) sem precisar editar o schema Python a cada vez. Chave aberta + fallback no frontend é o ponto mínimo de acoplamento: o autor escreve no YAML, o frontend adiciona o `<g>` no dicionário quando quiser desenhar o novo glifo. Antes disso, o nó renderiza no pip dourado — funcional, não bloqueia capítulo.

**Consequências.**
- **Coerência com ADR-038 (estado oculto não vaza).** O `icon` é propriedade da cena, e cenas ocultas continuam ocultas no `build_graph_response`. Não há ação adicional. O teste de invariante ganha um assert: "icon de cena oculta não aparece no payload".
- **`map_title` é metadata pública.** É equivalente a "Capítulo X" num livro — narrativa estrutural, não estado da partida. Aparece no `/graph` mesmo no turno 0, antes do jogador revelar qualquer cena. Não é vazamento; é título de mapa.
- **Coerência com o princípio "conteúdo é dado".** Cap 2 estreia com seu próprio `map_title` no YAML; nem uma linha de frontend muda. Adicionar uma locação com ícone existente também é só YAML.
- **Trade-off conhecido — glifo desconhecido cai silenciosamente no pip.** O frontend não emite warning no console nem mostra placeholder de erro. Aceitável: tipo no YAML não derruba o mapa, só perde o ornamento. Reviewer humano nota durante validação visual.

## ADR-042 — Topologia narrativa pública vs estado oculto da cena

**Contexto.** O ADR-038 estabeleceu que `/graph` filtra cenas não-reveladas em sua totalidade: `id`, `name`, `position`, `icon`, conexões — nada vaza. Funciona para preservar segredo, mas o resultado visual é problemático: capítulo com 5 cenas começa o mapa com 1 ponto isolado. Mapa parece vazio; perde a função editorial de "carta antiga parcialmente conhecida". O gênero RPG/aventura usa o mapa parcialmente revelado como ferramenta narrativa — você sabe que há lugares por explorar; não sabe o que são.

**Opções consideradas.**
- **A — Mapa só com revelados (status quo de ADR-038).** Privacidade máxima, mapa visualmente vazio na maior parte do tempo.
- **B — Mapa com tudo aberto.** Visual completo desde o turno 0, mas vaza nomes/ícones/conexões — spoiler estrutural total. Fora de consideração.
- **C — Meio termo: existência da cena é pública; conteúdo é oculto.** O `id` e a `position` da cena trafegam (silhueta no mapa). `name`, `icon`, `description`, `read_aloud`, `present` (NPCs), `connections` permanecem sob filtro. O jogador vê "tem um ponto aqui no mapa" sem saber o que é.

**Decisão.** **Opção C — refinar o filtro de ADR-038: filtra *conteúdo*, expõe *existência*.**

Concretamente:
- Nova classe `VeiledNode` em `app/api/schemas.py` com **apenas dois campos**: `id: str` e `position: GraphNodePosition`. Sem `name`, sem `icon`, sem qualquer outro — o contrato é o próprio schema.
- `GraphResponse` ganha `veiled_nodes: list[VeiledNode] = Field(default_factory=list)`.
- `build_graph_response` adiciona um segundo loop sobre `chapter.scenes`: cenas que **não** estão no conjunto `revealed` viram `VeiledNode(id, position)`.
- `nodes` (revelados) continua com tudo. `edges` continua só entre dois revelados — arestas envolvendo veladas **não trafegam** (preserva adjacência narrativa; o jogador descobre conexões ao explorar).
- A `current_location` nunca é considerada velada — defesa em profundidade: mesmo que `locations_revealed` esteja inconsistente, a cena onde o jogador está aparece em `nodes`, não em `veiled_nodes`.

**Por que lista separada e não `revealed: bool` em `GraphNode`.** O contrato fica auto-evidente: `VeiledNode` literalmente *não tem* os campos sensíveis. Impossível esquecer de filtrar `name` ou `icon` num refactor futuro — o campo simplesmente não existe no schema. Teste de invariante fica mais limpo: "tudo em `nodes` foi revelado; tudo em `veiled_nodes` é só id+position".

**Por que arestas com pontas veladas não trafegam.** Vazar `taverna_interior → rua_da_praca` antes de a praça ser revelada conta para o jogador que existe um caminho direto entre os dois pontos — adjacência narrativa que o autor quis ocultar até o jogador chegar lá. As silhuetas aparecem isoladas no mapa; conforme o jogador explora, as arestas correspondentes surgem. Se na prática isso ficar visualmente fragmentado demais, ADR futuro pode introduzir `veiled_edges` (arestas onde pelo menos uma ponta é revelada) — não fechamos a porta.

**Por que `position` não é considerada vazamento.** Saber que existe um ponto em (700, 250) não reconstitui conteúdo. Sem nome, sem ícone, sem descrição, a silhueta não diz se é clareira, cidade ou templo. O vazamento é mínimo e simétrico a um mapa de pergaminho velho onde regiões aparecem como contornos sem detalhe — vocabulário do gênero, não falha de segurança.

**Consequências.**
- **Refinamento, não rompimento, do ADR-038.** O invariante "estado oculto não vaza" permanece — só explicita o que conta como "estado oculto" (conteúdo, não topologia). Teste de invariante existente é refatorado: ao invés de string match no JSON serializado, passa a verificar campo a campo (porque `id` velado pode aparecer em `veiled_nodes`).
- **Cinto + suspensório no teste.** `test_veiled_node_has_no_name_or_icon` faz verificação **negativa explícita** para cada campo sensível conhecido (`name`, `icon`, `description`, `read_aloud`, `present`, `connections`): assert que **NÃO** existe em `VeiledNode.model_fields`. Defesa contra "alguém adicionou campo aparentemente inocente no schema".
- **Frontend renderiza duas camadas SVG.** `.location-graph__veiled-nodes` antes de `.location-graph__nodes` (z-order), sem text/glyph nos veladados. Quando uma cena é revelada, "preenche" a silhueta — posição igual, ganha disco com nome e ícone.
- **`computeViewBox` passa a considerar `[...graph.nodes, ...graph.veiled_nodes]`.** Senão o auto-fit ignora as silhuetas e o mapa fica espremido do tamanho dos revelados.
- **Fase 6 fecha com mapa parecendo mapa.** Critério de fechamento: validação visual com pelo menos duas cenas reveladas conectadas (taverna → cozinha ou taverna → rua) — checar que a aresta aparece entre os dois revelados, as silhuetas restantes seguem isoladas, e o layout não fica esquisito. Se ficar, decisão imediata: implementa `veiled_edges` agora num commit incremental, ou aceita como está na v1.

---

## ADR-043 — Eval set dos agentes em pytest com marker `eval` (opt-in, contra LLM real)

**Contexto.** A Fase 7 exige avaliação sistemática do comportamento dos agentes — não basta os unit tests determinísticos do motor. Três alvos: `RefereeAgent` (Ruling estruturado), `NarratorAgent` (prosa), e a heurística de robustez (determinística). O ADK oferece um CLI de avaliação próprio (`adk eval`), e há a opção tradicional de testes pytest. Como integrar isso ao projeto, sem que vire fricção no CI ou despesa silenciosa de API?

**Opções consideradas.**
- **A — `adk eval` (CLI/SDK do ADK):** ferramenta nativa, formato de caso próprio. Pago em complexidade de integração e em formato adicional para manter. Não há ganho prático que justifique a curva — os checks que queremos (campo Pydantic, regex em prosa) são triviais em Python.
- **B — Snapshot mockado:** mock do provider de LLM com respostas fixas, validando que parser/contrato não regrediu. Roda em CI sem custo, mas **não testa o agente real** — vira teste de plumbing. Invalida a tese do eval set (saber se o LLM faz a coisa certa).
- **C — Pytest com marker `eval` opt-in, chamando Gemini real:** os casos vivem em YAML ao lado de cada teste; o marker `eval` excluído do default (CI verde sem custo); rodar exige `GEMINI_API_KEY` no ambiente e `pytest -m eval` explícito. Skip elegante quando a chave não está presente.

**Decisão.** **Opção C — pytest + marker `eval`, opt-in, contra Gemini real.**

Concretamente:
- `pytest.ini` registra o marker `eval` e o exclui via `addopts = -m "not eval"`. O CI default fica verde sem custo de API.
- Casos vivem em `tests/evals/{robustness,referee,narrator}/cases.yaml`, carregados via fixture `load_cases` em `tests/evals/conftest.py`.
- O fixture `require_gemini_key` (ou check inline no fixture do agente) skipa o módulo quando a chave não está presente.
- Cada agente eval constrói o agente real via `build_*_agent(provider)` + um `InMemorySessionService` (não precisa de Postgres para isolar a invocação do agente).
- Cobertura de `app/rules` (90% obrigatório) é desligada com `--no-cov` quando se roda `pytest -m eval`, porque eval não exercita o motor.

**Escopo dos checks por agente:**
- **Referee:** estrutural e tolerante. `precisa_rolagem` exato, `pericia` por keywords, `dificuldade` por faixa, `consequencia_*` por presença. Não exige string-match. 8 casos cobrindo rolagem necessária (alta/baixa dificuldade), trivial sem rolagem, perícias distintas.
- **Narrator:** apenas **regressão grossa** (esta é a decisão de escopo dura — não perseguir nota alta em avaliação de prosa). Três modos bloqueantes: (a) regra alucinada (regex por `\d+d\d+`, "rolagem", "DC", "perícia"), (b) meta-fala ("como mestre", "vou narrar"), (c) contradição direta de lore (substring quando o caso fornece `lore_contradictions`). Heurística sobre prosa é ruidosa por natureza — perseguir fluência é over-engineering.
- **Robustez:** determinístico, sem `eval` marker. Mede precision (0 falso-positivo em ações válidas) e recall por categoria (0 falso-negativo em ações abusivas óbvias). Casos borderline são reportados sem falhar o build — documentam a fronteira da heurística (ADR-026).

**Consequências.**
- **CI fica verde sem custo.** `pytest` na raiz roda 139 testes + skipa 10 (postgres-dependent) + deseleciona 2 (eval Referee/Narrator). Cobertura do motor em 100%.
- **Eval roda quando se quer.** Desenvolvedor com chave: `pytest -m eval --no-cov` ~30 chamadas de API, custo desprezível em Gemini Flash.
- **Limitações aceitas:** o eval do Narrator vai dar ruído inevitável — uma narração legítima pode citar "espada de duas mãos" e disparar regex de gore se mal calibrado, ou ignorar um lore implícito sem disparar o check. A defesa é (a) `expected_forbidden` precisos por caso, (b) escopo grosso explícito neste ADR.
- **Custo escala com casos.** Mais casos = mais chamadas. Por isso o set é enxuto: 8 cases no Referee, 6 no Narrator, ~30 (gratuitos) na Robustez.
- **Refinamento futuro:** se vier um classificador de robustez (ADR-026 deixa a porta aberta), o eval set já existe para compará-lo com a heurística antes de promover.
- **Não usamos `adk eval`** — porta aberta para v2 se o ADK adicionar features que justifiquem.

---

## ADR-044 — Abertura da v2 do Unscripted

**Contexto.** A v1 foi **fechada e publicada** em `origin/main` no commit `76d03fd` (16/16 critérios do PRD §10 validados, README/LICENSE/CONTRIBUTING em forma final, 43 ADRs registrados). Esse marco é imutável.

Para que o projeto continue evoluindo sem corromper o significado do "fechamento da v1", a abertura da v2 precisa ser registrada com a mesma formalidade — princípios herdados, fronteira clara, lista de entregas planejadas, e primeira entrega declarada. Sem esse ADR, a v2 vira "trabalho que aconteceu depois da v1", não uma versão com identidade própria.

**Decisão.** A **v2 está aberta a partir deste ADR**. O princípio inalterado da v2 (também herdado de ADR-021): **v2 é acoplamento, não reescrita**. Cada item da v2 deve aproveitar um gancho que já existe na v1 e expandi-lo — nunca refazer.

**Itens planejados da v2** (atualizados no PRD §11 e na decisão atualizada do ADR-021):
1. **Multi-provider LLM com split por agente** — ✓ **CONCLUÍDA** (ADR-045). Aproveita a camada de providers (ADR-009). 3 providers validados: Gemini (regressão zero), Groq (free tier — `llama-3.3-70b` para REASONING e `llama-3.1-8b-instant` para NARRATIVE), OpenAI (`gpt-4o-mini` — eval Referee 7/8, Narrator 6/6).
2. **Suporte a Vertex AI** — Fase 1.5, **pendente de decisão**. `GeminiVertexProvider` na mesma camada de providers, ativável via `LLM_PROVIDER=gemini_vertex`. Só faz sentido se o Unscripted rodar em produção GCP real. Como projeto de portfólio local/VPS, AI Studio basta. Sem prazo.
3. **Cross-provider por agente** — Fase 2, **pendente de necessidade**. Permitir `LLM_PROVIDER_REASONING` ≠ `LLM_PROVIDER_NARRATIVE` (mistura entre providers). Hoje, OpenAI e Groq cobrem ambos os propósitos satisfatoriamente — esta fase só vira necessária se evals futuros mostrarem que nenhum provider único serve bem aos dois lados. Pendente dos resultados de uso real.
4. Grupo de múltiplos personagens.
5. Criação de personagem.
6. Sistema de descanso e recuperação.
7. Inventário com uso real de itens.
8. Progressão entre capítulos.
9. Rolagem de dados transparente.
10. Voz (STT/TTS concreto — interface existe desde v1).
11. Segundo idioma (inglês — i18n existe desde v1).
12. Capítulo 2 e seguintes.

**Método de execução.** A v2 é executada em **Fases**, espelhando o método da v1, em um documento próprio: `docs/PLANO_IMPLEMENTACAO_V2.md`. A v1 fica imutável em `docs/PLANO_IMPLEMENTACAO.md`; a v2 evolui no novo documento. Razão: cada versão tem ciclo próprio, e arquivo separado preserva o histórico de execução de uma versão concluída sem inflar o documento original.

**Critérios de "v2 concluída"** (Definition of Done da v2 — alto nível; cada Fase define seus próprios critérios concretos):
- Multi-provider LLM funciona com pelo menos 2 providers além de Gemini, validado por eval set.
- Grupo de personagens, criação e descanso entregues com testes.
- Voz STT/TTS substitui o provider stub da v1.
- Inglês populado e troca de idioma funcional.
- Capítulo 2 jogável de ponta a ponta, no formato de aventura.
- Sem regressão nos critérios da v1 (PRD §10).

**Consequências.**
- A **identidade da v2** fica clara: "A mesa completa" (ADR-021) — aprofundamento sem mudança de natureza.
- A **fronteira v1/v2** fica explícita: v1 é o sistema-base jogável; v2 é o que torna a experiência uma mesa de RPG de fato.
- A **fronteira v2/v3+** continua intacta: v3+ muda a natureza do sistema (multi-usuário, contas, plataforma).
- A **primeira entrega** está declarada e tem ADR técnico próprio (ADR-045) — não inflate este ADR.
- O **roadmap** (PRD §11, ADR-021) foi atualizado em conjunto.

---

## ADR-045 — Multi-provider LLM via LiteLlm com split por agente (primeira entrega da v2)

**Contexto.** Este é o **primeiro ADR técnico da v2** (ver ADR-044 para o marco de abertura). Durante o smoke da Fase 7 da v1, a quota free-tier do Gemini esgotou no segundo turno do jogo (20 RPD em `gemini-2.5-flash`, erro `429 RESOURCE_EXHAUSTED`). A experiência fluida exige uma alternativa.

A camada de providers já existe (ADR-009) e expõe uma interface `LlmProvider` em `backend/app/providers/llm.py`. Só `GeminiAiStudioProvider` está implementado. Esta entrega adiciona **Groq** (foco, free tier muito mais generoso) e **OpenAI** (benchmark de qualidade + fallback pago confiável), com seleção por env var. **É demonstração concreta de competência multi-LLM**, que faz parte do propósito de portfólio do projeto (PRD §1).

**Opções consideradas.**
- **A — Sair do ADK** para algo provider-agnostic (LangChain, Pydantic AI). Reescrita grande, perde o investimento na ADK feito na v1.
- **B — Usar o wrapper `LiteLlm` do próprio ADK.** Cobre dezenas de providers via prefixo (`groq/...`, `openai/...`). `output_schema=Ruling` é convertido automaticamente para `response_format` da OpenAI/Groq pelo método `_to_litellm_response_format()` do ADK ([`google/adk/models/lite_llm.py:1788`](google/adk/models/lite_llm.py)). Streaming funciona via `litellm.acompletion(stream=True)`.
- **C — Manter Gemini com plano pago.** Resolve a quota mas não exibe a competência de multi-provider — perde a oportunidade de portfólio. Não atende à motivação central.

**Decisão.** **Opção B — `LiteLlm` do ADK.** Adicionar `GroqProvider` e `OpenAiProvider` em `backend/app/providers/llm.py`, ambos retornando `LiteLlm(model="<prefix>/<model>")`. Manter `GeminiAiStudioProvider` com signatura nova. `get_llm_provider(settings)` despacha por env var `LLM_PROVIDER`.

**Split por agente.** Cada provider declara dois modelos: `*_MODEL_REASONING` (Referee) e `*_MODEL_NARRATIVE` (Narrator/NPC). Se `NARRATIVE` é omitido, faz fallback para `REASONING` (single-model preservado). Razão: no Groq free tier, os modelos têm quotas radicalmente diferentes (`llama-3.3-70b-versatile` tem 1K RPD, `llama-3.1-8b-instant` tem 14.4K RPD). Split aproveita as duas quotas sem gargalo único.

**Modelos default propostos** (a serem confirmados por eval set):
- **Gemini:** `gemini-2.5-flash` para os dois propósitos (free tier limitado, mas serve para sanity).
- **Groq:** REASONING = `llama-3.3-70b-versatile` (ou `qwen/qwen3-32b` se o eval favorecer); NARRATIVE = `llama-3.1-8b-instant`.
- **OpenAI:** `gpt-4o-mini` para os dois propósitos (~$0.001/turno, structured output robusto).

**Validação.** Eval set existente (`tests/evals/referee/` e `tests/evals/narrator/`) roda contra cada provider:
- Referee: 4 candidatos Groq testados (`llama-3.3-70b`, `qwen3-32b`, `gpt-oss-120b`, `gpt-oss-20b`); melhor vira default.
- Narrator: `llama-3.1-8b-instant` testado para streaming + regressão grossa.
- OpenAI: `gpt-4o-mini` em ambos.

Resultado vai para `docs/PROVIDERS.md` (novo) — tabela comparativa com pass rate, qualidade observada, latência, custo.

**Consequências.**
- **O gancho da camada de providers (ADR-009) é validado na prática.** Não é mais "preparado para troca" — está trocado.
- **Quota não bloqueia mais o desenvolvimento.** Groq oferece ~1000 turnos/dia no split conservador; OpenAI oferece quota ilimitada para uso normal por ~$0.001/turno.
- **Demonstração de portfólio:** multi-provider + eval comparativo + escolha consciente de modelos é exatamente o tipo de competência que o projeto se propõe a exibir (PRD §1).
- **Sem reescrita do loop de turno.** `runner_turn.process_turn` continua exatamente igual; os providers são intercambiáveis no ponto de injeção.
- **Plan B documentado (não acionado):** se um modelo específico do Groq não respeitasse `response_format json_schema`, o eval set detectaria. Nesse caso, implementar parsing manual do Ruling com retry. Hipótese de muito baixa probabilidade — não foi acionada (modelo vencedor `llama-3.3-70b-versatile` passou). Não tem ADR técnico próprio; se vier a ser necessário no futuro, ganha um número novo na fila.
- **Limites conhecidos e aceitos:**
  - `litellm` adiciona ~5 MB ao container. Negligível.
  - Modelos Groq podem ter qualidade inferior ao Gemini Flash em casos complexos. Eval set mede isso.
  - OpenAI requer conta paga (mesmo que muito barata). Documentado em `.env.example` e `PROVIDERS.md`.

---

## ADR-046 — Promoção da Fase Voz para a próxima entrega da v2

**Contexto.** O `PLANO_IMPLEMENTACAO_V2.md` original listava Voz como Fase 9, atrás de Grupo de personagens, Criação de personagem, Descanso, Itens reais, Progressão e Rolagem transparente. A ordem das fases 3-11 era declarada como "proposta, pode ser revista entre fases" (PLANO_V2.md §1).

Durante o uso real do jogo após a Fase 1 da v2, o dono do projeto identificou que **a voz tem mais valor de portfólio e de experiência que as outras fases pendentes**:

- Voz fecha a promessa "RPG de mesa conversacional" — a metáfora literal da palavra "conversacional".
- Voz é demonstração concreta de **dois SDKs distintos** (Groq Whisper + OpenAI TTS) atrás da camada de providers — reforça o gancho de ADR-009.
- Voz é trabalho **vertical e contido** (~3-4 dias), enquanto Grupo de personagens é refactor profundo do modelo de estado (`character: Character` → `party: list[Character]`) que afeta loop de turno, persistência e UI ao mesmo tempo — uma fatia muito maior.
- A interface de voz já existe desde a v1 como stub (ADR-014). Promover é "completar a fundação", não "abrir frente nova".

**Opções consideradas.**
- **A — Manter ordem original** (Voz = Fase 9). Coerente com o que estava escrito, mas ignora a recalibração que o uso real permite.
- **B — Promover Voz para a próxima fase.** Reordena 3-11. Compatível com a regra explícita do PLANO_V2 §1 ("a ordem é uma proposta — pode ser revista").
- **C — Promover Inglês** (Fase 10). Aproveita a infra de i18n da v1, mas é trabalho de **conteúdo** mais que arquitetura — menos valor de portfólio e menos vertical.

**Decisão.** **Opção B.** Voz vira a próxima entrega da v2. As demais fases (Grupo, Criação, Descanso, Itens, Progressão, Rolagem transparente, Inglês, Capítulo 2) permanecem como esboço futuro no `PLANO_IMPLEMENTACAO_V2.md` §"Fases 3-11", a serem detalhadas no momento de cada uma.

**Consequências.**
- `PLANO_IMPLEMENTACAO_V2.md` é atualizado para refletir Voz como próxima fase concreta; as demais ficam como "futura" sem ordem cravada.
- A primeira entrega técnica da fase ganha ADR-047 (providers concretos de voz).
- A regra "ordem é proposta" (PLANO_V2 §1) é exercitada — registro deste ADR é a forma de manter isso visível em vez de mudança silenciosa.

---

## ADR-047 — Voz: providers concretos (Groq Whisper STT + OpenAI gpt-4o-mini-tts TTS) e separação de interfaces

**Contexto.** A camada de voz nasceu na v1 (ADR-014) como **stub**: `VoiceProvider` Protocol único com `transcribe` + `synthesize`, e `StubVoiceProvider` retornando vazio. Era proporcional ao escopo da v1: a UI completa, o pipeline pronto, zero dependência externa de áudio.

Promovida a Voz para a próxima fase da v2 (ADR-046), implementações concretas precisam entrar. Restrição de arquitetura: o sistema sobe via `docker compose up` portável e idêntico em local e VPS (ADR-010) — sem GPU, sem assets pesados, sem binários extras.

**Opções consideradas.**

Para **STT (jogador → texto)**:
- Groq Whisper (`whisper-large-v3-turbo`): free tier generoso (~14.4K RPD em `*-turbo`), API simples, latência ~1s para ~30s de áudio, PT-BR direto, chave Groq já no `.env`.
- OpenAI Whisper: ~$0.006/min, mesma qualidade — mais caro, sem vantagem prática.
- Whisper local (`faster-whisper`, `whisper.cpp`): zero custo de API mas adiciona binário/modelo pesado ao container; arranha portabilidade.
- AssemblyAI / Deepgram: bons mas adicionam SDK e custo sem vantagem clara.

Para **TTS (texto → jogador)**:
- OpenAI `gpt-4o-mini-tts`: PT-BR nativo, streaming de áudio, ~$0.015/1K chars, chave OpenAI já no `.env`.
- ElevenLabs: qualidade superior em PT-BR, mas custo ~10x e mais um SDK.
- TTS local (Coqui, Bark): quebra portabilidade (modelos grandes, possivelmente GPU). **Descartado por princípio.**
- OpenAI `tts-1` (gen anterior): mais barato mas qualidade inferior.

Para **a interface no código**:
- Manter `VoiceProvider` único: força implementação a fazer STT **e** TTS, ou um dos dois ser stub. Não escala — Groq não tem TTS bom, OpenAI não tem STT competitivo. Acopla coisas que não pertencem juntas.
- **Separar em `SttProvider` × `TtsProvider`:** cada um com sua env var (`STT_PROVIDER`, `TTS_PROVIDER`). Implementações podem ser mixadas (`STT_PROVIDER=groq + TTS_PROVIDER=openai`).

**Decisão.**

- **STT:** `GroqWhisperProvider` em `backend/app/providers/stt.py`, via `litellm.atranscription(model="groq/whisper-large-v3-turbo", ...)`. Coerência com a Fase 1 da v2 (litellm já é o wrapper escolhido — ADR-045).
- **TTS:** `OpenAiTtsProvider` em `backend/app/providers/tts.py`, via `litellm.aspeech(model="openai/gpt-4o-mini-tts", ...)`. Coerência idem.
- **TTS local descartado** por princípio de portabilidade (ADR-010): qualquer provider de voz no container precisa ser uma API HTTP, não um binário/modelo grande.
- **Interface separada:** `SttProvider` (`transcribe`) e `TtsProvider` (`synthesize`, `synthesize_stream` opcional). `VoiceProvider` unificado da v1 é removido — `Stub*` migra para cada lado. Sem backwards-compat (não paga o aluguel — Princípio 2).
- **Stubs preservados:** `StubSttProvider` e `StubTtsProvider`. Útil em CI sem chaves e em dev quando se quer eliminar custo.

**Consequências.**
- `backend/app/providers/voice.py` é apagado; nasce `stt.py` + `tts.py`.
- `backend/app/config.py`: campo `voice_provider` removido; nascem `stt_provider`, `tts_provider`, `groq_stt_model`, `openai_tts_model`, `openai_tts_voice`.
- `backend/app/runner.py`: `_voice_provider` vira `_stt_provider` + `_tts_provider`. Accessor `get_voice_provider_cached` é substituído por `get_stt_provider_cached` + `get_tts_provider_cached`.
- `backend/app/api/voice.py`: endpoints `/voice/stt` e `/voice/tts` despacham para os providers corretos.
- `.env.example`: seção "Voz" com as variáveis novas e custo aproximado documentado.
- A interface do botão de gravar (frontend) **não muda** — herda comportamento.
- Mix de provedores fica explícito: Groq para STT (free tier), OpenAI para TTS (qualidade + streaming + PT-BR nativo). Não está acoplado: amanhã, trocar TTS para ElevenLabs é escrever um `ElevenLabsTtsProvider` e mudar uma env var.

---

## ADR-048 — Sincronia texto+voz no nível de frase, orquestrada pelo backend

**Contexto.** Com TTS turno-inteiro funcionando (ADR-047 + ADR-049), o áudio chega depois do texto terminar: backend gera narração completa (~10-20s), frontend recebe `done`, só então POSTa pro `/voice/tts`, OpenAI gera MP3 do texto inteiro (~2-5s). Total: o áudio começa visivelmente atrasado em relação ao texto. Quebra a promessa de "voz na mesma pegada do texto" que motiva a feature.

A questão central é: **onde reside a fonte de verdade do tempo da narração?** No backend, que vê os chunks do LLM primeiro. Qualquer sincronia precisa nascer ali.

**Opções consideradas.**

- **A — Sincronia no nível de FRASE, backend orquestra (A1).** `process_turn` mantém um buffer dos chunks do Narrator; quando detecta fim de frase (regex `[.!?…]\s+` ou `\n`), dispara `asyncio.create_task(tts.synthesize(frase))` em background e emite `audio_sentence` (base64 + índice) no **mesmo SSE** do texto. Frontend enfileira por ordem de índice. Custo: ~$0.001/turno, complexidade baixa, sem deps novas, encaixa na estética editorial do projeto.

- **A2 — Sincronia de frase, frontend orquestra.** Mesmo conceito mas o frontend detecta fim de frase e chama `POST /voice/tts` por frase. Duplica a lógica de detecção (back + front), expõe a chave OpenAI via mais roundtrips, e o backend perde visibilidade do que o jogador ouve. Rejeitada.

- **B — Sincronia no nível de PALAVRA (karaokê).** Cada palavra do texto "acende" quando o TTS a fala. Exige timestamps por palavra: OpenAI Realtime API (WebSocket novo, ~10x custo), forced alignment local (lib pesada, possivelmente GPU), ou re-Whisper do áudio gerado (dobra custo + latência). Karaokê palavra-a-palavra é UX explicitamente de produto de IA (Spotify lyrics, Suno) — choca com a identidade "livro-jogo editorial" que a Fase 6 da v1 protegeu. Rejeitada.

**Decisão.** **Opção A1 — sincronia de frase, backend orquestra.**

Razões:
- **Princípio "frontend só fala com backend".** Toda chamada à OpenAI fica em `providers/tts.py`. A2 arranharia esse isolamento.
- **Fonte de verdade do tempo.** O backend vê os chunks do LLM primeiro — detector de frase mora onde a informação chega primeiro. Frontend só consome áudio pronto.
- **Complexidade proporcional.** Detector de frase é regex puro; `useAudioQueue` no frontend já existe e toca em sequência. Sem dependência nova.
- **Estética.** Karaokê palavra-a-palavra (B) custaria uma semana+ e dependência nova para ganhar, na melhor hipótese, ~1s de latência, e pioraria a sensação de "leitura editorial" para a de "produto de IA". B custa mais e piora o produto na dimensão estética.

**Especificação técnica.**

1. **`SentenceBuffer`** em `backend/app/agents/sentence_buffer.py`: função pura que recebe chunks de texto e emite frases completas. Detector de fim de frase: `[.!?…]\s+` ou `\n`. Trata: decimais (`3.5`), reticências (`…` e `...`), ponto final fim-de-buffer (sem trailing space), abreviações comuns (`Sr.`, `etc.`, `Dr.`), aspas/itálicos colados ao terminador. Testes determinísticos por caso.

2. **`_stream_agent_text` em `runner_turn.py`** integra `SentenceBuffer`. Quando frase fecha: `asyncio.create_task(tts_provider.synthesize(frase, voice=...))`. Cada task tem índice sequencial. Quando o áudio fica pronto, yield `TurnEvent(type="audio_sentence", index=i, audio_b64=..., mime="audio/mpeg")` no mesmo gerador — mantém ordem por índice no frontend.

3. **`ActionRequest.tts_enabled: bool = False`** no Pydantic do endpoint `/action`. `action_endpoint` propaga para `process_turn`. Quando `False`, **zero chamadas** à OpenAI são feitas — custo zero quando off (default).

4. **Frontend**: `ActionEvent` ganha variante `audio_sentence`. `sse.ts` parseia o novo tipo. `Play.tsx` decodifica base64 → Blob → `useAudioQueue.enqueue(blob)`. Sem mudança no `useAudioQueue` existente — turno-inteiro vira N enqueues sequenciais.

5. **Tratamento de falha (ADR-020 estendido).** Se TTS de uma frase falhar/timeout, log estruturado, evento `audio_sentence` daquela frase **não** é emitido, próxima frase segue. Texto não é afetado. Trace do turno registra `tts_errors`.

6. **Toggle off mid-turno.** Frontend: `useAudioQueue.clear()` para áudio e descarta fila. Backend já não vai gerar mais (vê `tts_enabled` no turno seguinte). Áudios em-voo do turno atual chegam e são descartados pelo frontend.

**Consequências.**

- **Cadência casa.** Primeira frase de áudio chega ~1-2s depois da frase aparecer no texto. Depois empata. "Mesma pegada" cumprida.
- **TTS turno-inteiro do Bloco 2** é substituído. O caminho `Play.tsx → ttsToBlob(narraçãoCompleta) → useAudioQueue` é removido — passa a vir tudo pelo SSE.
- **Sem mudança na fila de áudio.** `useAudioQueue` já toca em sequência; agora recebe N blobs por turno em vez de 1. Comportamento idêntico ao jogador.
- **Custo total não muda.** Mesma quantidade de chars sintetizados; só fragmentado em chamadas menores. Pode até reduzir picos de latência da OpenAI.
- **Cache de TTS por frase** (otimização futura) fica natural — frases repetidas tipo "Você não consegue." poderiam ser cacheadas. Fora de escopo agora.

**Limites conhecidos e aceitos.**
- Frases muito curtas (`"— Não."`) viram chamadas TTS isoladas com overhead per-request alto. Aceitável; custo absoluto continua negligível.
- Se a primeira frase do Narrator demora a fechar (LLM emite chunks longos), a latência da 1ª frase de áudio aumenta proporcionalmente. Sem mitigação no Bloco 3; volta a aparecer só se observado.
- Se um caractere terminador de frase for emitido em chunks separados (ex.: chunk1=`"alerta"`, chunk2=`"."`, chunk3=`" Observando"`), o detector ainda funciona porque o buffer concatena antes de procurar terminadores. Coberto nos testes.

---

## ADR-049 — Toggle de narração falada no frontend; voz default `echo`

**Contexto.** Com o TTS real entrando (ADR-047), todo turno pode virar áudio falado. Mas nem todo jogador quer voz: alguns leem mais rápido que ouvem, outros estão em ambiente que não comporta som, outros simplesmente querem custo zero (cada turno com TTS ON dispara uma chamada de ~$0.001 ao gpt-4o-mini-tts). Sem um toggle, o jogador é refém de uma escolha global.

Duas decisões precisam ficar registradas: **(1)** onde mora o estado do toggle e **(2)** qual é a voz default.

**Opções consideradas — (1) onde mora o toggle:**
- **A — `localStorage`, default off, frontend-only.** Persiste entre F5/sessões, custo zero quando off, sem precisar autenticação.
- **B — Parte do `GameState` (persistido no Postgres).** Per-partida. Mais "rico" mas exige migration + endpoint para atualizar. Não paga o aluguel hoje (Princípio 2) — voz é preferência do dispositivo, não da campanha.
- **C — Cookie.** Mesmo que A mas com semântica de servidor — sem vantagem real, perde a chave clara `unscripted.tts_enabled`.

**Opções consideradas — (2) voz default:**
A OpenAI oferece 11+ vozes em `gpt-4o-mini-tts` (alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse). Para a v1 da fase de voz, geramos amostras das 5 mais comumente recomendadas para narração — `alloy` (neutra default), `sage` (calma), `echo` (grave, sóbria), `coral` (feminina expressiva), `shimmer` (feminina luminosa). O dono ouviu os MP3s gerados a partir do `read_aloud` da starting_scene do capítulo 1 (`scripts/sample_tts_voices.py`).

**Decisão.**

- **Toggle:** Opção A. Hook `useTtsToggle` em `frontend/src/state/useTtsToggle.ts` lê/escreve em `localStorage` na chave `unscripted.tts_enabled` (valores `"true"` | `"false"`). Default **off**. Sincroniza entre abas via evento `storage`. Falha de `localStorage` (contexto inseguro) cai pra memória — não fatal.

- **Voz default:** **`echo`**. Tom grave e sóbrio que casa com a estética de "livro-jogo editorial" do Unscripted (a regra inegociável da skill `mestre-frontend`: nada de cara de "produto de IA"). Vozes mais "brilhantes" como `shimmer` ou expressivas como `coral` puxam pra estética de assistente virtual; vozes neutras como `alloy` ficam genéricas. `echo` favorece a sensação de **mestre conduzindo a narrativa** em vez de IA falando texto.

- **Mecanismo de override:** voz é configurável por env (`OPENAI_TTS_VOICE`). Trocar é editar o `.env` e reiniciar — sem rebuild. Útil para A/B local sem mudar código.

**Consequências.**

- `frontend/src/state/useTtsToggle.ts`: hook + persistência.
- `frontend/src/components/TtsToggle.tsx`: botão no header da zona play, ícone alto-falante (riscado quando off).
- `frontend/src/state/useAudioQueue.ts`: fila de áudios que toca em sequência. `clear()` interrompe quando o toggle desliga mid-turno.
- `Play.tsx`: quando `done` chega no SSE **e** `ttsEnabled === true`, chama `POST /voice/tts` com a narração consolidada do turno e enfileira o blob. Quando o toggle desliga, chama `audioQueue.clear()`.
- `.env.example` e `.env`: `OPENAI_TTS_VOICE=echo`.
- Esta decisão fecha o Bloco 2 do plano da fase de voz: TTS turno-inteiro funcional, com toggle. Sincronia frase-a-frase (Bloco 3) chega em seguida usando exatamente esta mesma fila — só muda como o backend produz os áudios.

**Limites conhecidos.**
- A voz default vale para todos os jogadores. Per-jogador exigiria persistir em `localStorage` também — fora de escopo da Fase Voz; volta como item futuro se aparecer pedido real.
- A escolha de `echo` foi feita por **uma** pessoa (o dono) ouvindo as 5 amostras em um trecho do capítulo 1. Não é eval sistemático. Se outro jogador achar `echo` ruim, basta trocar a env — não é cara-de-pau cravar default sem dado massivo, porque o produto tem hoje exatamente um jogador alvo.

---

Esta seção é um lembrete: o planejamento cobriu as decisões estruturais, mas pontos novos surgirão quando o código encostar na realidade. Quando surgirem, decidir com base nos princípios (`ARQUITETURA.md` §2) e **registrar aqui** como um novo ADR. Não antecipar 100% agora — isso seria over-engineering aplicado ao planejamento.
