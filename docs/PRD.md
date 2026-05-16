# PRD — Documento de Requisitos do Produto

**Projeto:** Unscripted
**Tipo:** RPG de mesa single-player com Game Master de Inteligência Artificial
**Status:** Planejamento — pré-implementação
**Idioma deste documento:** Português

> Este documento descreve **o quê** o sistema faz e **por quê**, de forma independente de implementação. As decisões técnicas de **como** estão no `ARQUITETURA.md`. O histórico e a justificativa de cada decisão estão no `DECISOES.md`. Os três documentos são vivos e crescem a cada versão.

---

## 1. Visão geral e propósito

O Unscripted é uma aplicação web que permite a uma pessoa jogar uma aventura de RPG de mesa tendo a Inteligência Artificial no papel de **Game Master** (mestre do jogo): a entidade que narra o mundo, interpreta os personagens não-jogáveis, arbitra as ações do jogador e descreve as consequências.

O projeto tem dois propósitos simultâneos e igualmente válidos:

1. **Ser um projeto de portfólio de AI Engineer.** Demonstrar domínio de orquestração multi-agente, RAG, design de sistemas com IA, e — principalmente — o discernimento de **saber o que NÃO entregar a um LLM**. O valor do projeto está nas decisões de engenharia, não no volume de funcionalidades.
2. **Ser um produto real e jogável.** Mesmo sendo um projeto de estudo, deve ser uma experiência genuína que possa, no futuro, ajudar pessoas que queiram jogar. Toda decisão é tomada pensando pelo lado do jogador.

## 2. Contexto: o que é RPG de mesa e o papel do Game Master

Esta seção existe para que qualquer pessoa que pegue o repositório sem conhecer RPG entenda o domínio.

**RPG de mesa é uma conversa estruturada.** Não há menus, não há botões de ação, não há movimentação por grid. O loop fundamental é: o Game Master descreve uma situação → o jogador diz, em linguagem livre, o que seu personagem **tenta** fazer → o Game Master determina o resultado → o Game Master descreve a nova situação. Repete.

A palavra central é **tenta**. O jogador declara intenção, nunca resultado. "Eu armo uma emboscada para o cavaleiro" significa "eu tento armar uma emboscada" — quem decide se funciona é o Game Master, cruzando a intenção com a realidade do mundo.

**O Game Master é um árbitro-narrador.** Numa mesa real é um dos participantes que assume esse papel: ele narra, interpreta os NPCs, descreve o mundo e arbitra o que acontece. Não é um personagem visível na história — é a voz que conduz. O "rosto" do Game Master, nesta aplicação, é o texto bem escrito e bem apresentado, não uma figura na tela.

**O conceito de estado oculto.** O mundo contém informação que o jogador não vê: o cavaleiro é um veterano treinado contra emboscadas; o baú é armadilhado; o taverneiro está mentindo. Esse estado existe **antes** de o jogador agir. O Game Master não inventa na hora que a emboscada falha — ele consulta o que já era verdade e revela através da consequência. Essa **resistência do mundo** é o que separa um jogo de uma escrita colaborativa complacente.

**O visual de uma mesa real é mínimo e funcional:** uma ficha de personagem (números do herói), os dados, e às vezes um diagrama de posições no nível de abstração de um tabuleiro de xadrez. O meio do RPG de mesa é o texto. Isso não é uma versão pobre do RPG — é o que o RPG é, e é por isso que combina com LLM.

## 3. Conceito do produto

O Unscripted é, em essência, um **livro-jogo conversacional**: o jogador progride por uma história em capítulos, e em vez de escolher entre opções pré-escritas, **descreve livremente** o que quer fazer. Combina a liberdade de uma mesa de RPG com a acessibilidade de uma aplicação single-player.

A referência mental: imagine um jogo de ficção interativa só-texto (estilo Zork) modernizado — com um painel de personagem ao lado, um mapa de progresso, feedback visual reativo, e um mestre que entende linguagem natural livre em vez de comandos fixos.

## 4. Público-alvo

- **Jogador final:** uma pessoa que quer jogar uma aventura de RPG sozinha, sem precisar reunir um grupo nem encontrar um mestre humano.
- **Comunidade técnica:** desenvolvedores que encontram o repositório público e querem estudar, rodar ou contribuir.

