# Mode template — Systematic Review (with two human reviewers)

> Aplica-se APENAS quando `review_type: systematic_review_with_2_reviewers` E `two_reviewer_kappa_documented: true` no metadado do manuscrito.
> Este é o único modo no qual o termo "Systematic Review" pode ser usado.

## Selo obrigatório no header

```html
<div class="review-mode-badge mode-sr-strict" role="status">
  <strong>Systematic Review</strong>
  <span class="mode-detail">following PRISMA-2020 with two independent human reviewers (kappa = X.XX)</span>
  <span class="mode-disclaimer">AI-assistance limited to specified stages with full disclosure (see §03).</span>
</div>
```

CSS sugerido (SR estrito = verde escuro):
```css
.review-mode-badge.mode-sr-strict {
  background: #e8f5e9;
  border-left: 4px solid #2e7d32;
  padding: 12px 16px;
  margin: 16px 0;
}
```

## Pré-requisito ELIMINATÓRIO (E16)

Para usar este modo, o manuscrito DEVE incluir:

1. **Identificação dos dois revisores humanos** (nomes + afiliações + ORCIDs).
2. **Cohen's kappa documentado** entre os dois revisores em pelo menos: triagem (title/abstract), inclusão (full-text), extração de dados.
3. **Disagreement resolution protocol** descrito (consenso, terceiro revisor, voto).
4. **Evidência verificável** que ambos revisores são humanos (não dois modelos LLM).

Se algum desses ausente, o ghostwriter REJEITA o modo SR estrito e oferece scoping/rapid/mapping como alternativas.

## Seções obrigatórias

### §03 — Two-reviewer process explícito (PRISMA-2020 itens 8 e 9)

Texto-padrão (preencher):

> "**Selection process:** Title/abstract screening was performed independently by two human reviewers ([Reviewer 1: Name, ORCID] and [Reviewer 2: Name, ORCID]). Inter-rater agreement at title/abstract stage: Cohen's kappa = X.XX (interpretation: [substantial / almost perfect]). Disagreements were resolved by [consensus discussion / third reviewer / pre-defined protocol]. Full-text screening followed the same independent two-reviewer protocol (kappa = X.XX). Data extraction was performed independently by both reviewers using a piloted extraction form (kappa = X.XX on a 20% random sample). The Reviewers' Agreement Log is available in the Reproducibility Package."

### §03 — Declaração de uso de IAG (modo SR estrito)

Mesmo com 2 revisores humanos, se IA foi usada em qualquer estágio, declarar:

> "**Declaration of AI use** — In addition to the two independent human reviewers, AI was used as a [supporting tool / not used] for: [list specific stages — e.g., 'preliminary search-string expansion (validated by both reviewers)', 'duplicate detection (verified by both reviewers)']. AI was NOT used as a substitute for either human reviewer in screening, full-text inclusion, extraction, critical appraisal, or synthesis. Model parameters and prompts (if applicable) are deposited in the Reproducibility Package."

## Reporting guideline aplicável

`PRISMA-2020` (27 itens) — perfil completo em `references/profiles/_guidelines/prisma-2020.yaml`.

Adicionalmente, conforme área:
- Saúde: pode adicionar **MECIR** (Cochrane) ou **AMSTAR-2** (auditoria).
- CS/SE: pode adicionar **SIGSOFT-EMP-STANDARDS**.
- Educação/Ciências Sociais: pode adicionar **CAMPBELL-STANDARDS**.

## Selos no metadado YAML

```yaml
review_type: systematic_review_with_2_reviewers
review_purpose: design_foundational  # ou independent_inquiry
reporting_guideline_primary: PRISMA-2020
reporting_guideline_secondary: []
reviewer_count_human: 2  # OBRIGATÓRIO ≥ 2
reviewer_count_ai: 0  # ou 1 se assistente, mas NUNCA substitui revisor humano
ai_dual_check_sample_pct: null  # N/A
two_reviewer_kappa_documented: true  # OBRIGATÓRIO true
two_reviewer_kappa_screening: 0.XX
two_reviewer_kappa_fulltext: 0.XX
two_reviewer_kappa_extraction: 0.XX
reviewer_1_orcid: ""  # OBRIGATÓRIO preenchido
reviewer_2_orcid: ""  # OBRIGATÓRIO preenchido
disagreement_resolution_method: "consensus"  # ou "third_reviewer", "pre-defined_voting"
title_must_contain: "Systematic Review"
prospero_or_osf_registration_id: "CRDXXXXXXXXX"  # OBRIGATÓRIO preenchido
```

## Nota crítica sobre escala

Este modo é o único que justifica o termo "Systematic Review", mas exige dois revisores humanos qualificados. Para o projeto base do usuário (5-200 RS), este modo será raro — viável apenas para revisões de altíssima prioridade onde valha a pena envolver um segundo revisor humano qualificado. A maior parte da produção será em modos scoping, rapid e mapping.
