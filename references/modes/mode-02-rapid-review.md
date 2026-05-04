# Modo 02 — AI-Assisted Rapid Review

> Camada hierárquica: **PRIMÁRIA** (você sozinho + pesquisa bibliográfica autônoma).

## Caso de uso

Suporte a decisão time-bounded — política pública urgente, decisão de design com prazo, emergência sanitária. Aceita single-reviewer + AI dual-check + busca limitada com transparência total.

## Layer 1 — Modo

| Dimensão | Especificação |
|---|---|
| **review_type** | `rapid_review` |
| **Reporting guideline primário** | PRISMA-RR (Stevens et al. 2024) |
| **Reporting guideline secundário** | Cochrane Rapid Reviews Methods Group |
| **Camada hierárquica** | Primária |
| **Tempo típico de produção** | `user_estimate_15min_unvalidated` |
| **Selo HTML** | `mode-rapid` (laranja) |

## Layer 2 — Reporting guideline (PRISMA-RR)

| Dimensão | Especificação |
|---|---|
| **Itens da checklist** | 16 itens |
| **Itens automatizáveis (full)** | 5 |
| **Itens automatizáveis (partial)** | 9 |
| **Itens human-only** | 2 |
| **Revisores humanos exigidos** | 1 (single-reviewer com AI dual-check 100% obrigatório) |
| **AI dual-check exigido** | OBRIGATÓRIO (100% dos screening calls) |
| **Pré-registro** | OSF OBRIGATÓRIO (PRISMA-RR item RR-4) |

### Declarações obrigatórias (PRISMA-RR-específicas)

- **Justificativa do uso de Rapid** (RR-3) — explicitar urgência/contexto decisional
- **Single-reviewer disclosure** (RR-7) — AI-assisted ou dual-check
- **Limitations linking to rapid methodology** (RR-12) — OBRIGATÓRIO; falta dessa seção é o erro mais comum em rapid reviews mal-feitas
- **Should this be upgraded to SR?** (RR-13) — responder explicitamente
- **Funding + COI + AI Disclosure**

### Estrutura mínima (seções)

1. Title contendo "rapid review" ou "revisão rápida"
2. Structured abstract com nota da metodologia rapid
3. Introduction com justificativa da abordagem rapid
4. Methods (eligibility, search ≥1 base + grey lit, single-reviewer disclosure, simplified appraisal)
5. Results com PRISMA flow + characteristics summary
6. Discussion com **limitations específicas da rapid methodology**
7. Implications + upgrade recommendation
8. Funding + COI + AI Disclosure
9. Reproducibility package mention (DOI Zenodo)

## Layer 3 — Venue padrão e alternativas (OA-first)

### Padrão (OA-gratuito, $0 APC)

**Zenodo** + preprint paralelo (medRxiv para saúde, EdArXiv para educação, OSF Preprints multi-área). DOI persistente, sem peer review formal — apropriado para suporte a decisão urgente.

### Alternativas com peer review (Qualis A1 BR, $0 APC)

- **Revista de Saúde Pública** (USP) — A1 saúde, aceita rapid reviews para temas de saúde pública.
- **Cadernos de Saúde Pública** (Fiocruz) — A1 saúde, especialmente apropriado para temas brasileiros de política pública.

### Alternativas internacionais

- **The BMJ** — hybrid, alto impacto, aceita rapid reviews para temas clínicos urgentes (~$5000 APC para OA).
- **BMJ Open** — fully OA, ~$2300 APC, peer review tradicional.

## Bases de busca recomendadas

Mínimo: **1 base + grey literature** (PRISMA-RR item RR-6) com justificativa explícita do escopo limitado.

Tier 1 prioritário:
- **Saúde**: PubMed (cobre maior parte da literatura clínica) + grey lit (OECD reports, OMS, ANVISA, conforme tema)
- **Educação**: ERIC + grey lit (UNESCO, OECD Education, MEC, INEP)
- **CS/SE**: arXiv (cs.*) + grey lit (W3C drafts, ACM Tech Reports, NIST)

## Estudos primários esperados

Tipicamente **10-50 estudos incluídos**. Rapid review é por definição limitada — escopo restrito é aceito desde que justificado.

## Custos para o usuário

- **APC**: $0 (padrão Zenodo)
- **Pré-registro**: $0 (OSF; OBRIGATÓRIO em PRISMA-RR)
- **Software**: opcional
- **Bases pagas**: não exigidas (Tier 1 cobre)

## Eliminadores aplicáveis

- E1-E15 todos
- E16: protege contra uso indevido do termo "Systematic Review"

## Limitações OBRIGATORIAMENTE declaradas (PRISMA-RR RR-12)

> "**Limitations attributable to the rapid methodology**: (i) single-reviewer screening (mitigated by AI dual-check but not equivalent to two independent humans); (ii) limited number of databases searched (specify) compared to a full SR; (iii) simplified critical appraisal; (iv) restricted time window for search updates; (v) synthesis is narrative rather than meta-analytic. Readers should weight conclusions accordingly."

## Quando NÃO usar este modo

- Sem urgência decisional → Modo 1 (Scoping Review)
- Pergunta exige meta-análise → Modo 4 (SR estrito) com 2 revisores
- Pergunta sobre mecanismos causais → Modo 10 (Realist Review)