## 5. O loop de turno (requisito funcional central)

Todo o sistema gira em torno de processar uma ação do jogador. O loop, ilustrado com o exemplo da emboscada ao cavaleiro:

O jogador escreve: *"quero armar uma emboscada para o cavaleiro, pegá-lo de surpresa."*

1. **Interpretar a intenção** — entender que o jogador quer um ataque furtivo com vantagem de surpresa.
2. **Consultar o estado oculto e as regras** — o cavaleiro tem estado que o jogador não conhece ("veterano, treinado contra emboscadas, percepção alta"). Isso está registrado no estado do jogo / no conteúdo do capítulo, não é improvisado.
3. **Arbitrar** — cruzar intenção com realidade: isso vira um teste de Furtividade contra a Percepção do cavaleiro; como ele é experiente, a dificuldade é alta. Os termos são definidos pelo julgamento; os números, pela regra.
4. **Resolver** — rolar os dados. Determinístico. Suponha que o jogador falhe.
5. **Aplicar consequências** — a regra define o resultado mecânico: a emboscada falha, o cavaleiro percebe, o jogador perde a vantagem e talvez sofra o primeiro golpe. HP é atualizado.
6. **Narrar** — transformar o resultado mecânico em história, em linguagem natural, mantendo o tom e a coerência com o mundo.

Esse é o turno completo, e é **o** fluxo do jogo — não um caso especial de combate. Toda ação do jogador percorre essas etapas (algumas podem ser puladas quando não se aplicam, ex.: uma ação trivial sem necessidade de rolagem).

## 6. Requisitos funcionais

### 6.1. Personagem do jogador
- Na v1, o jogador escolhe entre **dois personagens pré-prontos**: **Guerreiro** e **Paladino**. Cada um com ficha completa (atributos, HP, perícias, equipamento inicial) definida no conteúdo do jogo.
- Criação de personagem customizada é funcionalidade de v2.

### 6.2. Estado do jogo
O sistema mantém, de forma persistente, o estado completo de uma partida:
- Ficha do personagem (atributos, HP atual e máximo, nível).
- Inventário (itens que o personagem possui).
- Localização atual dentro do grafo de locações.
- Flags de progresso / objetivos da aventura (estado de quests, eventos já ocorridos).
- Histórico relevante do que aconteceu (para coerência narrativa).

### 6.3. Salvar e continuar
- O jogador pode fechar o navegador no meio de um capítulo e retomar exatamente de onde parou.
- Na v1 isso é feito via **identificação anônima por ID de sessão** — sem cadastro, sem e-mail, sem senha. O sistema gera um ID; o jogador retoma a partida por ele.
- Contas de usuário com login são funcionalidade de v2.

### 6.4. Interface — três zonas
A tela do jogo é composta de três zonas:
- **Zona de narração** (centro, coração da experiência): onde o texto do Game Master aparece e onde o jogador escreve o que quer fazer. Tratada com cuidado editorial — boa tipografia, fala de NPCs destacada, texto que "flui" com ritmo em vez de aparecer em bloco.
- **Painel de estado** (lateral): mostra o que o jogador precisa saber sem perguntar — HP, nível, inventário, localização atual, objetivos. É a versão digital da ficha de personagem. Mostra apenas o que o jogador **conhece** (não revela estado oculto).
- **Zona de cena** (mapa/grafo): o grafo de locações que se revela conforme o jogador explora, com marcador na posição atual. É um diagrama de navegação, não uma paisagem.

### 6.5. Grafo de locações
- O "mapa" do jogo é um **grafo**: nós (locações) conectados por arestas (passagens), com a posição atual destacada.
- O grafo é **derivado dos dados do capítulo** — não é arte desenhada nem imagem importada. Ao escrever um capítulo no formato estruturado de aventura, as locações e suas conexões já ficam definidas; o grafo é esses dados renderizados.
- As locações se revelam progressivamente conforme exploradas.

