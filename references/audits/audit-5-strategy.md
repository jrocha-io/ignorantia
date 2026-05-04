# Estratégia consolidada — auditoria #5 (D1-D6) + análise SOLID/DRY (E1-E10)

Plano único respondendo aos achados pendentes. Consolidação em **v2.23.0**. Não empacotar até pedido explícito do usuário.

## Mandato

Usuário (2026-05-04 pós-criação do AUDIT_PROCEDURE.md): *"Primeiro, corrija todos os bugs ainda não corrigidos. O problema: o objetivo era ter sido feita uma análise exploratória para buscar novas categorias. Desde o começo foi adotado práticas de código limpo, como SOLID? Padrões que um arquivo adota e outro deveria adotar parece caracterizar uso de código repetido."*

**Princípio reforçado**: muitas das categorias detectadas em auditorias anteriores são **sintomas** de violações DRY/SOLID, não causas independentes. USER_AGENT em 9 versões (DRY), schema item-level heterogêneo (Liskov), pipeline_finalize que requer modificar core para nova etapa (Open/Closed).

## Pendências consolidadas

### Auditoria #5 (D1-D6, não-aplicada)

- **D1**: schema legacy OA heterogêneo (doaj sem `year_range`, scielo schema antigo, vários com `url_for_pdf` em vez de `url`)
- **D2**: 35+ adapters "outros" com schemas variados
- **D3 CRÍTICO**: schema mock dos 4 retrofitted DIVERGE do real (arxiv real sem `language`/`is_oa`/`url`/`venue`; crossref real sem `language`/`is_oa`; dblp real sem `language`/`is_oa`; s2 real sem `language`/`is_oa`)
- **D4**: `FetchedItem` é canônico mas só 16 paywall usam — escopo grande, **adiar para v3.0.0**
- **D5**: orquestrador mostra `[warn] eric — erro:` com mensagem VAZIA (A7 não generalizado)
- **D6**: orquestrador NÃO gera resumo final agregado

### Análise das 27 dimensões (DIM 4, 11, 12)

- **DIM 4**: SKILL.md diz "61 adapters" mas há **62**
- **DIM 11**: USER_AGENT fossilizado em **10 valores diferentes** (`2.6.0`, `2.9.0`, `2.10.0`, `2.10.1`, `2.10.2`, `2.11.0`, `2.12.0` etc.) — DRY violation
- **DIM 12**: throttle/max_results/timeout defaults inconsistentes entre adapters

### Análise SOLID/DRY (E1-E10) — bugs novos detectados

- **E1**: `source_tier` é `int` em paywall/legacy (`1`, `2`) e **`str`** em retrofitted (`'tier1'`, `'tier2'`) — **Liskov violation grave**. Pós-processadores quebram silenciosamente.
- **E2**: USER_AGENT em 10 valores diferentes — **DRY violation**. Cada adapter fossiliza versão. Solução: derivar de `VERSION` constant única (já existe em `contextual_preamble.VERSION`).
- **E3**: argparse boilerplate repetido em 42 adapters legacy. Paywall já usa `_adapter_base.cli()` helper. Padrão NÃO foi generalizado aos legacy. Bug futuro: adicionar flag em todo adapter requer 42 edits.
- **E4**: `_mock` / `_real` / `_cli` pattern repetido 35-45 vezes — sem classe base abstrata para legacy. **Open/Closed violation**: cada novo adapter copia código.
- **E5**: 13 ocorrências de throttle/sleep com magic number (`0.5`, `1.0`, `2.0`, `3.0`) em vez de derivar de `DEFAULT_THROTTLE`.
- **E6**: `method` field é magic string (`"BDTD_REAL_PARTIAL"`, `"DOAJ_MOCK"`, etc.) sem enum/Literal type. Tipos de método: `MOCK | REAL | REAL_PARTIAL | REAL_ERROR`. **41+ valores duplicados**.
- **E7**: Funções gigantes — `search_orchestrator.main` tem **283 linhas**; `slr_to_package.build_content_json` tem 277 linhas. **Single Responsibility violation**.
- **E8**: 22 ocorrências de `datetime.now()` em outputs JSON — **reprodutibilidade**. Padrão correto: timestamp configurável via param `now: datetime | None = None`.
- **E9**: 0 validações de `jsonschema` em 78 `json.dump` — falta de validação de output. Schema do adapter é implícito/derivado.
- **E10**: pipeline_finalize tem 12 funções `_step_*` mas não há registry/lista — adicionar etapa nova requer editar `run_pipeline()` core. **Open/Closed violation**.

