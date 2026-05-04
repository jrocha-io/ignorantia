# Modo 04 — Systematic Review (estrito, com 2 revisores humanos)

> Camada hierárquica: **TERCIÁRIA** (você + ≥1 humano qualificado adicional obrigatório).
>
> ⚠️ Este modo NÃO é oferecido como recomendação default. Só use se você tem segundo revisor humano qualificado disponível.

## Caso de uso

Revisão sistemática estrita seguindo PRISMA-2020 + MECIR (Cochrane) ou Campbell Standards, com dois revisores humanos independentes em todas as etapas (screening, full-text, extraction) e kappa documentado. Único modo no qual o termo "Systematic Review" pode ser usado sem violar E16.

## Layer 1 — Modo

| Dimensão | Especificação |
|---|---|
| **review_type** | `systematic_review_with_2_reviewers` |
| **Reporting guideline primário** | PRISMA-2020 |
| **Reporting guideline secundário** | MECIR (Cochrane), Campbell Standards (políticas sociais), SIGSOFT (CS/SE) conforme área |
| **Camada hierárquica** | **Terciária** |
| **Tempo típico de produção** | `user_estimate_15min_unvalidated` (apenas para o ghostwriter; trabalho humano de 2 revisores adiciona dias-semanas) |
| **Selo HTML** | `mode-sr-strict` (verde escuro) |

## Layer 2 — Reporting guideline (PRISMA-2020)

| Dimensão | Especificação |
|---|---|
| **Itens checklist** | 27 itens (PRISMA-2020) + 16 (PRISMA-S) |
| **Revisores humanos OBRIGATÓRIOS** | **2** (com ORCID, identidades verificáveis) |
| **AI dual-check** | Não substitui segundo revisor humano |
| **Pré-registro** | **PROSPERO OBRIGATÓRIO** (saúde) ou OSF Registries (outras áreas) |
| **Kappa documentado** | OBRIGATÓRIO em screening, full-text, extraction |

### Declarações obrigatórias adicionais (vs Scoping/Rapid)

- **PROSPERO/OSF registration ID** (E10/E16)
- **Reviewer 1 + Reviewer 2 nomes + ORCID + afiliações**
- **Cohen's kappa screening/full-text/extraction com valores numéricos**
- **Disagreement resolution method** (consensus | third reviewer | voting)
- **PRISMA flow diagram** com números coerentes
- **GRADE certainty of evidence** (recomendado)
- **Plain Language Summary** (Cochrane)

### Estrutura mínima

PRISMA-2020 27 itens completos + Plain Language Summary se Cochrane.

## Layer 3 — Venue padrão e alternativas (OA-first)

### Padrão (OA-gratuito $0)

**Zenodo** se o objetivo é apenas registro com DOI; mas para SR estrito, peer review tradicional é tipicamente o destino.

### Alternativas Qualis A1 BR ($0 APC, peer review)

- **Cadernos de Saúde Pública** (Fiocruz) — A1 saúde, OJS, $0, aceita SR estrito
- **Revista de Saúde Pública** (USP) — A1 saúde, OJS, $0, aceita SR estrito
- **Ciência & Saúde Coletiva** (Abrasco) — A1 saúde, OJS, $0
- **Educação e Pesquisa** (USP) — A1 educação, OJS, $0

### Alternativas internacionais Q1 (peer review)

- **The BMJ** — hybrid (~$5000 APC para OA), padrão SR clínica
- **The Lancet** — hybrid, alto impacto
- **Cochrane Database of Systematic Reviews** — hybrid, padrão-ouro mas exige MECIR completo + 3-stage process
- **Campbell Systematic Reviews** — fully OA, $0 APC, alta exigência metodológica
- **Research Synthesis Methods** — Q1, hybrid, ~$3500 APC

## Bases de busca recomendadas

Mínimo: **5 bases** (mais rigoroso que Scoping/Rapid).

- **Saúde**: PubMed + EMBASE + Cochrane CENTRAL + LILACS + ClinicalTrials.gov
- **Educação**: ERIC + PsycINFO + Web of Science + Scopus + Google Scholar
- **CS/SE**: ACM DL + IEEE Xplore + SpringerLink + ScienceDirect + DBLP

Para SR estrito, **Tier 3 (paywall) é frequentemente necessário** — o usuário precisa ter acesso institucional ou fornecer material manualmente.

## Estudos primários esperados

Tipicamente **20-80 estudos incluídos** após filtragem rigorosa. SRs com <10 estudos sugerem busca insuficiente; >150 sugerem que pergunta deveria ser subdividida.

## Custos para o usuário

- **APC**: variável — $0 (Qualis A1 BR ou Campbell) até $5000+ (BMJ/Lancet OA)
- **Pré-registro**: $0 (PROSPERO/OSF)
- **Software**: Rayyan free tier ou Covidence (paid) recomendado para 2-reviewer workflow
- **Bases pagas**: frequentemente exigidas — usuário precisa de acesso institucional
- **Trabalho humano adicional**: segundo revisor é o custo dominante (não-monetário mas não-trivial)

## E16 — eliminatório crítico

Este é o ÚNICO modo no qual `review_type: systematic_review_with_2_reviewers` é aceito. Sem evidência de 2 revisores humanos com kappa documentado, E16 bloqueia.

## Limitações declaradas (mesmo em SR estrito)

- Limitações da evidência incluída
- Limitações dos processos de revisão (mesmo com 2 revisores, há subjetividade residual)
- Implicações para prática vs implicações para pesquisa futura

## Quando NÃO usar este modo

- **Você está sozinho** → Modo 1 (Scoping), 2 (Rapid), 9 (Integrative), ou 10 (Realist) conforme natureza
- **Pergunta sobre mecanismos causais** → Modo 10 (Realist Review)
- **Decisão urgente** → Modo 2 (Rapid Review) com upgrade futuro se necessário
- **Mistura quanti/quali/teórica** → Modo 9 (Integrative Review)