### 6.6. Feedback visual reativo (v1)
A interface reage ao que acontece na narrativa, para que a tela seja **viva** sem precisar de representação de personagens. Tudo via animação de UI (CSS e transições leves), zero assets gráficos:
- Reação de dano: a tela pulsa em vermelho nas bordas; o HP no painel anima a queda, fica vermelho, treme.
- Rolagem de dado visível: o dado gira na tela antes de revelar o resultado.
- Transição entre locações: o nó acende no grafo, a transição tem peso.
- Fluxo de texto da narração com ritmo.
- Destaque de momentos-chave: acerto crítico, derrota de um inimigo, descoberta de tesouro disparam um efeito de realce na zona de narração.

### 6.7. Painel de "pensamento do mestre"
- Um elemento recolhível (ex.: uma seta na parte inferior) que expõe o **raciocínio do Game Master** sobre o turno: o ruling (precisava de rolagem? qual a dificuldade e por quê?), o resultado dos dados, e o que motivou a consequência — por exemplo, "o cavaleiro é experiente e já esperava a emboscada".
- Não aparece automaticamente na narração; fica escondido e disponível sob demanda. Serve tanto ao jogador curioso quanto ao debug (ver seção de observabilidade no `ARQUITETURA.md`).

### 6.8. Feedback de processamento
- O loop de turno envolve várias chamadas de LLM em sequência e leva alguns segundos. A interface deve dar feedback claro ("o mestre está pensando...") em vez de parecer travada.

### 6.9. Conteúdo: histórias e capítulos
- O sistema **não é engessado em uma única história**. O motor roda **qualquer** história escrita no formato estruturado de aventura — o conteúdo é dado de entrada, não código. "Múltiplas histórias" é uma **capacidade nativa** do sistema, não uma funcionalidade futura; o que muda com o tempo é apenas a *quantidade de conteúdo* disponível.
- A v1 entrega o sistema-base capaz de rodar qualquer história, com **uma história e o capítulo 1 dela** como conteúdo inicial — completo e jogável do início ao fim.
- O conteúdo de aventura vive como **arquivo versionado** no repositório (fonte de verdade) e é **ingerido para o banco de dados** na inicialização. Em tempo de execução o jogo lê do banco. Ver `ARQUITETURA.md` e `DECISOES.md` (ADR-023).
- A história é contínua e não tem "fim" definitivo: o capítulo 1 termina e dá gancho para o capítulo 2, que ainda não existe. Não há tela de "Fim de jogo" — há continuidade de campanha.
- A v1 não precisa de menu de campanha nem de seleção de capítulo/história: começa no capítulo 1 da história inicial, joga, e encerra com o gancho para o próximo.

## 7. Requisitos não-funcionais

### 7.1. Segurança
O código será **público** e rodará em VPS. Segurança é requisito de primeira classe:
- Segredos (chaves de API) nunca versionados; geridos por variáveis de ambiente, com arquivo de exemplo versionado.
- A chave da API do LLM vive apenas no backend, nunca exposta ao frontend.
- Toda entrada do jogador é texto livre destinado a um LLM — portanto **injeção de prompt é tratada como vetor de ataque real**, com mitigação documentada.
- O retorno do LLM é validado e sanitizado antes de ser aplicado ao estado do jogo.
- Rate limiting nos endpoints; CORS configurado corretamente.
- Detalhes técnicos no `ARQUITETURA.md`.

### 7.2. Privacidade
- A v1 não coleta nenhum dado pessoal (decorrência da autenticação anônima por ID).
- Quando contas de usuário forem introduzidas (v2), as implicações de proteção de dados (incluindo LGPD) e política de privacidade passam a ser requisitos explícitos.

### 7.3. Performance
- Latência de alguns segundos por turno é aceitável na v1, dado o número de chamadas de LLM. O requisito é que a interface comunique o processamento, e que o estado **nunca** seja corrompido por uma resposta lenta.

### 7.4. Portabilidade
- A aplicação é **portável e conteinerizada**: roda de forma idêntica em ambiente de desenvolvimento local e em VPS. Mudar de ambiente é trocar variáveis de ambiente e fazer deploy do mesmo container — não há reescrita.

### 7.5. Internacionalização (i18n)
- A **arquitetura** de múltiplos idiomas entra na v1: nada de texto engessado no código, estrutura preparada para troca de idioma.
- Na v1, apenas o **português** é populado (interface + conteúdo do capítulo 1). O **inglês** e a troca de idioma em si são funcionalidade de v2.
- Observação: a camada de regras referencia o SRD 5.1, cujo texto oficial é em inglês; a narração e o conteúdo de aventura são em português.

