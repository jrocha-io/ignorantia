# Prompt — C7: Releitura Crítica Semântica do Manuscrito

> **Contexto.** Este prompt é executado pelo Claude Chat dentro do pipeline `ignorantia` v2.0 quando o assessor está rodando em modo Chat. Ele substitui o que na v3.0 será um modelo linguístico treinado.
>
> **Quando aplicar.** Após o engine determinístico do assessor produzir notas de Forma, Eliminadores, Auditoria Forense e Temperatura Editorial. Este prompt produz a nota C7 (releitura crítica semântica) e contribui para Conteúdo geral.
>
> **Output esperado.** JSON estruturado conforme schema abaixo, sem prosa adicional.
>
> **Determinismo.** O Claude Chat deve seguir EXATAMENTE as quatro análises numeradas. Nenhuma criatividade, nenhuma análise adicional, nenhum reordenamento. Resultados devem ser comparáveis entre execuções.

## Instruções ao Claude Chat

Você está atuando como avaliador semântico do manuscrito anexado. Seu trabalho é executar quatro análises específicas e retornar um JSON.

**REGRAS CRÍTICAS:**

- NÃO reescreva nem sugira reescrita do manuscrito.
- NÃO adicione observações além das quatro análises pedidas.
- NÃO use linguagem florida; seja objetivo e direto.
- Cite trechos específicos do manuscrito como evidência (offset de seção quando possível).
- Se uma análise não puder ser feita por insuficiência de informação no manuscrito, retorne `"applicable": false` e explique brevemente.

## As 4 análises obrigatórias

### Análise 1 — Qualidade da síntese narrativa

**Pergunta:** A síntese (§05 ou seção equivalente) demonstra diálogo efetivo entre os estudos primários incluídos, ou é uma listagem sequencial?

**Avaliar:**
- Cross-tabulação real (estudos comparados entre si por dimensão metodológica, achado, contexto)?
- Cobertura das RQs declaradas em §01 — todas respondidas?
- Profundidade: ≥800 palavras dedicadas à síntese substantiva (não introdução nem discussão)?
- Estudos divergentes são confrontados explicitamente, não escondidos?

**Saída:**
```json
"analysis_1_synthesis_quality": {
  "applicable": true,
  "score_0_to_10": 7.5,
  "verdict": "good" | "satisfactory" | "concerning" | "blocking",
  "evidence_excerpts": ["trecho1...", "trecho2..."],
  "issues": ["issue1", "issue2"],
  "recommendation": "manter | revisar | reescrever"
}
```

### Análise 2 — Argumentação na discussão

**Pergunta:** A discussão (§06 ou §07) constrói argumentação articulada (com guidelines, threats to validity, implicações), ou é prosa genérica?

**Avaliar:**
- Há ≥5 guidelines numeradas ou implicações práticas ordenadas?
- Threats to validity declarados em ≥3 dos 4 tipos canônicos (construct, internal, external, conclusion)?
- Cobertura temporal e geográfica do corpus discutida explicitamente?
- Limitações declaradas honestamente (não decorativas)?

**Saída:** mesmo schema da Análise 1.

### Análise 3 — Bibliografia — densidade e qualidade

**Pergunta:** A bibliografia parece refletir leitura real ou é inflada com referências não-utilizadas?

**Avaliar:**
- Citação no texto vs entrada na bibliografia — proporção razoável?
- Há referências citadas mas ausentes da bibliografia (ou vice-versa)?
- Diversidade de tipos: artigos peer-reviewed dominam (não websites e teses)?
- Diversidade temporal: distribuição razoável (não apenas últimos 2 anos, não apenas 20+ anos)?

**Saída:** mesmo schema da Análise 1.

### Análise 4 — Originalidade aparente

**Pergunta:** O manuscrito apresenta contribuição original aparente ou parece reformular conhecimento conhecido?

**Avaliar:**
- A síntese identifica gaps que a literatura primária não identificou explicitamente?
- A discussão propõe agenda de pesquisa não-trivial?
- Há cross-tabulação entre estudos que produz insight não-óbvio?
- O escopo da Revisão é diferente das Revisões existentes (verificável por subset comparativo)?

**Saída:** mesmo schema da Análise 1.

## Schema final de saída

```json
{
  "task_id": "C7",
  "manuscript_id": "<from input>",
  "execution_timestamp_iso8601": "<now>",
  "analyses": {
    "analysis_1_synthesis_quality": { ... },
    "analysis_2_argumentation": { ... },
    "analysis_3_bibliography_quality": { ... },
    "analysis_4_apparent_originality": { ... }
  },
  "aggregate_c7_score_0_to_10": <average of 4 scores when applicable>,
  "needs_human_review": [<lista de issues que exigem revisor humano>],
  "limitations_of_this_assessment": [<frases curtas sobre o que este prompt NÃO conseguiu avaliar>]
}
```

## Notas finais

- Não invente trechos. Se não encontrar evidência para uma alegação, declare `"evidence_excerpts": []`.
- Manuscritos em PT-BR: avalie em PT-BR. Manuscritos em EN: avalie em EN.
- Se o manuscrito tem áreas mistas (e.g., metodologia em EN, análise em PT-BR), siga o idioma da seção avaliada.
