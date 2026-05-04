# Quality appraisal — Template

Aplicado a cada estudo incluído. Escolher UM instrumento na fase de protocolo; mantê-lo até o fim. Mudar de instrumento meio da SLR invalida a pré-registro.

## Instrumento 1: DARE (genérico, 5 questões)

Database of Abstracts of Reviews of Effects, NHS Centre for Reviews and Dissemination.

| # | Questão | Sim (1) | Parcial (0.5) | Não (0) |
|---|---------|---------|---------------|---------|
| QA1 | Os critérios de inclusão são apropriados para a RQ? | | | |
| QA2 | A busca foi adequada para identificar todos os estudos relevantes? | | | |
| QA3 | A qualidade dos estudos incluídos foi avaliada? | | | |
| QA4 | Os detalhes básicos dos estudos foram fornecidos? | | | |
| QA5 | Os achados foram sintetizados apropriadamente? | | | |

**Total:** 0–5. Threshold típico: ≥ 3.

## Instrumento 2: Kitchenham QA1–QA5 (engenharia de software)

| # | Questão | Sim (1) | Parcial (0.5) | Não (0) |
|---|---------|---------|---------------|---------|
| QA1 | Os objetivos do estudo são claramente declarados? | | | |
| QA2 | O escopo, contexto e desenho experimental são definidos? | | | |
| QA3 | As variáveis são prováveis de serem válidas e confiáveis? | | | |
| QA4 | O processo de pesquisa é documentado adequadamente? | | | |
| QA5 | Todas as questões do estudo são respondidas? | | | |

**Total:** 0–5. Threshold típico: ≥ 2.5.

## Instrumento 3: Dyba-Dingsoyr 11Q (SE empírico, mais rigoroso)

Recomendado quando a SLR é em SE empírico. Cobre 4 dimensões: rigor, credibilidade, relevância, qualidade do reporte.

| # | Questão | Sim | Parcial | Não |
|---|---------|-----|---------|-----|
| 1 | O estudo é claramente reportado como pesquisa empírica? | | | |
| 2 | Há declaração clara dos objetivos? | | | |
| 3 | A pesquisa é adequada ao problema? | | | |
| 4 | O design é justificado? | | | |
| 5 | A estratégia de amostragem é justificada? | | | |
| 6 | Os métodos de coleta de dados foram adequadamente descritos? | | | |
| 7 | A análise é suficientemente rigorosa? | | | |
| 8 | A relação pesquisador-participantes foi adequadamente considerada? | | | |
| 9 | Há declaração clara dos achados? | | | |
| 10 | O estudo é de valor para pesquisa ou prática? | | | |
| 11 | Os achados podem ser transferidos para outros contextos? | | | |

**Total:** 0–11. Threshold típico: ≥ 6.

## Instrumento 4: CASP (Critical Appraisal Skills Programme)

CASP tem checklists específicos por design:
- Systematic Review (10 questões)
- Randomized Controlled Trial (11)
- Qualitative Studies (10)
- Cohort (12)
- Case-control (11)
- Diagnostic Test (12)
- Economic Evaluation (12)
- Clinical Prediction Rule (10)

Cada questão é "Sim/Talvez/Não/Não pode dizer". Não há score numérico unificado — interpretação narrativa por dimensão (validade, resultados, aplicabilidade).

Use CASP quando a SLR é em saúde e mistura designs heterogêneos. Documentos oficiais em https://casp-uk.net/casp-tools-checklists/.

## Procedimento

1. Dois revisores independentes pontuam cada estudo.
2. Conflitos: discutir; se persistir, terceiro revisor.
3. Calcular Cohen's kappa entre os dois revisores (esperado ≥ 0.6 para "boa concordância", ≥ 0.8 para "excelente").
4. Estudos abaixo do threshold: marcar como "baixa qualidade". Decisão: excluir da síntese OU manter mas sinalizar visualmente nas tabelas.

## Cohen's kappa — fórmula

```
κ = (po − pe) / (1 − pe)
```

Onde:
- `po` = concordância observada (proporção de itens classificados igual pelos dois revisores)
- `pe` = concordância esperada por acaso

Interpretação (Landis & Koch, 1977):

| κ | Concordância |
|---|--------------|
| < 0.00 | Pobre |
| 0.00–0.20 | Leve |
| 0.21–0.40 | Razoável |
| 0.41–0.60 | Moderada |
| 0.61–0.80 | Boa |
| 0.81–1.00 | Quase perfeita |

Calcular separadamente para: triagem T/A, triagem FT, QA. Reportar todos no manuscrito.

## Saída

Salvar como `quality-appraisal.csv`:

```csv
study_id,reviewer1_QA1,reviewer1_QA2,...,reviewer1_total,reviewer2_QA1,...,reviewer2_total,consensus_QA1,...,consensus_total,passed_threshold,notes
```