### 7.6. Observabilidade
- O sistema registra as decisões dos agentes (o ruling, o resultado dos dados, o retorno de cada agente) para permitir entender **por que** o Game Master decidiu algo. É barato de implementar e é boa prática de AI Engineering.

### 7.7. Robustez a falhas externas
- O LLM é uma dependência externa que pode falhar, demorar ou exceder limites. Nessas situações, a aplicação trata o erro com elegância: informa o jogador ("tivemos um problema no processamento, tente novamente"), **não consome o turno**, e **não perde a mensagem do jogador** — devolve ao estado anterior com a mensagem (ou áudio) preservada na caixa de envio.

## 8. Regras de robustez do Game Master

O Game Master deve se manter no papel e no escopo do jogo independentemente do que o jogador escreva. Duas categorias de situação:

### 8.1. Ação impossível ou que quebra o jogo
Quando o jogador tenta declarar um resultado em vez de uma intenção, ou algo impossível ("eu mato o cavaleiro instantaneamente e pego o tesouro"):
- O turno **não é processado** como jogada normal.
- A interface exibe um **aviso vermelho destacado** informando que aquilo não é uma ação válida.
- O jogador pode jogar novamente. O mundo resiste — o Game Master nunca concede um resultado só porque foi pedido.

### 8.2. Tentativa abusiva ou fora de personagem
Quando o jogador tenta usar o campo de texto para tirar o LLM do papel, fazer injeção de prompt, ou inserir conteúdo impróprio:
- Mesmo tratamento: o turno não acontece, e um **aviso vermelho destacado** é exibido informando que aquela é uma prática abusiva.
- O Game Master se mantém no personagem e no escopo do jogo aconteça o que acontecer.

Essas regras são implementadas tanto no prompt dos agentes quanto em validação determinística — ver `ARQUITETURA.md`.

## 9. Política de conteúdo sensível

RPG envolve combate, perigo e morte — isso é parte do gênero e é permitido. A linha:
- **Permitido:** violência de fantasia no nível de um livro de aventura (combate, ferimentos, morte de personagens) descrita sem gráficos gratuitos.
- **Proibido:** gore gratuito, violência em nível muito alto, conteúdo sexual, e temas pesados que exigiriam aviso de conteúdo.
- Quando o jogador tenta levar a narrativa para território proibido, aplica-se o mesmo tratamento das regras de robustez: o turno não acontece e um **aviso vermelho destacado** é exibido.
- Essa política é diretriz para os prompts dos agentes e para o design dos capítulos.

## 10. Critérios de aceitação da v1 (Definition of Done)

A v1 está pronta quando **todos** os itens abaixo são verdadeiros:

- [ ] O jogador consegue jogar o Capítulo 1 da história inicial do início ao fim.
- [ ] O motor é capaz de rodar qualquer história no formato estruturado de aventura (a v1 popula uma).
- [ ] O jogo funciona de ponta a ponta em pelo menos um idioma (português).
- [ ] O jogador escolhe entre Guerreiro e Paladino pré-prontos.
- [ ] O Game Master narra, interpreta NPCs, arbitra ações e aplica consequências corretamente, seguindo o loop de turno.
- [ ] O estado do jogo (HP, inventário, localização, progresso) persiste, e a partida pode ser retomada pelo ID anônimo.
- [ ] O grafo de locações reflete a posição real do jogador e se revela conforme a exploração.
- [ ] A interface tem as três zonas funcionando (narração, painel de estado, zona de cena).
- [ ] O feedback visual reativo está presente (reação de dano, rolagem de dado, transições, destaque de momentos-chave).
- [ ] O painel de "pensamento do mestre" está disponível e mostra o raciocínio do turno.
- [ ] As regras de robustez do Game Master funcionam: ações impossíveis, abusivas e conteúdo proibido são barradas com o aviso vermelho, sem consumir o turno.
- [ ] Falhas do LLM são tratadas sem corromper estado e sem perder a mensagem do jogador.
- [ ] A interface de voz existe (ainda que a implementação de STT/TTS seja v2).
- [ ] A arquitetura de i18n está pronta (apenas português populado).
- [ ] Segredos não estão versionados; `.env.example` existe; a aplicação sobe via Docker Compose de forma idêntica local e em VPS.
- [ ] Repositório público com README, licença, e guia básico de contribuição.

