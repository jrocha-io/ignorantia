# Estratégia auditoria #3 — fixes B1 a B13

Plano de 3 sprints respondendo aos 13 achados da auditoria #3 da v2.20.0. Consolidação em release única **v2.21.0**.

## Mandato

Usuário (2026-05-04 pós-auditoria #3): *"Sim"* (autonomia para criar estratégia e executar). Princípio reforçado: **integração ≠ implementação** — todo fix precisa de regressão + smoke E2E real do caminho principal (pipeline_finalize).

## Sprint T1 — P0 vitrine quebrada arquitetural

| Fix | O que faz | Smoke validation |
|---|---|---|
| **B1** | `pipeline_finalize.py` propaga `contextual_preamble_markdown` aos 3 renderers (docx, latex, chunks). Adiciona flags `--contextual-preamble`, `--preamble-topic`, `--preamble-area`, `--preamble-language`, `--preamble-mock` no CLI. Gera o preâmbulo uma única vez e passa o mesmo Markdown aos 3 renderers. | Rodar `pipeline_finalize.py --contextual-preamble --preamble-mock` e verificar que `manuscript.html`, `manuscript.docx`, `manuscript.tex` contêm "campo onde este artigo vive" |
| **B2** | `render_chunks.py` aceita `contextual_preamble_html` ou `contextual_preamble_markdown` na função principal + injeção do bloco antes da Introdução (mesmo padrão do `render_v2.py`). | Pipeline gera HTML com `<section id="contextual-preamble">` |
| **B3** | `pipeline_finalize.py` docstring atualizada para 6 etapas (incluindo screening_pipeline). | grep da docstring retorna "6 outputs" |
| **B5** | SKILL.md placeholder "+N" → "+25 = 291". | grep "+N" SKILL.md retorna 0 |
| **B6** | `search_la_referencia.py` docstring de uso: `results_lareferencia.json` → `results_la_referencia.json`. | grep "results_lareferencia" retorna 0 |

## Sprint T2 — P1 coerência + teste E2E

| Fix | O que faz | Smoke validation |
|---|---|---|
| **B4** | 4 adapters retrofitted (arxiv, crossref, dblp, semantic_scholar) usam `total_results` no JSON output em vez de `n`. **Manter `n` como alias para retrocompat** (não quebrar pós-processadores existentes que possam ter sido escritos esperando `n`). | Schema unificado em `total_results`; `n` ainda lido se presente |
| **B8** | `tests/test_v21_modes.py`: substituir `open(path)` por `with open(path) as f: ...`. | Regressão sem ResourceWarnings (≤ 5; era 182) |
| **B11** | Avaliar `render_manuscript.py`: se realmente legacy não-usado, marcar com warning de deprecation no topo do arquivo. Se usado em algum lugar, manter. | Decision documentada |
| **B13** | Novo teste E2E `tests/test_v2210_e2e_pipeline.py` que roda `pipeline_finalize.py` completo com fixtures + valida que artefatos finais contêm preâmbulo (smoke real subprocess). | Teste valida B1+B2 end-to-end |

## Sprint T3 — P2/P3 refinamento

| Fix | O que faz | Esforço |
|---|---|---|
| **B7** | F15/A9 resto: parsers reais para 2 dos 16 adapters restantes em `_REAL_PARTIAL`. Priorizar `redalyc` via OAI-PMH (estrutura padrão Dublin Core) e `scielo_preprints` via OJS REST API. | médio |
| **B9** | `_markdown_to_latex`: detectar asteriscos órfãos não-fechados e escape literal ao invés de retornar Markdown cru. | leve |
| **B12** | Consolidar `AUDIT_FIXES_STRATEGY.md` e `AUDIT2_FIXES_STRATEGY.md` em diretório `references/audits/` ou em `AUDIT_LOG.md` único. | leve |
| **B10** | Escolher um renderer HTML canônico. Decisão: `render_chunks.py` é o renderer principal (usado pelo pipeline). `render_v2.py` continua disponível como alternativa 4-tabs. Documentar em SKILL.md. | leve |

## Critérios de pausa entre sprints

- Cada sprint fecha com **regressão verde** + smoke E2E (T1 e T2).
- T3 fica para v2.21.0 ou pode ser parcial (B7 restante fica para v2.22.0+).
- Empacotar como **v2.21.0 consolidada** ao final.

## Cronograma proposto

T1 → B1+B2+B3+B5+B6 — esta sessão (~30%)
T2 → B4+B8+B11+B13 — esta sessão (~30%)
T3 → B7+B9+B10+B12 — esta sessão (~25%)
Empacotamento + docs — esta sessão (~15%)

## Histórico

| Data | Sprint | Status |
|---|---|---|
| 2026-05-04 | Plano auditoria #3 | criado |

## Histórico (atualizado)

| Data | Sprint | Status |
|---|---|---|
| 2026-05-04 | Plano auditoria #3 | criado |
| 2026-05-04 | T1 (B1, B2, B3, B5, B6) | ✅ entregue (em v2.21.0) |
| 2026-05-04 | T2 (B4, B8, B11, B13) | ✅ entregue (em v2.21.0) |
| 2026-05-04 | T3 (B7, B9, B10, B12) | ✅ entregue (em v2.21.0) |
| (futuro) | B7 resto (parsers para 15 adapters restantes em _REAL_PARTIAL) | 🔜 v2.22.0+ |
