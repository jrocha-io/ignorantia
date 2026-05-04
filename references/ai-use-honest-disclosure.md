# Uso honesto de IA em trabalhos acadêmicos

> "A IA pode escrever para você. Mas se a banca pergunta 'por que você decidiu X?', e você não souber responder, é porque **você não fez ciência — você delegou**."

Este documento explicita o que a IA pode fazer pelo usuário, o que **não pode** (mesmo declarando), e o que **deve fazer com supervisão estreita**. Aqui está a honestidade brutal que o nome `ignorantia` promete: trabalho acadêmico mediado por IA tem **limites éticos e práticos** que nenhuma quantidade de declaração formal compensa.

## Fontes primárias

- **Portaria CNPq nº 2.664/2026** — Política de Integridade na Atividade Científica. https://www.gov.br/cnpq/pt-br/assuntos/noticias/cnpq-em-acao/cnpq-publica-portaria-que-institui-politica-de-integridade-na-atividade-cientifica
- **COPE position on Authorship and AI tools**. https://publicationethics.org/guidance/cope-position/authorship-and-ai-tools
- **ICMJE Recommendations** (atualização jan 2024). https://www.icmje.org/recommendations/
- **WAME Recommendations on Chatbots**. https://wame.org/page3.php?id=106
- **Anthropic's Acceptable Use Policy** (para uso responsável do Claude). https://www.anthropic.com/legal/aup
- **MEC Referencial para Desenvolvimento e Uso Responsáveis de IA na Educação** (fev 2026). https://www.gov.br/mec/pt-br

## A linha vermelha: o que a IA NÃO pode fazer (mesmo declarado)

**Bancas, revisores e periódicos sérios rejeitam trabalho onde estes itens foram delegados à IA**, mesmo que a declaração de uso seja completa. Não porque é tecnicamente impossível detectar — é porque **viola a essência da autoria acadêmica**.

### 1. Decidir critérios de inclusão e exclusão

A definição do que é "elegível" para responder uma pergunta de pesquisa é **a primeira decisão científica do trabalho**. Reflete o juízo do pesquisador sobre o que é relevante, o que é confiável, qual é o escopo da contribuição. Delegar isso à IA é delegar a tese.

**Sintoma de delegação:** o usuário não consegue justificar por que excluiu artigos que o leitor consideraria centrais.

**O que a IA pode:** sugerir critérios padrão da área para discussão. O usuário decide.

### 2. Decidir o que é o objeto da pesquisa

A pergunta de pesquisa em PICO/PICOC, o foco, a delimitação — vem do interesse do pesquisador, não da máquina. Se a IA "decidiu" o tema, não é seu trabalho.

**Sintoma de delegação:** o usuário não consegue dizer por que escolheu este tema e não outro.

### 3. Triagem efetiva (incluir/excluir cada paper individualmente)

PRISMA exige leitura humana de título/abstract para decidir inclusão. Pode-se usar IA como **assistente** (tipo "este abstract parece off-topic, confirme?"), mas a decisão final tem que ser humana. **Em SLRs com 2 revisores, isso é duplicado e o kappa mede concordância humana.** IA não conta como revisor.

**O que a IA pode:** sugerir candidatos a exclusão, com razão para o usuário avaliar.

### 4. Quality appraisal

Avaliar qualidade metodológica de um estudo exige juízo crítico sobre **adequação do método à pergunta**, não cheque-lista mecânica. CASP/DARE/Kitchenham têm questões que pedem reflexão (ex.: "the design appropriately addressed the aims of the research?"). Delegar isso à IA é fingir avaliação.

**O que a IA pode:** preencher cheque-lista mecânica em primeiro passo, marcar incertezas para revisão humana.

### 5. Síntese narrativa-temática

A síntese **é a contribuição** do trabalho. É onde o pesquisador identifica padrões que **ninguém ainda articulou**, propõe categorias, contrasta achados conflitantes, decide o que é tendência e o que é ruído. **A IA não tem ponto de vista** — gera texto que reflete consenso pré-existente, não articulação nova.

**Sintoma de delegação:** a síntese não diz nada que outro pesquisador da área não diria; falta posicionamento autoral.

**O que a IA pode:** gerar primeira versão de síntese descritiva (lista de achados por estudo), que o usuário **substancialmente reescreve** com sua interpretação.

### 6. Discussão e implicações

A discussão amarra achados aos debates da área, identifica implicações teóricas e práticas, propõe direções futuras. **Exige conhecimento profundo do campo**, que a IA simula mas não possui.

**Sintoma de delegação:** a discussão é genérica, poderia caber a qualquer trabalho similar.

### 7. Conclusões

Conclusões são juízos do autor sobre o que o trabalho **significa**. Não são "resumo dos resultados". Quem conclui assume autoria intelectual.

**Sintoma de delegação:** conclusões não correspondem aos achados do próprio trabalho, são platitudes.

### 8. Posicionamento do autor