## 11. Roadmap — organização por temas

O roadmap é organizado por **temas**, não por listas soltas de features. Cada salto de versão tem uma identidade clara.

### v1 — O sistema-base jogável
Todo o sistema funcionando para **um jogador, um personagem**. O motor roda qualquer história no formato de aventura; a v1 inclui **uma história com o capítulo 1** como conteúdo inicial. É um jogo completo e jogável — não um pedaço. Inclui tudo das seções 5 a 10 acima.

### v2 — "A mesa completa"
Aprofunda a fidelidade ao RPG de mesa, **mantendo a natureza single-player e a arquitetura da v1**. Tudo aqui é expansão de um jogo que já existe:
- **Grupo de múltiplos personagens** — um jogador controlando uma party de 3-4 personagens (não confundir com multiplayer; ainda é single-player). Provavelmente o item mais fiel à essência do RPG de mesa.
- **Criação de personagem** — escolher raça, classe, distribuir atributos, em vez dos pré-prontos.
- **Sistema de descanso e recuperação** — acampar, recuperar HP, repreparar magias; o ciclo clássico de gestão de recursos.
- **Inventário com uso real de itens** — usar poções, equipar armas que mudam as chances, encontrar itens mágicos.
- **Progressão de personagem entre capítulos** — experiência, subida de nível; o fio que liga uma campanha.
- **Rolagem de dados transparente** — o jogador vê a matemática completa (modificadores, bônus, por que a dificuldade era aquela).
- **Voz** — implementação concreta de Speech-to-Text na entrada e Text-to-Speech na saída (a interface já existe desde a v1).
- **Segundo idioma** — popular o inglês e habilitar a troca de idioma (a arquitetura de i18n já existe desde a v1).
- **Capítulo 2** e seguintes — acoplados ao sistema-base.

### v3+ — "A mesa compartilhada e a plataforma"
O que **muda a natureza** do sistema, de jogo single-player para multi-usuário/plataforma:
- **Contas de usuário** com login, com todas as implicações de segurança e proteção de dados.
- **Multiplayer online** — salas com ID compartilhável, várias pessoas jogando juntas, cada uma de sua casa, com estado compartilhado em tempo real.
- **Suporte a Vertex AI** — adicionar um provider Vertex AI à camada de abstração de dependências externas (a arquitetura de providers já existe desde a v1; aqui é só implementar mais um).
- **Capítulos contínuos** sendo acoplados continuamente como expansão da campanha.

> **Nota sobre a v1 vs. "pensar baixo":** adiar uma funcionalidade documentada não é pensar pequeno — é sequenciar com responsabilidade. Um escopo enxuto e **terminado** comunica mais senioridade que um escopo grande e pela metade. A v1 que sai deste roadmap é um RPG com IA completo e jogável; tudo na v2/v3+ é expansão de algo que já funciona — e é por isso que será "só acoplar".

## 12. Fora de escopo — explícito

Registrado para não ser reaberto sem decisão consciente:

- **Representação visual de personagens** — não há "boneco" do Game Master (ele não é um personagem, é a narração) nem sprites do jogador/NPCs.
- **Animação de combate 2D/3D** — sem sprites lutando, sem efeitos de poder com assets, sem motor gráfico. A riqueza visual vem da **reatividade da interface** (seção 6.6), não da representação de personagens. Eventual reconsideração só faria sentido numa versão muito amadurecida com orçamento de design real — horizonte distante, não escopo.
- **Mapa tático com grid e posicionamento** — isso é motor de videogame determinístico, fora do gênero do produto.
- **Geração procedural de capítulos por IA** — o conteúdo de aventura é escrito e curado, não gerado sem revisão (ver `DECISOES.md`, ADR-018).
- **Trilha sonora / áudio ambiente** — arrasta produção de assets e licenciamento; fora do contexto de RPG de mesa.
- **MCP (Model Context Protocol)** — avaliado e descartado em favor de `FunctionTool` do ADK (ver `DECISOES.md`, ADR-005).
