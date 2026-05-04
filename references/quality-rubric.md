# Rubrica de avaliação — `ignorantia` v2

> "A nota não é prêmio. É **espelho**: mostra a distância real entre o que você (com a IA) construiu e o que a comunidade científica considera publicável."

## Filosofia da rubrica

1. **Substância pesa mais que forma.** Ter os campos preenchidos não basta; o conteúdo tem que ser real.
2. **Avaliação severa.** O objetivo não é estimular o usuário com nota alta, mas mostrar a distância real até venues sérios.
3. **Eliminatórios são duros.** Trabalho fictício, IA listada como autora, plágio crítico → nota 0.0. Sem segunda chance.
4. **Versões incompletas começam em 0.x.y.** Sem capa, sem revisão dupla, sem kappa = trabalho incompleto. Nota máxima reflete isso.
5. **Arredondamento sempre para baixo.** 8.49 vira 8.4. Nunca 8.5.
6. **A nota é uma síntese, não a avaliação.** A análise por dimensão e a matriz por venue dizem mais.

## Estrutura

A avaliação é feita em quatro **camadas independentes**:

1. **Eliminatórios** — passa/não-passa (8 critérios)
2. **Zona de zero** — qual tipo de "nota baixa" se aplica (incompleto / inválido / fraudulento)
3. **Nota geral** — número 0.0-10.0 sintetizando 5 dimensões
4. **Matriz por venue** — status colorido (🟢🟡🟠🔴) por publisher de elite e por A1 nacional

## Camada 1: Eliminatórios (8 critérios — qualquer falha = 0.0)

Estes critérios são **avaliados primeiro**. Se qualquer um falha, a nota é **0.0** e a Zona de Zero é "inválido". Os demais cálculos são apresentados apenas como diagnóstico.

| # | Critério | Detecção |
|---|---|---|
| E1 | IA listada como autora | regex em texto: "(autor\|author).{0,40}?(claude\|gpt\|gemini\|llm\|chatgpt)" |
| E2 | PRISMA flow ausente ou matematicamente incoerente | arquivo `prisma-flow.svg` existe + `prisma-flow.json` tem identified ≥ deduplicated ≥ screened ≥ assessed ≥ included |
| E3 | Quality appraisal ausente | `quality-appraisal.csv` existe + tem ≥ 1 linha por estudo incluído |
| E4 | < 3 bases consultadas | `searches.json` tem ≥ 3 entradas |
| E5 | Manuscrito identificado como fictício/sintético | strings de detecção: "smoke test", "lorem ipsum", "synthetic", "fictício", "exemplo de teste", "smoke-test" |
| E6 | Síntese < 500 palavras | contagem de palavras em §05 (proxy: "não há análise real") |
| E7 | Bibliografia < 10 referências | `len(content.references) < 10` |
| E8 | Declaração de uso de IA ausente quando exigida | bloco "Declaração de IA" / "Declaration of AI use" tem `tool` e `stages` preenchidos |

**Implementação:** os eliminatórios são checados antes de qualquer cálculo de nota. Se qualquer um falha:

- A nota é forçada a **0.0**.
- O HTML de avaliação mostra **alerta vermelho no topo** indicando qual eliminatório foi acionado.
- A análise por dimensão é exibida como diagnóstico, mas com cabeçalho "[NOTA ELIMINATÓRIA — análise apenas para fins de melhoria]".

## Camada 2: Zona de zero (3 zonas)

Quando a nota é 0.0, qual tipo é importante distinguir:

### 🟧 Incompleto (0.x.y)
Trabalho em construção legítima. Não tem peer review humano duplo (kappa pendente), ainda. Versão SemVer começa em **0.x.y**. Nota geral é prefixada por `(incompleto)`.

**Características:**
- Versão 0.x.y declarada
- Faltando: kappa, revisão por dois professores humanos, deposição final no Zenodo após revisão
- **Não falhou em E1-E8**, apenas não chegou à completude

**Sinalização:** banner laranja no HTML de avaliação. Mensagem: "Esta versão é declaradamente incompleta (sem capa). Trabalho em andamento. Versionamento 0.x.y indica que a revisão por pares humana ainda não ocorreu."

### 🟥 Inválido
Trabalho que falhou em pelo menos um eliminatório E1-E8. Não é SLR, ou é SLR mal-feita, ou tem violação ética grave.

**Sinalização:** banner vermelho no HTML. Mensagem específica explicando qual eliminatório foi acionado e como corrigir.

### ⛔ Fraudulento
Trabalho com indícios de fabricação, plágio crítico (camada 1 detecta), ou IA-como-autor explícito. Mais grave que "inválido" — sinaliza má-fé.

