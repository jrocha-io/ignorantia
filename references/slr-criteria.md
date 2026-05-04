# Critérios para um trabalho ser identificado como Revisão Sistemática

Este documento estabelece o que diferencia uma **revisão sistemática (SLR)** de uma revisão narrativa, mapeamento sistemático, scoping review, ou simples levantamento bibliográfico. O skill `ignorantia` segue PRISMA-2020 como norma principal e Kitchenham como complementar para SE/CS.

## Fontes primárias

Todas as decisões deste skill sobre o que constitui SLR vêm de:

- **PRISMA 2020 statement**: Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ. 2021;372:n71. https://doi.org/10.1136/bmj.n71
- **PRISMA 2020 explanation and elaboration**: Page MJ et al. BMJ. 2021;372:n160. https://doi.org/10.1136/bmj.n160
- **Cochrane Handbook for Systematic Reviews of Interventions** (versão atual): https://training.cochrane.org/handbook
- **Kitchenham B, Charters S.** Guidelines for performing Systematic Literature Reviews in Software Engineering. Technical Report EBSE-2007-01. Keele University. 2007.
- **Wohlin C.** Guidelines for snowballing in systematic literature studies and a replication in software engineering. EASE 2014. https://doi.org/10.1145/2601248.2601268
- **Booth A, Sutton A, Clowes M, Martyn-St James M.** Systematic Approaches to a Successful Literature Review. 3rd ed. SAGE; 2021.
- **Petersen K, Vakkalanka S, Kuzniarz L.** Guidelines for conducting systematic mapping studies in software engineering: An update. Information and Software Technology. 2015;64:1-18.

## O que diferencia SLR de outros tipos de revisão

| Aspecto | Revisão narrativa | Scoping review | Systematic mapping | **SLR** |
|---|---|---|---|---|
| Pergunta | Ampla | Ampla | Ampla | **Específica e respondível** |
| Protocolo prévio | Não exigido | Recomendado | Sim | **Obrigatório** |
| Buscas exaustivas | Não | Parcial | Sim | **Sim, replicáveis** |
| Critérios I/E declarados | Não | Sim | Sim | **Sim, antes da busca** |
| Quality appraisal | Raro | Não | Não | **Obrigatório** |
| Síntese | Narrativa livre | Mapeamento | Categorização | **Síntese narrativa-temática ou meta-análise** |
| PRISMA flow | Não | Sim (PRISMA-ScR) | Não | **Sim, números coerentes** |
| Reprodutibilidade | Baixa | Média | Alta | **Alta — outro pesquisador chega ao mesmo conjunto** |

## Os 8 elementos obrigatórios de uma SLR (segundo PRISMA-2020)

Sem qualquer um destes, **não é SLR** — pode ser outro tipo de revisão, mas não SLR. O `ignorantia` checa cada um na rubrica de avaliação.

### 1. Protocolo pré-registrado (item 5 PRISMA-2020)

- Pergunta de pesquisa em formato PICO (saúde), PICOC (SE/CS) ou equivalente
- Critérios de inclusão e exclusão numerados antes da busca
- Bases de dados que serão consultadas
- Strings booleanas por base
- Ferramenta de quality appraisal escolhida
- Pré-registro em PROSPERO (saúde), OSF, ou Zenodo antes da execução

**Verificação:** existe `protocol.md` no pacote, com PICO/PICOC, CI numerados, CE numerados, strings booleanas literais, ferramenta de QA declarada.

### 2. Lista finita e fechada de bases (itens 6-7 PRISMA-2020)

- Mínimo 3 bases, recomendado ≥ 5
- Para SE/CS: IEEE Xplore + ACM DL + dblp + Scopus + Web of Science (ou subset com justificativa)
- Para saúde: PubMed/MEDLINE + Cochrane Library + Scopus + Embase
- Para psicologia/educação: ERIC + PsycINFO + Scopus + Web of Science
- Para Brasil pt-BR: SciELO + BDTD + Portal CAPES (e bases internacionais relevantes)

**Verificação:** `searches.json` lista cada base com data de execução, string usada, e número de hits retornados.

### 3. Strings booleanas por base, com sintaxe correta (item 7 PRISMA-2020)

Cada base tem sua sintaxe. Não é "string única replicada" — é string adaptada à sintaxe específica.

**Exemplo (PubMed):** `("digital literacy"[MeSH] OR "digital literacy"[Title/Abstract]) AND ("aged"[MeSH] OR elder*[Title/Abstract])`

**Exemplo (IEEE Xplore):** `("All Metadata":"digital literacy") AND ("All Metadata":elderly OR "All Metadata":aged)`

**Verificação:** `searches.json` tem `query` específica por base, não a mesma string em todas.

### 4. Critérios de inclusão/exclusão aplicados, decisão registrada (itens 8-9 PRISMA-2020)

- Cada paper triado tem decisão registrada (incluído / excluído / dúvida → resolvida)
- Para excluídos, qual CI ou CE foi invocado
- Razões agrupadas: off-topic, não peer-reviewed, língua errada, sem texto integral acessível, etc.

**Verificação:** `screening.csv` tem coluna `decision` (include/exclude) e coluna `reason` (CI/CE invocado).

### 5. PRISMA flow diagram com números coerentes (item 16 PRISMA-2020)

- `Records identified from databases (n=...)` ≥
- `Records after duplicates removed (n=...)` ≥
- `Records screened by title/abstract (n=...)` ≥
- `Reports assessed for eligibility (n=...)` ≥
- `Studies included in review (n=...)`

