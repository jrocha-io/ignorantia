# Protocolo de Comparação Automatizada — Etapa 4b da `ignorantia`

**Versão do protocolo:** 1.0.0 (criado v2.5.0, 2026-05-03)
**Versão da ferramenta avaliada:** `ignorantia` v2.5.0
**Status:** infraestrutura mínima funcional. **Sem casos reais ainda.**

## 1. Propósito

Documentar o protocolo e fornecer scripts reprodutíveis para comparar a `ignorantia` contra baselines de SLR tooling, conforme mapeamento técnico em `/mnt/project/Baseline_Mapping_for_Automated_Comparison_of_the_ignorantia_Tool_v2_4_0.md`.

**Esta infraestrutura NÃO produz validação empírica por si só.** Ela cria o andaime — quando casos reais (SLRs efetivamente conduzidas com a ferramenta) existirem, basta alimentar o pipeline com manuscritos + ground truth e os scripts produzem o relatório comparativo.

## 2. Escopo

A comparação cobre **três das quatro categorias funcionais** mapeadas no artifact baseline:

| Categoria | Baseline integrado | Modo de execução |
|---|---|---|
| 1 — Journal recommenders | B!SON (TIB), JANE (scaffold), snapshots manuais (Elsevier/Springer/Wiley/T&F/IEEE/Clarivate) | Real API + mock fallback |
| 2 — SLR screening | ASReview LAB v2 (modo simulação) | Subprocess + fixture fallback |
| 3 — Compliance/reporting checkers | Penelope.ai (snapshot manual), GoodReports (decision tree codificado) | Snapshot ingestion |

**Categoria 4 (submission systems) é explicitamente excluída.** Editorial Manager, ScholarOne, OJS e eJournalPress fazem validação de metadados, não comparação semântica de conteúdo. Esta exclusão é declarada e auditável.

## 3. Princípios

1. **Categorização antes de quantificação.** Cada métrica é computada apenas dentro de sua categoria funcional. Comparações cross-category são proibidas.
2. **Datasets compartilhados onde possível.** SYNERGY (ASReview) para screening; corpus interno para venue ranking; corpus PRISMA-2020 anotado para compliance.
3. **Frozen baselines onde APIs não existem.** Snapshot datado e versionado; sem scraping (ToS).
4. **Output unificado em JSON estável.** Schema versionado, validado, alimenta dashboards.
5. **Fallback gracioso.** Cada cliente tem modo `mock` para CI rodar sem dependências externas.

## 4. Datasets de input (a fornecer pelo usuário)

### 4.1 Para venue recommenders

- `manuscripts/<id>.json` no schema `manuscript_input.schema.json`. Campos: `title`, `abstract`, `references` (DOIs), `language`, `mode` (modo `ignorantia`), `ground_truth_venue` (venue real de publicação).
- **Volume mínimo para inferência estatística:** N ≥ 50. Para piloto: N ≥ 5.

### 4.2 Para screening

- Dataset SYNERGY (van de Schoot, DOI 10.34894/HE6NAQ). Não requer fornecimento — o wrapper baixa do GitHub `asreview/synergy-dataset` se solicitado.

### 4.3 Para compliance

- `compliance_corpus/<id>.json` com anotação humana item-a-item dos 27 itens PRISMA-2020. Volume mínimo: 30 manuscritos para κ confiável.

## 5. Métricas computadas

| Categoria | Métricas primárias | Implementadas em |
|---|---|---|
| Recommenders | Top-1, Top-5, Top-10 accuracy; MRR; nDCG@10 | `metrics/topk.py` |
| Screening | WSS@95; recall@k; ATD | `metrics/wss.py` |
| Compliance | F1 item-level; sensibilidade; especificidade; Cohen's κ | `metrics/compliance.py` |

## 6. Pipeline ponta-a-ponta

```
manuscripts/<id>.json   ──┐
                          ├──→  clients/bson.py     ──┐
                          ├──→  clients/jane.py     ──┤
                          ├──→  clients/snapshot.py ──┼──→ unify.py ──→ unified_output.json
ground_truth.json       ──┤                          │       │
                          ├──→  clients/asreview.py ──┤       └──→ metrics/*.py
ignorantia engine       ──┘                          │              │
                                                     │              ↓
                                                     └──→ report.py ──→ comparison_report.{md,html}
```

## 7. Comandos canônicos

```bash
# Smoke test (sem dependências externas, usa mocks)
cd scripts/comparison
python -m pytest tests/ -v

# Pipeline com 1 manuscrito (modo mock para B!SON e ASReview)
python -m clients.bson --input fixtures/manuscript_001.json --mock --out /tmp/bson_001.json
python -m clients.asreview --dataset SYNERGY/van_de_Schoot_2018 --mock --out /tmp/asr_001.json
python unify.py --inputs /tmp/bson_001.json /tmp/asr_001.json --ignorantia-out fixtures/ignorantia_001.json \
                --ground-truth fixtures/ground_truth.json --out /tmp/unified_001.json
python report.py --input /tmp/unified_001.json --out /tmp/report_001.md
```

## 8. Exclusões declaradas e auditáveis

| Excluído | Motivo |
|---|---|
| Editorial Manager, ScholarOne, OJS, eJournalPress | Workflow systems; não fazem comparação semântica de conteúdo |
| Wiley JF, T&F Suggester, IEEE Recommender | Caixas-pretas comerciais sem API; ToS proíbe scraping; opção é snapshot manual em P3 |
| Trinka, Writefull, Paperpal | Writing assistants B2B com licença paga; não comparáveis ao engine determinístico |
| Rayyan (modo screening além de 3 reviews) | Modelo paid; integração se v2.5+ estender escopo a triagem |

## 9. Limitações desta infraestrutura

1. **Sem casos reais.** Os fixtures são sintéticos. Resultados do smoke test **não constituem validação empírica.**
2. **B!SON cobre apenas DOAJ.** Para venues não-OA dos 68 perfis YAML, B!SON é silente; não é falha — é cobertura editorial divergente.
3. **JANE em modo scaffold.** Cliente é stub que aguarda implementação real (self-host Lucene ou contato direto com Schuemie). Documentado como TODO.
4. **Snapshots manuais não automatizam.** O ingestor lê arquivos JSON pré-criados; submissão à UI dos publishers é manual e datada.

## 10. Próximos passos

Quando o usuário tiver 1-2 SLRs reais conduzidas com a ferramenta:

1. Converter cada SLR para `manuscripts/<id>.json` no schema padronizado.
2. Rodar `clients/bson.py` em modo real (sem `--mock`) para o subset OA.
3. Submeter à UI de Penelope.ai os manuscritos finais, salvar resultados em `snapshots/penelope_<YYYYMMDD>.json`.
4. Para cada manuscrito, rodar o engine `ignorantia` e salvar em `ignorantia_outputs/<id>.json`.
5. Rodar `unify.py` e `report.py`.
6. Reportar resultados como **Etapa 4b concluída** no journal e CHANGELOG, abrindo gate para Etapa 5 (PUBLISHABLE_ASPECTS_ANALYSIS retomado com base empírica).
