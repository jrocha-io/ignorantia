# Mode template — Software Paper

> Aplica-se quando `review_type: software_paper` no metadado do manuscrito.
> Camada hierárquica: **Secundária** (exige software pronto fornecido pelo usuário).
> Combinar com o template-base.

## Selo obrigatório no header

```html
<div class="review-mode-badge mode-software-paper" role="status">
  <strong>Software Paper</strong>
  <span class="mode-detail">following SOFTWARE-PAPER-GENERIC standard (JOSS-aligned)</span>
  <span class="mode-disclaimer">Document about research software. AI-assisted drafting with full disclosure.</span>
</div>
```

CSS sugerido (software paper = ciano):
```css
.review-mode-badge.mode-software-paper {
  background: #e1f5fe;
  border-left: 4px solid #0277bd;
  padding: 12px 16px;
  margin: 16px 0;
}
```

## Pré-requisitos (Camada Secundária)

ANTES de iniciar este modo, o usuário deve confirmar que:

1. **Software já existe** e está hospedado em repositório Git público (GitHub, GitLab, Codeberg, Sourcehut).
2. **License OSI-approved** declarada (MIT, Apache-2.0, BSD-3-Clause, GPL, LGPL, MPL).
3. **Tests existem** no repositório (qualquer framework — pytest, Jest, JUnit, etc.).
4. **Documentation existe** (README + docs/ ou wiki).
5. **Repositório público ≥6 meses** com active development (gate JOSS).
6. **Uso real demonstrável** além do autor (gate JOSS, mais flexível em outros venues).

Se algum desses ausente, o ghostwriter REJEITA o modo Software Paper e oferece alternativas:
- Modo 7 (Technical Report) se o software existe mas não cumpre os gates.
- Modo 6 (Position Paper) se a contribuição é conceitual sobre o software, não sobre o software pronto.

## Venue padrão e alternativas (OA-first)

**Padrão**: **JOSS** (Journal of Open Source Software). $0 APC, peer review aberto público, foco em software de pesquisa, formato curto (750-1750 palavras). Coerente com ethos OA-first.

**Alternativas explicadas**:
- **F1000Research (Software Tool Article)**: $1350-1850 APC, peer review pós-publicação aberto, formato mais flexível.
- **SoftwareX (Elsevier)**: $2400 APC, peer review tradicional, indexado WoS/Scopus, formato 4-6 páginas.
- **IEEE Software (Tools track)**: hybrid (~$2500 APC para OA), alta visibilidade IEEE, formato mais técnico.

A ferramenta apresenta a escolha ao usuário no início, com a justificativa do padrão e as alternativas.

## Seções obrigatórias

### Summary (high-level functionality, non-specialist audience)

Texto-padrão a guiar:

> "[Software name] is a [type of tool — library, application, framework] for [domain — e.g., Python data analysis, web visualization, etc.] that addresses [specific research need]. [Software name] enables [target users — e.g., bioinformaticians, education researchers] to [primary capability]. The software is implemented in [language] and is available as open source under [license]."

### Statement of need

Texto-padrão a guiar:

> "[Domain area] research increasingly requires [specific capability]. Existing tools such as [Tool A] and [Tool B] address [partial aspect] but do not [specific gap]. [Software name] fills this gap by [specific contribution]. Target users are [audience]. The software has been used in [list real applications / publications enabled by it]."

ATENÇÃO: para JOSS, "uso real além do autor" é GATE. Sem demonstração concreta de uso, JOSS faz desk-reject.

### State of the field (comparison with related software)

Comparar com 3-5 ferramentas similares. Tabela recomendada com dimensões de comparação.

### Software design / architecture

Visão geral da arquitetura (diagrama recomendado, não obrigatório). Não detalhar API — isso fica na documentação do software.

### Use cases / examples

1-3 exemplos concretos de uso (preferencialmente referenciando publicações onde o software foi usado).

### AI usage disclosure (OBRIGATÓRIO em JOSS 2025)

Texto-padrão:

> "**AI usage disclosure** — Generative AI was used in the development of this software paper as follows:
> - Tool: [Claude Opus 4.7 / GPT-X / etc., versão]
> - Where used: [e.g., 'drafting paper text', 'generating documentation examples', 'code refactoring suggestions']
> - Nature and scope of assistance: [e.g., 'drafting Statement of Need section, validated by author', 'docstring formatting', 'test scaffolding']
> - Confirmation: All AI-assisted outputs were reviewed, edited, and validated by the human author(s). All core design decisions, scientific claims, and architectural choices were made by humans."

### Acknowledgements

Financiamento + contribuidores que não atendem critérios de autoria.

### References

Citações com nomes completos de venues (não abreviações específicas de área).

## Selos no metadado YAML do manuscrito

```yaml
review_type: software_paper
review_purpose: independent_inquiry  # tipicamente
reporting_guideline_primary: SOFTWARE-PAPER-GENERIC
target_venue_primary: joss
target_venue_alternatives: [f1000research_software, softwarex_elsevier, ieee_software_tools]
software_name: ""
software_repo_url: ""
software_license: ""  # MIT, Apache-2.0, BSD-3-Clause, GPL-3.0, etc.
software_tests_present: true
software_docs_present: true
repo_public_since: ""  # YYYY-MM-DD; deve ser ≥6 meses antes da submissão a JOSS
real_users_demonstrated: false  # GATE para JOSS; declarar honestamente
authors:
  - name: ""
    orcid: ""
    affiliation: ""
ai_disclosure_required: true
funding: ""
conflicts_of_interest: ""
```

## Notas críticas

- Software Paper sobre o **próprio ignorantia** seria interessante, mas tem problema de circularidade epistêmica (a ferramenta produz o paper sobre a ferramenta). Isso é resolvível mas exige decisões editoriais delicadas (declaração explícita de self-generation, peer review pós-deposit, etc.).
- Software Papers NÃO devem reportar resultados novos de pesquisa — isso é um paper de pesquisa, não software paper. O foco é o **software como contribuição**, não os achados que ele permite.
- Se o software ainda não tem uso real além do autor, **considerar adiar a submissão** até que haja casos de uso reais documentados, ou submeter a F1000Research (mais flexível).