**Sinalização:** banner vermelho com aviso forte. Texto: "Este trabalho apresenta indícios de fraude acadêmica. Submeter neste estado pode resultar em sanções (Portaria CNPq nº 2.664/2026, COPE)."

## Camada 3: Nota geral (0.0-10.0)

Apenas calculada se **nenhum eliminatório foi acionado**. Soma de 5 dimensões:

| Dim | Nome | Peso | Foco |
|---|---|---|---|
| D1 | Rigor metodológico | **2.0** | PRISMA, Kitchenham, reprodutibilidade |
| D2 | Compliance ético-legal | **1.5** | CNPq, COPE/ICMJE, LGPD, CEP/CONEP |
| D3 | Qualidade do corpus | **3.5** | Cobertura, venues de elite, QA scores |
| D4 | Substância da síntese | **2.5** | Profundidade, interpretação, autoria |
| D5 | Apresentação | **0.5** | HTML interativo, links DOI, hashes |

**Peso ajustado:** D3+D4 valem **60%** (era 35% na v1). Substância importa mais que forma.

### D1 — Rigor metodológico (2.0)

| Pontos | Critério |
|---|---|
| 0.4 | Protocolo pré-registrado com PICO/PICOC, CI/CE numerados, strings booleanas |
| 0.3 | PRISMA flow com números coerentes |
| 0.5 | ≥ 5 bases Tier 1 consultadas, com sintaxe específica por base, incluindo bases ibero-americanas obrigatórias para pt-BR/es-LA (Decisão 25) |
| 0.3 | QA aplicada a 100% dos incluídos com instrumento adequado |
| 0.2 | Threshold de QA explícito + tratamento transparente |
| 0.2 | Cohen's kappa **realizado** ou **declaradamente pendente** com plano de execução |
| 0.1 | Para SE/CS: Kitchenham QA1-QA8; para saúde: GRADE; para psi/edu: APA JARS |

> **Nota v2.10.1:** "Snowballing executado e documentado" foi **removido** como critério pontuável (Decisão 23, v2.9.0): snowballing backward + forward é **obrigatório** desde a v2.9.0, então não pode ser bonificação. Os 0.2 pts foram redistribuídos para o critério de bases consultadas (que ganhou de 0.3 para 0.5), refletindo a expansão do Tier 1 obrigatório com bases ibero-americanas (Decisão 25).

### D2 — Compliance ético-legal (1.5)

#### Para pt-BR:

| Pontos | Critério |
|---|---|
| 0.4 | Bloco "Declaração de uso de IAG" com TODOS os 8 campos da Portaria CNPq art. 9 substantivamente preenchidos (não com "—") |
| 0.3 | IA NÃO listada como autora (verificável programaticamente) |
| 0.2 | Documento de Área CAPES referenciado |
| 0.2 | Status CEP/CONEP declarado no protocolo |
| 0.2 | LGPD considerada (especialmente para temas sensíveis) |
| 0.1 | LDA: licença declarada, citações com atribuição |
| 0.1 | Vinculação a fomento declarada |

#### Para EN:

| Pontos | Critério |
|---|---|
| 0.4 | Bloco "Declaration of AI use" conforme COPE + ICMJE |
| 0.3 | IA NÃO listada como autora |
| 0.3 | Política específica do publisher-alvo seguida |
| 0.2 | CoI + Funding statements presentes |
| 0.2 | Confidentiality acknowledged (ICMJE Section II.C.2.a) |
| 0.1 | Citações têm DOI/URL |

### D3 — Qualidade do corpus (3.5) — peso aumentado significativamente

| Pontos | Critério |
|---|---|
| 0.6 | Número de incluídos suficiente (área-dependente: SE/CS ≥ 30, saúde ≥ 20, hum ≥ 15) |
| 0.7 | **Presença de venues de elite na bibliografia**. Pt-BR: ≥ 20% Qualis A1-A2. EN: ≥ 30% de elite (IEEE Trans, Nature/Springer, Elsevier flagship, etc.) |
| 0.4 | Cobertura temporal coerente (janela respeitada + estudos seminais) |
| 0.4 | Diversidade de tipos de estudo (≥ 3 distintos) |
| 0.5 | QA scores: média ≥ 70%, mediana ≥ 75% |
| 0.5 | Saturação de RQs: cada RQ tem ≥ 5 estudos para sustentação (era 3 na v1) |
| 0.4 | **Triangulação de fontes**: corpus inclui empíricos, teóricos, e revisões anteriores |

### D4 — Substância da síntese (2.5) — novo, peso aumentado