## Plano de sprints (consolidado em v2.23.0)

### Sprint W1 — P0 críticos (mock/real divergência + Liskov)

| Fix | O que faz | Prioridade |
|---|---|---|
| **D3** | `parse_entry()` arxiv adiciona `language`, `is_oa`, `url`, `venue`. `normalize()` crossref/dblp/s2 adicionam `language`, `is_oa`. Mock e real geram schema item-level idêntico. | P0 |
| **E1** | `source_tier` SEMPRE `int` (1, 2, 3) — string `'tier1'`/`'tier2'` viram apenas labels derivados. Ou: SEMPRE string canônica (`"tier1"`/`"tier2"`/`"tier3"`). Decisão: usar **string** porque já é majoritário e mais legível em JSON. Migrar `int` → `string` em paywall/legacy. **Adicionar `tier` numérico como campo separado** (`source_tier: "tier1", source_tier_num: 1`) para retrocompat. | P0 |
| **D5** | Helper `print_error_to_stderr_if_present(result)` em `_adapter_base.py`. Generalizar a todos adapters com pattern `return 0 if not r.get("error") else 1`. Eliminar `[warn] eric — erro:` vazio. | P0 |

### Sprint W2 — P1 schema unificado + DRY

| Fix | O que faz |
|---|---|
| **D1+D2** | Adapters legacy OA: adicionar `year_range`, normalizar `n` → `total_results` em scielo (mantendo `n` alias), adicionar `method`/`year_start`/`year_end` em scielo. `url_for_pdf` ganha `url` alias quando ausente. Cobertura: doaj, scielo, oapen, core, osf_preprints, zenodo, biorxiv, eric, europepmc. |
| **E2 (USER_AGENT)** | Criar `scripts/_skill_version.py` com constante única `VERSION = "2.23.0"`. Todos os USER_AGENT derivam dela. Função `build_user_agent(contact_email)` retorna `f"ignorantia-skill/{VERSION} ({contact_email}) python-urllib/{python_ver}"`. |
| **E5 + DIM 12** | Adapters legacy importam `DEFAULT_THROTTLE`/`DEFAULT_TIMEOUT` de `_adapter_base`. Defaults consistentes. |
| **E6** | Em `_adapter_base.py`, `class AdapterMethod(str, Enum)` com `MOCK = "MOCK"`, `REAL = "REAL"`, `REAL_PARTIAL = "REAL_PARTIAL"`, `REAL_ERROR = "REAL_ERROR"`. Tipo de método torna-se enumerável e checkable. |

### Sprint W3 — P1 orquestrador + paridade declarativa

| Fix | O que faz |
|---|---|
| **D6** | Orquestrador gera `orchestration_summary.json` no final com: tier1_total, tier2_total, tier3_total, adapters_run, adapters_with_error, timestamp_start/end, output_files. |
| **DIM 4** | SKILL.md "61 adapters" → "62 adapters". Validar todos os contadores no inventário automatizado. |
| **DIM 11** | Após E2, todos os USER_AGENT batem com VERSION única. |

### Sprint W4 — P2 SRP/Open-Closed (escopo controlado)

