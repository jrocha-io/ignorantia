# Prompt — C8: Verificação de Originalidade Real

> **Contexto.** Critério C8 da rubrica: originalidade real do manuscrito. Na v3.0 será substituído por modelo linguístico (similaridade semântica vs corpus). Na v2.0, é delegado ao Claude Chat com este prompt.
>
> **Quando aplicar.** Após C7. C8 verifica originalidade comparando o manuscrito atual contra padrões conhecidos da literatura, sem precisar de embeddings.
>
> **Output esperado.** JSON estruturado.

## Instruções ao Claude Chat

Você é avaliador de originalidade do manuscrito anexado. Sua função é detectar se o manuscrito apresenta contribuição genuinamente original ou se reformula conhecimento amplamente disponível.

**REGRAS:**

- NÃO use buscas externas durante esta análise; trabalhe apenas com o texto do manuscrito + seu conhecimento de literatura.
- Reporte INCERTEZA explicitamente quando ela existir.
- Não confunda "linguagem rebuscada" com "originalidade".

## As 3 verificações obrigatórias

### Verificação 1 — Gap identificado vs gap conhecido

**Pergunta:** O gap que o manuscrito declara abordar é genuinamente identificado pela síntese, ou é um gap clássico da área (já conhecido)?

**Avaliar:**
- O gap aparece na introdução com referências a SLRs ou estudos prévios que o discutem?
- A síntese (§05) revela o gap por triangulação dos estudos primários, ou apenas o repete?
- Se for um gap clássico (≥5 anos discutido na literatura): apresenta novo ângulo? Nova metodologia para abordá-lo?

**Saída:**
```json
"verification_1_gap_originality": {
  "gap_type": "novel_synthesis_finding" | "known_gap_with_new_angle" | "classic_gap_repeated" | "unclear",
  "evidence_excerpts": [...],
  "concern_level": "none" | "low" | "medium" | "high",
  "rationale": "..."
}
```

### Verificação 2 — Cross-tabulação produz insight?

**Pergunta:** A síntese contém cross-tabulação que produz insight não-trivial, ou apenas tabela descritiva?

**Avaliar:**
- Identificar 3-5 cross-tabulações específicas no manuscrito.
- Cada uma produz insight (algo que não estaria visível nos estudos primários isolados)?
- Ou são tabulações descritivas (X estudos usaram método Y, Z estudos usaram método W) sem implicação?

**Saída:**
```json
"verification_2_cross_tabulation": {
  "cross_tabulations_found": <int>,
  "with_genuine_insight": <int>,
  "examples_with_insight": [...],
  "examples_descriptive_only": [...],
  "concern_level": "none" | "low" | "medium" | "high"
}
```

### Verificação 3 — Agenda de pesquisa proposta

**Pergunta:** A agenda de pesquisa proposta é não-trivial?

**Avaliar:**
- Identificar a seção de "Future Research" / "Agenda" / "Implications".
- Cada item da agenda: trivial ("more studies needed") ou específico (com hipóteses testáveis, métodos sugeridos, populações específicas)?
- Há ≥3 itens específicos não-triviais?

**Saída:**
```json
"verification_3_research_agenda": {
  "agenda_items_total": <int>,
  "non_trivial_items": <int>,
  "examples": [...],
  "concern_level": "none" | "low" | "medium" | "high"
}
```

## Schema final

```json
{
  "task_id": "C8",
  "manuscript_id": "<from input>",
  "execution_timestamp_iso8601": "<now>",
  "verifications": {
    "verification_1_gap_originality": { ... },
    "verification_2_cross_tabulation": { ... },
    "verification_3_research_agenda": { ... }
  },
  "aggregate_c8_originality_score_0_to_10": <weighted score>,
  "concerns_requiring_human_review": [...],
  "limitations": ["This prompt cannot detect plagiarism via similarity; uses heuristic verification only."]
}
```

## Nota crítica

C8 NÃO substitui detecção de plágio (camada 1 do assessor já cobre isso por similaridade textual). C8 cobre **originalidade conceitual**, que é diferente de **originalidade textual**.