| Pontos | Critério |
|---|---|
| 0.5 | Síntese ≥ 2000 palavras (era 800 na v1; agora exige profundidade real) |
| 0.5 | **Interpretação, não descrição**: detecção de cross-tabulação, padrões identificados, framework conceitual proposto. Heurística: presença de termos como "padrão emergente", "três grupos de estudos", "convergência aparente", "tensão entre", "framework", "taxonomia" |
| 0.4 | Cada RQ é respondida com referência a múltiplos estudos cruzados |
| 0.4 | Discussão tem ≥ 5 guidelines/insights numerados |
| 0.3 | Discussão dialoga com debates da área (cita autores canônicos) |
| 0.2 | Threats to validity discute 4 tipos (construct, internal, external, conclusion) |
| 0.2 | Conclusões vão além de "este tema é importante" — declaram contribuição específica |

### D5 — Apresentação (0.5) — peso reduzido

| Pontos | Critério |
|---|---|
| 0.1 | HTML carrega + 4 tabs funcionais + busca + dark mode |
| 0.1 | Toda referência clicável com DOI/URL vivo (HTTP HEAD bem-sucedido) |
| 0.1 | PRISMA flow inline (SVG) + matriz de venues |
| 0.1 | Pacote completo (≥ 12 artefatos esperados) |
| 0.1 | README com hashes SHA-256 + changelog + versão SemVer |

> **Nota v2.8.0:** "Gráficos D3.js dinâmicos" foi removido como critério de qualidade (Decisão sobre rubrica, v2.8.0). Visualização interativa é agradável mas **não é evidência de mérito científico**. A v2.10.0 também tornará obrigatórios os outputs adicionais `.tex`, `.pdf` e `.docx` ABNT — esses passam a fazer parte do pacote completo (item de 0.1 acima), não como dimensão D5 expandida.

## Camada 4: Matriz por venue

Para cada venue de elite **filtrado por área** (não os 30, mas os 5-15 relevantes), o skill atribui status:

- 🟢 **Pronto** — atende todos os critérios formais e metodológicos do venue
- 🟡 **Próximo** — 1-3 critérios faltando
- 🟠 **Distante** — 4+ critérios faltando, ou requer mudança estrutural
- 🔴 **Inadequado** — escopo/área não combina; não submeter

Cada status vem com **lista exata do que falta** referenciando `references/venue-criteria-elite.md` ou `references/venue-criteria-qualis-a1.md`.

### Triagem em 3 grupos por venue

1. **Top 3 venues** mais alinhados ao tema → análise detalhada (uma seção cada com critérios específicos)
2. **Próximos 7-10 venues** → análise resumida (linha em tabela com status + 2-3 itens críticos)
3. **Demais venues** abaixo do limiar → linha única "abaixo do limiar de submissão"

## Bonificadores (até +0.3)

| Critério | Pontos |
|---|---|
| Pré-registro Zenodo/PROSPERO antes da execução das buscas | +0.1 |
| Verificação de plágio Camada 3 (Copyleaks/iThenticate) executada e limpa | +0.1 |

## Eixo de destino acadêmico (separado)

Reportado em paralelo à nota geral, sem se misturar:

- **TCC (graduação)** — corpus mínimo 15, síntese 800-1500 palavras, defesa 30-40min
- **TCC nota 10 banca exigente USP/Unicamp/UNESP** — corpus 25+, síntese 1500+ palavras, profundidade aproxima dissertação
- **Dissertação de mestrado** — corpus 25-40, síntese 2000-4000 palavras, kappa real
- **Dissertação programa nota 6-7** — corpus 40+, síntese 4000+, artigo derivado A2-A4 esperado
- **Tese de doutorado** — corpus 50+, síntese 5000+, artigos derivados A2-A1
- **Tese cum laude** — corpus 80-150, artigo A1/Q1 já publicado, contribuição reconhecida

O HTML de avaliação reporta **em qual destino acadêmico o trabalho atualmente está enquadrado**, separado da nota.

## Mapeamento da nota geral aos eixos

| Nota | Publicação (pt-BR) | Publicação (EN) | Destino acadêmico aproximado |
|---|---|---|---|
| 9.5-10.0 | Qualis A1 / Q1 internacional | Top elite (Nature, Lancet, IEEE Trans Q1, AAAS) | Tese cum laude / publicação direta |
| 8.5-9.4 | Qualis A2-A3 | Q1-Q2 secundário | Tese de doutorado |
| 7.5-8.4 | Qualis A4-B1 | Q2-Q3 | Dissertação programa nota 6-7 |
| 6.5-7.4 | Qualis B2-B3 | Q3-Q4 | Dissertação ou TCC nota 10 banca exigente |
| 5.0-6.4 | Qualis B4-B5 | OA generalistas | TCC bom |
| 0.1-4.9 | Não recomendar publicação | Não recomendar | TCC com revisões; Dissertação inicial |
| 0.0 | NÃO submeter — eliminatório acionado, ou versão incompleta | Idem | NÃO submeter |