| Fix | O que faz |
|---|---|
| **E10** | `pipeline_finalize.py` migra para registry de steps: `STEPS = [Step(name="cross_tab", fn=_step_cross_tab, skip_flag="skip_cross_tab"), ...]`. `run_pipeline()` itera o registry. Adicionar nova etapa = adicionar tupla. |
| **E8** | Funções com `datetime.now()` em outputs aceitam param `now: datetime | None = None` (default `datetime.now(timezone.utc)`). Reprodutibilidade quando passado explicitamente. |
| **E3+E4 (parcial)** | Helper `legacy_adapter_cli(search_fn, source_name, source_tier)` em `_adapter_base.py` para reduzir argparse boilerplate em **3-5 adapters representativos** como prova de conceito. Migração completa ficaria para v2.24.0+ por escopo. |

### Adiados explicitamente

- **D4** (FetchedItem migration): escopo grande, breaking change → **v3.0.0**
- **E3+E4 completo**: 42 adapters legacy migrados para classe base → **v2.24.0+** (após validar pattern em 3-5)
- **E7** (funções gigantes): refactoring estrutural → **v2.24.0+**
- **E9** (jsonschema validation): adicionar dependência + writing schemas → **v2.24.0+**
- **DIM 16, 17 completo**: validação schema + reprodutibilidade total → **v2.24.0+**

## Smoke validation requerido (antes de fechar release)

1. Schema mock vs real idêntico em arxiv/crossref/dblp/s2 (D3).
2. `source_tier` é tipo consistente em todos os 61 adapters (E1).
3. USER_AGENT bate com VERSION em todos (E2).
4. Orquestrador gera `orchestration_summary.json` (D6).
5. `[warn] X — erro: <mensagem útil>` em todos os adapters (D5).
6. `pipeline_finalize.py --contextual-preamble --preamble-mock` propaga ao HTML/docx/tex (smoke E2E).
7. **325 testes existentes verdes** + 25-30 novos para v2.23.0.

## Política de empacotamento

**Não empacotar zips em `/mnt/user-data/outputs/` até instrução explícita do usuário.** Trabalho persiste em `/home/claude/ignorantia_v2/` entre sessões.

## Histórico

| Data | Item | Status |
|---|---|---|
| 2026-05-04 | Plano consolidado #5+6 | criado |

## Histórico (atualizado)

| Data | Sprint | Status |
|---|---|---|
| 2026-05-04 | Plano consolidado #5+SOLID/DRY | criado |
| 2026-05-04 | W1 (D3, E1, D5) | ✅ entregue (em v2.23.0) |
| 2026-05-04 | W2 (D1+D2, E2, E5, E6) | ✅ entregue (em v2.23.0) |
| 2026-05-04 | W3 (D6, DIM 4) | ✅ entregue (em v2.23.0) |
| 2026-05-04 | W4 (E10) | ✅ entregue (em v2.23.0) |
| (futuro) | E3+E4 (legacy_adapter_cli helper, argparse DRY) | 🔜 v3.0.0 (incluído no refactoring) |
| (futuro) | E7 (funções gigantes refatoradas) | 🔜 v3.0.0 |
| (futuro) | E8 (datetime.now param) | 🔜 v3.0.0 |
| (futuro) | E9 (jsonschema validation) | 🔜 v3.0.0 |
| (futuro) | D4 (FetchedItem migration) | 🔜 v3.0.0 (breaking change) |

**Padrão TDD aplicado pela primeira vez**: 34 testes escritos ANTES dos fixes em `test_v2230_audit5_solid_dry.py`. Faseamento red→green confirmado: 30 passed + 4 failed na fase red (E6 enum, D6 summary, E10 registry); todos green após implementação.

**Plano v3.0.0** detalhado em `references/V3_ARCHITECTURE_PLAN.md` — Clean Architecture/DDD/ports & adapters/TDD estrito/cobertura ≥90%/mypy strict/9 fases. Cowork adiado para v4.