Em humanidades e ciências sociais especialmente, o autor tem que **declarar de onde fala** — referencial teórico, posicionamento epistemológico, viés assumido. **A IA não tem posicionamento.** Quando gera texto que finge ter, é literalmente alucinação.

## O que a IA pode fazer (com declaração explícita)

Tarefas onde a IA é **assistente eficiente sem violar autoria**:

- Sugerir strings booleanas para cada base (autor confere e ajusta)
- Gerar BibTeX a partir de DOIs
- Aplicar formatação ABNT/IEEE/Vancouver/APA
- Gerar template de protocolo, manuscript, README
- Executar buscas em APIs abertas (arXiv, Semantic Scholar, dblp, Crossref, SciELO)
- Deduplicar registros (DOI/título/autor/ano)
- Gerar PRISMA flow diagram a partir de números reais
- Gerar visualizações (charts, mapas) a partir de dados extraídos
- Detectar citações órfãs e DOIs mortos
- Verificação ortográfica e gramatical
- Tradução (com revisão humana minuciosa)
- Gerar resumo descritivo de cada estudo a partir do abstract
- Sugerir estrutura de seções
- Sugerir periódicos relevantes para submissão

Em todas essas, **a IA serve a velocidade, não a substância**.

## O que a IA deve fazer (mas com supervisão estreita)

Zona cinzenta: tarefas onde a IA acelera mas o usuário **deve revisar parágrafo a parágrafo**:

- Gerar primeira versão de introdução, background, método (texto descritivo de algo que já está decidido)
- Gerar primeira versão de descrição de cada estudo na síntese
- Gerar primeira versão de threats to validity
- Gerar versão executiva do abstract
- Reescrever trechos por clareza ou concisão

**Critério de revisão:** se você não consegue defender cada frase quando alguém perguntar "por que você escreveu isso?", precisa reescrever.

## Honrar a participação: o que isto significa na prática

O `ignorantia` faz a primeira versão. Para o trabalho ser **seu**, você precisa:

1. **Reler cada decisão de inclusão/exclusão** e confirmar (ou alterar) com base no seu juízo.
2. **Reler cada quality appraisal** e ajustar pontuações com sua leitura crítica.
3. **Reescrever a síntese** com a sua interpretação dos padrões. A primeira versão da IA é estrutura; a substância é sua.
4. **Escrever a discussão você mesmo**, ou reescrever extensivamente. É aqui que sua autoria mais aparece.
5. **Escrever as conclusões pessoalmente**. A IA pode ser banco de palavras, não banco de juízos.
6. **Verificar cada citação no texto contra a fonte original**. A IA pode ter alucinado o que o paper diz.
7. **Adicionar seu posicionamento** quando relevante (humanidades, ciências sociais).

## Sinalização visual no `ignorantia`

O HTML interativo do skill identifica, em cada parágrafo:

- **🤖 Gerado pela IA, não revisado** — texto que o autor ainda não revisou (cor de alerta)
- **🤖✓ Gerado pela IA, revisado pelo autor** — autor confirmou (cor neutra)
- **✍️ Reescrito pelo autor** — autor reescreveu substancialmente (cor positiva)
- **👤 Original do autor** — autor escreveu do zero

Isso é declarado em `manuscript-content.json` campo `provenance` por seção/parágrafo. O usuário **explicita** o que fez. Sem essa explicitação, default é 🤖, e o avaliacao penaliza fortemente.

## O que bancas brasileiras estão começando a exigir

Algumas IES já adotam (em 2026):

- Declaração de uso de IA em todos os trabalhos de pós-graduação (USP, Unicamp, UFRGS, UFMG)
- Banca pode pedir que o autor explique trecho específico — se não explica, suspeita de delegação
- Em alguns programas, percentual de texto gerado por IA é avaliado por Turnitin AI Detector ou similar
- Guia de Boas Práticas da USP (3ª edição, 2024) tem capítulo dedicado

**Mensagem central:** declaração não é proteção contra a substância da delegação. Você pode declarar tudo certinho e ser rejeitado se a banca perceber que não é seu trabalho.

## Checklist de auto-honestidade (para o usuário)

Antes de submeter qualquer trabalho mediado por IA, pergunte:

- [ ] Eu sei dizer **por que** escolhi cada critério de inclusão/exclusão? (não "a IA sugeriu")
- [ ] Eu li **cada** estudo incluído? (não só abstracts)
- [ ] Eu **discordo** da IA em algum ponto da síntese? (se 100% concorda, não revisou)
- [ ] Eu consigo defender cada parágrafo da discussão se alguém perguntar?
- [ ] As conclusões refletem **minha** interpretação? (não as platitudes da IA)
- [ ] Verifiquei cada citação no texto contra a fonte original?
- [ ] Declarei honestamente cada etapa onde a IA foi usada?

Se algum **não** ficou para trás, o trabalho não é seu o suficiente para ser submetido como seu.

## A última frase

A IA é **uma ferramenta extraordinária para aprender com profundidade**. É péssima ferramenta para **fingir competência**. `ignorantia` é construído para o primeiro uso. Se você usar para o segundo, o `avaliacao.html` vai dizer.