## Estrutura do output

A avaliação **não é mais um arquivo separado**. Está embutida no HTML principal como **§ 11 Auditoria** (próximo documento explica), com:

- **Banner de status** (verde/amarelo/laranja/vermelho conforme situação)
- **Nota geral** com decomposição por dimensão
- **Matriz de venues** com status colorido + clique para detalhar
- **Lista priorizada do que falta** para subir de patamar
- **Próxima versão sugerida** (PATCH/MINOR/MAJOR ou bump 0.x → 1.0)

## Critérios removidos da rubrica (v2.8.0)

Auditoria do RS-42 v1.0.0 identificou critérios que penalizavam o autor por situações que não são lacunas reais de qualidade. Os seguintes critérios foram **removidos** da rubrica:

| Critério antigo | Razão da remoção |
|---|---|
| **"Spot-check humano nas exclusões da Fase 4 não foi conduzido"** (D1) | Decisão 21: ao prosseguir do screening para a extração, o autor já está aceitando as exclusões; auditoria separada é redundante. O `reproducibility_manifest.yaml` registra `phase4_exclusions_review: implicit_consent` automaticamente. |
| **"Vinculação bidirecional Zenodo ↔ projeto subjacente é Categoria B"** (D2) | Decisão editorial pós-depósito, fora do escopo do skill. O skill não tem como avaliar isso porque acontece após a entrega do pacote. |
| **"Bases Tier 3 (Scopus, WoS, IEEE Xplore subset, Embase) não consultadas"** como lacuna a aceitar | Reescrito na v2.9.0 (Decisão 24): essas bases passam a ser **prioridade 0** via Tier 0 routing (Unpaywall + OAB + CORE + CAFe + gap report). Não-consulta deixa de ser "limitação aceitável" e vira erro de configuração quando o usuário tinha como acessar. |
| **"SciELO direto deveria ter sido consultado"** como limitação aceita | Reescrito na v2.9.0 (Decisão 25): SciELO + LA Referencia + Redalyc + CLACSO + BDTD + Scioteca + DOAJ + Periódicos CAPES + LILACS/BVS são **obrigatórias** na pesquisa pt-BR/es-LA. Não-consulta é defeito, não limitação. |
| **"Apenas X% dos elegíveis foram extraídos com profundidade"** | Decisão 26 (v2.9.0): todo elegível recebe extração com mesmo rigor de SR, independente do modo. Esse critério deixa de existir. |
| **"Idiomas restritos a EN/PT/ES"** | EN+PT+ES é **obrigação** da skill (Decisão 27, v2.9.0), não limitação a declarar. Critério removido. |
| **"Gráficos D3.js dinâmicos não implementados"** (D5) | Removido: visualização interativa não é evidência de mérito científico. |
| **"Camada de rabiscos for fun não implementada"** (D5) | Decisão 30 (v2.8.0): feature foi removida da skill. Critério já não se aplica. |
| **"Manuscrito formal opcional (.docx ABNT) não gerado"** | Reescrito na v2.10.0: `.docx` ABNT, `.tex` e `.pdf` passam a ser **obrigatórios** no pacote final, dentro do critério "pacote completo" da D5. |
| **"Snowballing executado e documentado" (D1, 0.2 pts)** + **"Snowballing forward + backward" como bonus (+0.1)** | Removido na v2.10.1: Decisão 23 (v2.9.0) já tornou snowballing backward + forward **obrigatório**. Os 0.2 pts de D1 foram redistribuídos para o critério de bases consultadas (que cobre a expansão Tier 1 da Decisão 25). Bonificação de +0.1 era duplicação. |

## Disclaimer obrigatório

Ao final da avaliação, sempre:

> Esta avaliação é gerada automaticamente com base na rubrica em `references/quality-rubric.md`. **Serve para o usuário aprender** quão longe está dos padrões de elite, **não para validar publicação real**. A decisão editorial final é dos revisores humanos do venue-alvo. A nota 10.0 não garante aceitação — significa apenas que o manuscrito atende aos requisitos formais e metodológicos para ser **elegível**. Trabalho mediado por IA tem limites éticos descritos em `references/ai-use-honest-disclosure.md` que nenhuma quantidade de declaração formal compensa.
