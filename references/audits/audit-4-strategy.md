# Estratégia auditoria #4 — fixes C1 a C8

Plano de 3 sprints respondendo aos 8 achados da auditoria #4 da v2.21.0. Consolidação em release única **v2.22.0**.

## Mandato

Usuário (2026-05-04 pós-auditoria #4): *"Sim"*. Autonomia para criar estratégia e executar. Princípio reforçado: **integração ≠ implementação** + **schema consistente** entre adapters.

## Sprint U1 — P1 coerência declarativa + DeprecationWarning

| Fix | O que faz | Smoke validation |
|---|---|---|
| **C1+C2** | Unificar schema dos 4 retrofitted (arxiv, crossref, dblp, semantic_scholar): adicionar `year_range` no top-level (consistente entre 4); adicionar campos item-level faltantes (`year` em arxiv, `doi` em dblp, `language` e `is_oa` quando aplicável). Manter retrocompat. | Schema dump consistente entre 4 retrofitted |
| **C4** | README.md ganha linha de status com contadores: 61 adapters, 57 TIER1_RUNNERS, 7 áreas, 6 etapas, 16 paywall, 12 DDs. | grep README retorna 5+ contadores |
| **C5** | `render_manuscript.py` emite `DeprecationWarning` em runtime quando importado. | `python3 -W error -c "import render_manuscript"` falha com DeprecationWarning |

## Sprint U2 — P1 parsers reais para 4 adapters ibero (Decisão 25)

| Fix | O que faz | Esforço |
|---|---|---|
| **C3 parcial** | Implementar parsers reais para 4 adapters ibero prioritários (Decisão 25): `clacso` (HTML/OAI-PMH), `dialnet` (HTML público), `pepsic` (BVS portal — pattern do LILACS), `scielo_preprints` (OJS REST API). Padrão: regex/JSON conservador com fallback honesto. | médio |

## Sprint U3 — P2/P3 refinamento

| Fix | O que faz | Esforço |
|---|---|---|
| **C6** | Adapters sem parser (11 restantes após U2): substituir `method: <X>_REAL` por `method: <X>_REAL_PARTIAL` quando retornam apenas raw_size_bytes. Honestidade explícita no schema. | leve |
| **C7** | Validar referências cross-doc após B12 (referencias/audits/). Atualizar caminhos antigos AUDIT_FIXES_STRATEGY.md → audits/audit-N-strategy.md em CHANGELOG, journal, MODES_OVERVIEW. | leve |
| **C8** | Decisão arquitetural sobre renderers HTML: documentar em DD nova (DD-13) que `render_chunks.py` é canônico e `render_v2.py` é alternativo standalone, sem migração planejada (custo > benefício). | leve |

## Critérios de pausa entre sprints

- Cada sprint fecha com **regressão verde** + smoke E2E (testes B13 continuam passando).
- Empacotar como **v2.22.0 consolidada** ao final dos 3 sprints.

## Cronograma proposto

U1 → C1+C2+C4+C5 — esta sessão (~25%)
U2 → C3 parcial (4 parsers) — esta sessão (~40%)
U3 → C6+C7+C8 — esta sessão (~20%)
Empacotamento + docs — esta sessão (~15%)

## Histórico

| Data | Sprint | Status |
|---|---|---|
| 2026-05-04 | Plano auditoria #4 | criado |

## Histórico (atualizado)

| Data | Sprint | Status |
|---|---|---|
| 2026-05-04 | Plano auditoria #4 | criado |
| 2026-05-04 | U1 (C1, C2, C4, C5) | ✅ entregue (em v2.22.0) |
| 2026-05-04 | U2 (C3 — 4 parsers ibero) | ✅ entregue (em v2.22.0) |
| 2026-05-04 | U3 (C6, C7, C8) | ✅ entregue (em v2.22.0) |
| (futuro) | C3 resto (parsers para 11 adapters restantes em _REAL_PARTIAL) | 🔜 v2.23.0+ |
