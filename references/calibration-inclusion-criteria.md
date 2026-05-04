# Critérios Canônicos de Inclusão — Corpus de Calibração

**Rodada J1** | **Versão 1.0** | **Data**: 2026-04-29

## Definição operacional de "SLR válida"

Para entrar no corpus de calibração, um artigo deve **simultaneamente**:

### Critérios de inclusão (todos obrigatórios)

**I1. Tipo de estudo**: Identifica-se explicitamente como uma das seguintes:
  - Systematic review / Revisão sistemática
  - Systematic literature review / Revisão sistemática da literatura
  - Meta-analysis / Meta-análise (quantitativa ou qualitativa)
  - Mapping study / Estudo de mapeamento (Kitchenham 2007)
  - Tertiary review / Revisão de revisões

**I2. Reporting guideline declarado**: Menciona explicitamente PRISMA, PRISMA-2020, PRISMA-ScR, MOOSE, ENTREQ, ROSES, EBSE/Kitchenham ou guideline equivalente em métodos ou abstract.

**I3. Protocolo de busca**: Reporta strings booleanas, bases consultadas (≥2), datas de busca.

**I4. Critérios de elegibilidade**: Apresenta inclusão/exclusão explícitos com justificativa.

**I5. PRISMA flow numerado**: Reporta ao menos os números agregados (identification → screening → eligibility → inclusion).

**I6. Venue identificável**: DOI ou ISSN presente; venue mapeável para Qualis CAPES 2021-2024 ou Quartil Scopus/JCR.

**I7. Acesso ao texto**: Texto integral acessível via OA, repositório institucional ou licença Crossref/PMC/SciELO.

### Critérios de exclusão (qualquer um exclui)

**E1**. Scoping reviews **sem** PRISMA-ScR (escopo mais leve, calibração diferente).
**E2**. Revisões narrativas sem protocolo (literature review, narrative review).
**E3**. Meta-análises de RCTs **puramente clínicas** sem síntese qualitativa (perfil distinto da SLR alvo do `ignorantia`).
**E4**. Pré-prints sem revisão por pares (incompatível com ground-truth Qualis).
**E5**. Capítulos de livro, dissertações, teses, anais não indexados.
**E6**. Errata, comentários, cartas, editoriais, correções.
**E7**. Estudos publicados **antes de 2018** (Qualis CAPES atual é 2021-2024; calibração privilegia janela próxima).
**E8**. Venues sem estrato Qualis declarado **e** sem Quartil Scopus/JCR (impossibilita ground-truth).

### Janela temporal

- **Publicação**: 2018-01-01 a 2026-04-29 (cobre ciclo Qualis vigente + ano corrente).
- **Bases consultadas pela SLR**: a SLR pode ter buscado em qualquer janela.

### Idiomas aceitos

- Português (BR e PT)
- Inglês
- Espanhol (limitado: apenas se ground-truth Qualis confirmado)

Outros idiomas adiados para versão futura.

### Estratos canônicos para amostragem

A meta original (300 SLRs) busca **50 por estrato** distribuídos em:

| Estrato Qualis | Quartil global equivalente | Meta |
|---|---|---|
| A1 | Q1 (upper) | 50 |
| A2 | Q1 (lower) | 50 |
| A3 | Q2 (upper) | 50 |
| A4 | Q2 (lower) | 50 |
| B1 | Q3 (upper) | 50 |
| B2 | Q3 (lower) | 50 |
| **TOTAL** | | **300** |

### Tratamento de ambiguidades

**Estrato variável por área-mãe**: o mesmo periódico pode ter Qualis A1 em educação e B1 em saúde. Convenção: registrar **estrato canônico** = mais alto entre áreas-mãe relevantes ao tema da SLR + nota de área-mãe usada.

**Múltiplos identificadores**: se SLR tem DOI principal + DOI Crossref + DOI institucional, usar DOI principal (registrado pelo publisher).

**SLR multi-RQ**: contabilizar como uma única entrada, não múltiplas.

## Workflow de triagem

1. **Coleta automática** (J3): query estruturada por venue/estrato/janela em Crossref/SciELO/PMC/DOAJ.
2. **Triagem L1** (J4 automatizada): regex sobre título/abstract para detectar I1+I2 (systematic review + PRISMA).
3. **Triagem L2** (J5 manual amostral 20%): inspeção do texto para confirmar I3-I5.
4. **Triagem L3** (J5 manual seletiva): casos limítrofes resolvidos por discussão entre revisores.

## Output da Rodada J

Arquivo `references/calibration-corpus.json` no formato:

```json
{
  "version": "1.0",
  "fetched_at": "2026-04-29",
  "criteria_version": "1.0",
  "n_total": <int>,
  "by_stratum": {
    "A1": <int>, "A2": <int>, ..., "B2": <int>
  },
  "by_language": {"pt": <int>, "en": <int>, "es": <int>},
  "by_area_mae": {
    "educacao": <int>, "saude": <int>, ...
  },
  "studies": [
    {
      "doi": "10.xxxx/yyy",
      "title": "...",
      "year": 2024,
      "venue": "...",
      "venue_issn": "0000-0000",
      "qualis_stratum_canonical": "A2",
      "quartil_global": "Q1 (lower)",
      "area_mae": "educacao",
      "language": "pt",
      "tier_source": "catalog88|sucupira_2024|scopus_jcr",
      "abstract": "...",
      "passes_triage_l1": true,
      "triage_notes": "..."
    },
    ...
  ]
}
```
