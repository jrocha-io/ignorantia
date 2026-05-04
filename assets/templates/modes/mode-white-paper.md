# Mode template — White Paper / Policy Brief

> Aplica-se quando `review_type: white_paper` ou `review_type: policy_brief` no metadado.
> Camada hierárquica: **Secundária** (problema + recomendações vêm do usuário).
> Combinar com o template-base.

## Selo obrigatório no header

```html
<div class="review-mode-badge mode-white-paper" role="status">
  <strong>White Paper / Policy Brief</strong>
  <span class="mode-detail">following Brookings/RAND/Carnegie/ICCT conventions</span>
  <span class="mode-disclaimer">Not peer-reviewed. Informed positioning for decision-making, not scientific consensus claim.</span>
</div>
```

CSS sugerido (white paper = bege institucional):
```css
.review-mode-badge.mode-white-paper {
  background: #f5f5f0;
  border-left: 4px solid #6d4c41;
  padding: 12px 16px;
  margin: 16px 0;
}
```

## Pré-requisitos (Camada Secundária)

ANTES de iniciar este modo, o usuário deve declarar:

1. **O problema de política pública** (educação, IA, tecnologia, saúde, etc.) que o documento aborda.
2. **A audiência alvo** específica (formuladores de política em qual nível? indústria? sociedade civil?).
3. **As recomendações principais** que quer fazer (sem isso, o documento vira descritivo, não prescritivo).
4. **As limitações** que reconhece (o que o documento NÃO faz).

Sem essas quatro declarações iniciais, o ghostwriter pede esclarecimento. Isso evita White Papers ambíguos que misturam descrição e prescrição sem clareza.

## Venue padrão e alternativas (OA-first)

**Padrão**: **Zenodo** (White Paper / Policy Brief category). $0 APC, DOI persistente, neutralidade institucional. Coerente com ethos OA-first e com a natureza do formato (alcance público).

**Alternativas explicadas**:
- **OSF Preprints (Policy section)**: $0, alternativa OA, fácil submissão.
- **SciELO Preprints**: $0, alta visibilidade Latam, especialmente para temas brasileiros.
- **SSRN (Public Policy Network)**: $0, alta visibilidade ciências sociais e política pública.
- **Repositório institucional do autor**: para uso interno organizacional ou da universidade.

White Papers são por natureza o modo mais coerente com OA-first: o objetivo é alcançar formuladores de política, indústria, sociedade civil — não academia tradicional. Paywall vai contra o propósito.

A ferramenta apresenta a escolha ao usuário no início.

## Seções obrigatórias

### Executive Summary (1 página máximo — assinatura do formato)

OBRIGATÓRIO. Sem Executive Summary, o documento NÃO É White Paper — vira Technical Report ou Position Paper. Estrutura típica:

> "**Key findings**:
> - [Achado 1, frase única]
> - [Achado 2, frase única]
> - [Achado 3, frase única]
>
> **Recommendations**:
> - [Recomendação 1, acionável]
> - [Recomendação 2, acionável]
> - [Recomendação 3, acionável]
>
> **For**: [audiência específica]"

### Background / Problem Statement

Contexto + por que importa agora + magnitude do problema (com dados oficiais quando disponíveis).

### Findings

Síntese de evidências relevantes. Não exaustivo (não é SR). Mistura:
- Evidência peer-reviewed (preferencialmente OA)
- Relatórios oficiais (OECD, UNESCO, Banco Mundial, BNCC, etc.)
- Estatísticas oficiais (IBGE, INEP, etc., conforme tema brasileiro)
- Grey literature relevante

### Policy Recommendations (prescritivas, acionáveis)

Cada recomendação deve ter:
1. **Ação específica**: o que deve ser feito.
2. **Ator responsável**: quem deve fazer (Ministério X, Secretaria Y, organização Z).
3. **Timeframe**: quando (curto/médio/longo prazo).
4. **Recursos estimados**: viabilidade econômica, quando relevante.

Recomendações vagas como "mais pesquisa é necessária" são insuficientes. Reviewers/leitores penalizam.

### Limitations (OBRIGATÓRIO)

O que este documento NÃO faz:
- Não é peer-reviewed.
- Não pode ser citado como evidência primária.
- Não pode reivindicar status de "consenso científico".
- Limitações de escopo (geográfico, temporal, populacional).
- Limitações da base de evidência consultada (apenas OA? apenas até data X?).

White Paper sem limitations declaradas confunde-se com propaganda. Declarar limites é essencial à honestidade do formato.

### Target audience explicit

Em texto OU no metadado. Recomendações dirigidas vagamente a "todos" são menos eficazes.

### References

Mistura honesta de fontes (peer-reviewed + relatórios + dados oficiais + grey literature). Citação completa para verificabilidade.

### AI Disclosure (OBRIGATÓRIA)

Texto-padrão:

> "**Declaration of AI use** — Generative AI was used in the preparation of this White Paper as follows:
> - Tool: [model name + version]
> - Stages of use: [e.g., 'drafting Background section', 'organizing Findings into themes', 'searching grey literature in OA repositories', 'editorial revision']
> - Stages NOT used: [e.g., 'core policy recommendation formulation', 'ethical evaluation', 'final wording approval']
> - Author's responsibility: All policy recommendations and final positions are the author's. AI assisted with structure and synthesis of evidence; the prescriptive content is human-authored."

### Conflicts of Interest + Funding

OBRIGATÓRIO declarar afiliação institucional + financiamento + qualquer relação com partes interessadas no problema abordado.

### Plain Language Summary (recomendado)

Para audiência leiga (sociedade civil, imprensa). 200-300 palavras. No topo do documento, antes do Executive Summary, ou como destaque.

## Selos no metadado YAML

```yaml
review_type: white_paper
review_purpose: independent_inquiry  # ou design_correction se documento responde a falha de política existente
reporting_guideline_primary: WHITE-PAPER-GENERIC
target_venue_primary: zenodo_white_paper
target_venue_alternatives: [osf_preprints_policy, scielo_preprints, ssrn_public_policy, institutional_repository]
target_audience: ""  # policymakers_federal | policymakers_state | policymakers_municipal | industry | civil_society | press
policy_problem: ""
key_recommendations: []
recommendations_actor: ""  # ator responsável esperado
recommendations_timeframe: ""  # short | medium | long
geographic_scope: ""  # global | regional | national | subnational
authors:
  - name: ""
    orcid: ""
    affiliation: ""
    institutional_role: ""
ai_disclosure_required: true
funding: ""
conflicts_of_interest: ""
plain_language_summary_present: false
```

## Notas críticas

- White Papers NÃO são peer-reviewed. Para impacto acadêmico, considere Modo 6 (Position Paper) com submissão a venue peer-reviewed.
- White Papers TÊM impacto político/social maior que papers acadêmicos quando bem feitos e bem distribuídos.
- White Paper é o formato natural para o caso "IA e jogos educacionais não substituem professor" do projeto base — defesa de posição de política pública educacional brasileira, audiência primária formuladores de política e gestores educacionais.
- Para o caso brasileiro, considerar adicionalmente versão em PT-BR depositada em SciELO Preprints + repositório universitário, para máximo alcance da audiência alvo.