Cada passo tem número de excluídos com **razão**.

**Verificação:** `prisma-flow.svg` existe; `prisma-flow.json` (interno) tem coerência matemática verificável programaticamente.

### 6. Quality appraisal aplicado a TODOS os incluídos (item 11 PRISMA-2020)

- Instrumento declarado no protocolo: CASP (qualitativo), DARE (revisões), Kitchenham QA1-QA8 (SE), Dyba-Dingsoyr 11Q (SE empírico), JBI (saúde), MMAT (mistos), GRADE (certeza de evidência)
- Pontuação por questão e por estudo
- Threshold declarado (e.g., ≥ 50% do máximo)
- Estudos abaixo do threshold: excluídos com justificativa OU mantidos com flag "baixa qualidade"

**Verificação:** `quality-appraisal.csv` tem uma linha por estudo incluído, colunas para cada questão do instrumento, total computado.

### 7. Extração de dados em formulário pré-definido (item 10 PRISMA-2020)

- Schema da extração declarado no protocolo
- Campos típicos: ID, autor, ano, venue, país, contexto, objetivo, método, amostra, framework, achados, RQ atendida, QA score
- Preenchido para todos os incluídos
- Inconsistências resolvidas por consenso (em SLR humana, com kappa)

**Verificação:** `extraction.csv` tem schema consistente; campos críticos não vazios.

### 8. Síntese (itens 13-15 PRISMA-2020)

- Síntese narrativa-temática por RQ — interpreta, cross-tabula, identifica padrões
- Não basta listar achados de cada estudo
- Tabelas comparativas e visualizações complementam, não substituem
- Para meta-análise (saúde): forest plot + heterogeneidade + viés de publicação

**Verificação:** `manuscript.html` §05 tem síntese ≥ 800 palavras com cruzamentos; cada RQ é respondida com referência aos estudos.

## O segundo revisor e o Cohen's kappa

PRISMA exige (no item de "rigor") que triagem e extração sejam feitas **independentemente por dois revisores** e que discordâncias sejam computadas com Cohen's kappa, depois resolvidas por consenso ou terceiro revisor.

**O `ignorantia` não simula segundo revisor.** O skill produz a primeira passagem (versão 0.x.y, declaradamente incompleta). O usuário precisa de **dois professores humanos** para fazer a segunda passagem independente e calcular o kappa real. Só então a versão sobe para 1.x.y (completa).

Se o usuário usar o skill sozinho, **o trabalho permanece em 0.x.y para sempre**, e a avaliação informa: "esta SLR não tem segundo revisor; segundo PRISMA, isto a torna **incompleta**, independentemente da qualidade dos demais elementos."

## Snowballing (item adicional, não obrigatório, mas recomendado)

Wohlin (2014) propõe snowballing como complemento ou alternativa às buscas em bases. Forward snowballing: papers que citam um seed paper. Backward snowballing: papers citados por um seed paper.

**`ignorantia` recomenda snowballing como bonificador**, não como obrigatório. Documenta-se o que foi adicionado por snowballing e a partir de qual seed.

## Diferenças por área

### Saúde — segue PRISMA + Cochrane Handbook

- PICO obrigatório (não PICOC)
- Reporting guideline específico para meta-análise: PRISMA + AMSTAR-2 + GRADE
- Risk of bias: RoB-2 (RCTs), ROBINS-I (observacionais)
- Pré-registro PROSPERO obrigatório

### SE/CS — segue PRISMA + Kitchenham

- PICOC ou variantes (Population, Intervention, Comparison, Outcome, Context)
- QA1-QA8 (Kitchenham) ou 11Q (Dyba-Dingsoyr)
- Snowballing forte recomendado (Wohlin)

### Psicologia/Educação — segue PRISMA + APA JARS

- Pode ser PICO, SPIDER (qualitativo), ou outro
- APA Journal Article Reporting Standards
- Quality appraisal: MMAT (Mixed Methods Appraisal Tool)

### Humanidades — segue PRISMA adaptado

- Booth, Sutton & Papaioannou: SALSA framework (Search, Appraisal, Synthesis, Analysis)
- Quality appraisal frequentemente adaptado da área
- Síntese é predominantemente narrativa, não quantitativa

## Critérios eliminatórios (para o `ignorantia`)

Se qualquer destes falha, o trabalho **não é uma SLR** segundo PRISMA, e a nota da avaliação é **0.0** (zona "inválido"):

1. PRISMA flow ausente ou matematicamente incoerente
2. Quality appraisal ausente ou aplicado a < 100% dos incluídos
3. Buscas em < 3 bases distintas
4. Extração sem schema definido
5. Sem critérios de inclusão/exclusão registrados
6. Síntese < 500 palavras (proxy de "não há análise real")
7. Bibliografia < 10 referências (proxy de "corpus insuficiente")
8. Manuscrito identificado como fictício/sintético/teste (detectado por strings)

## O que o usuário aprende com este documento

- Que SLR ≠ "revisão de literatura"
- Que cada elemento exige trabalho específico, não palpite
- Que a banca/revisor humano vai cobrar exatamente esses 8 elementos
- Que existe diferença entre "fiz uma revisão sobre X" e "conduzi uma SLR PRISMA-2020 sobre X"

Quando o `avaliacao.html` aponta deficiência num desses elementos, o link aqui explica **o porquê** — o usuário entende não só o que está faltando, mas a razão científica.
