# Formulário de extração — Template

Um registro por estudo incluído. Salvar como CSV (ou XLSX) com colunas correspondentes a cada campo. Para SLRs grandes, usar planilha com filtros.

## Cabeçalhos (CSV)

```csv
study_id,citation,doi,year,venue,country,study_type,design,population,sample_size,intervention,comparator,outcomes_primary,outcomes_secondary,methods,limitations_declared,qa_score,rq_addressed,reviewer_notes
```

## Campos — descrição

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `study_id` | str | Identificador interno: S01, S02, ... |
| `citation` | str | Citação completa formatada na norma do projeto |
| `doi` | str | DOI (sem prefixo http) |
| `year` | int | Ano de publicação |
| `venue` | str | Periódico ou conferência |
| `country` | str | País(es) do estudo (do contexto, não da afiliação) |
| `study_type` | str | Empírico-quantitativo \| Empírico-qualitativo \| Empírico-misto \| Teórico \| Revisão \| Estudo de caso \| Survey \| RCT \| Outro |
| `design` | str | Detalhamento do desenho metodológico |
| `population` | str | População-alvo do estudo |
| `sample_size` | int / str | n; quando aplicável |
| `intervention` | str | Intervenção, objeto, fenômeno estudado |
| `comparator` | str | Grupo controle ou referência (vazio se não aplicável) |
| `outcomes_primary` | str | Achados/desfechos primários — em prosa concisa |
| `outcomes_secondary` | str | Achados secundários |
| `methods` | str | Métodos resumidos |
| `limitations_declared` | str | Limitações declaradas pelos autores |
| `qa_score` | float | Pontuação no instrumento de QA (ex.: 4.5 / 5) |
| `rq_addressed` | str | Quais RQs/sub-RQs o estudo responde (RQ1, RQ1.2, ...) |
| `reviewer_notes` | str | Notas do extrator (anomalias, dúvidas, decisões) |

## Campos extras opcionais

Adicionar conforme natureza do tema:

- `population_age_range` (ex.: idosos: 65+)
- `theoretical_framework` (Vygotsky, Piaget, Erikson, etc.)
- `technology` (plataforma, framework, dispositivo)
- `intervention_duration` (semanas, meses)
- `effect_size` (Cohen's d, Hedge's g, OR — quando reportado)
- `funding_source`
- `conflict_of_interest`
- `replicable` (sim/parcial/não — código/dados disponíveis?)

## Convenções

- **Não inventar.** Se um campo não está reportado no estudo, registrar `NR` (não-reportado), não estimar.
- **Citação direta:** usar aspas para frases extraídas verbatim. Sempre incluir página.
- **Texto longo:** preferir prosa concisa; se for longa, anexar em planilha separada e referenciar pelo `study_id`.
- **Conflitos entre revisores:** marcar com `[CONFLITO]` no campo, e arquivar em `conflict-log.md`.

## Exemplo preenchido (fictício)

```csv
study_id,citation,doi,year,venue,country,study_type,design,population,sample_size,intervention,comparator,outcomes_primary,methods,limitations_declared,qa_score,rq_addressed
S01,"Silva JP et al. ...",10.1590/ES.250214,2024,Educação & Sociedade,Brasil,Empírico-quantitativo,RCT,"Idosos 65+ alfabetizados",120,"Curso de informática básica via celular","Curso tradicional em laboratório","Adesão 87% vs 64%; ganho médio em letramento digital +18pp (p<0.001)","RCT 12 semanas; pré/pós com escala validada","Amostra única-cidade; sem follow-up >3 meses",4.5,"RQ1, RQ2.1"
```
