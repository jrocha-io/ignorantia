# Changelog ignorantia

Todas as mudanças notáveis serão documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento [SemVer 2.0.0](https://semver.org/lang/pt-BR/spec/v2.0.0.html).

## [3.0.0-rc1] — 2026-05-07

**Release candidate da reescrita Clean Architecture v3.** Reorganiza
o pacote em quatro camadas (`domain/` · `application/` ·
`infrastructure/` · `interface/`) com cinco bounded contexts isolados
(search · render · pipeline · compliance · audit), CLI Click com
quatro subcomandos schema-validados, e camada de compatibilidade
para chamadas v2.

A v2.x continua funcionando inalterada durante a transição —
`scripts/` não foi removido. O cronograma de descontinuação está em
[`docs/MIGRATION_v2_TO_v3.md`](docs/MIGRATION_v2_TO_v3.md).

### Adicionado

- **Quatro camadas Clean Architecture** sob `src/ignorantia/`:
  `domain/` (cinco bounded contexts), `application/` (use cases +
  DTOs), `infrastructure/` (adapters concretos, 58 search adapters
  + 4 renderers + 4 citation formatters), `interface/` (Click CLI).
- **CLI Click** com quatro subcomandos: `audit`, `finalize`,
  `render`, `search`. Cada subcomando emite uma linha JSON validada
  contra um JSON-schema em `src/ignorantia/interface/manifests/`.
- **Quatro use cases** em `application/use_cases/`: `RunAuditUseCase`,
  `FinalizePipelineUseCase`, `RenderManuscriptUseCase`,
  `SearchForStudiesUseCase`. Cada um traduz Command DTO ↔ domínio
  via portas (DIP).
- **Strategy pattern de citações**: `CitationFormatterPort` com
  quatro implementações (ABNT NBR 6023:2018, APA 7th, IEEE numeric,
  Vancouver/ICMJE) + `citation_formatter_for(style)` factory.
- **Strategy pattern de renderers**: `RendererPort` com três
  implementações (HTML, LaTeX, DOCX). DOCX gated no extra opcional
  `[docx]`. `InteractiveRendererPort` para incrementação por seção
  (HTML).
- **`ManuscriptDoc.builder()`** — builder fluente para montagem
  incremental de manuscritos.
- **`PipelineExecutor` + `PipelineStep`** — registry pattern do v2
  (E10) reescrito como serviço de domínio tipado.
- **`ComplianceEngine`** — sucessor do `scripts/compliance/engine.py`
  com `Decision`/`DesignDecision`/`Severity` value objects e
  `VenueProfile`/`ComplianceReport` agregados.
- **`ManifestService`** + `ReproducibilityManifest` — sucessor de
  `scripts/manifest_helpers.py` (Decisões 21+22) como persistent
  data structure.
- **`ignorantia.legacy`** — pacote de compatibilidade que emite
  `DeprecationWarning` no import e expõe `migration_guide()` com
  o mapeamento v2→v3.
- **Documentação completa**: `README` v3 quickstart,
  `docs/TUTORIAL.md` (<30 min), `docs/architecture/C4_DIAGRAMS.md`
  (Mermaid), API reference scaffold MkDocs + mkdocstrings em
  `docs/api/`, `docs/MIGRATION_v2_TO_v3.md`, anexo v3 em
  `references/audits/AUDIT_PROCEDURE.md`.

### Mudanças (vs v2.x)

- **Injeção de relógio (issue #13)**: zero `datetime.now()` em
  `domain/` ou `application/`. Toda chamada centralizada em
  `interface/cli/main._real_clock()` e injetada via `clock`
  callable nos serviços que dependem dela.
- **HTTP centralizado**: `infrastructure/http_client.py` único.
  Adapters de busca não chamam `urllib.request.urlopen` diretamente.
  USER_AGENT, throttle, retry, timeout configurados centralmente.
- **Schemas runtime (issue #14)**: cada saída JSON do CLI é
  validada contra Draft 2020-12 schema em
  `interface/manifests/*.schema.json` antes do `click.echo`. Drift
  do DTO falha o build.
- **Bounded contexts isolados**: contextos `domain/<ctx>` não
  importam de outros contextos `domain/`. Comunicação cross-context
  passa por DTOs em `application/`.

### Critérios de aceitação v3.0.0 — status

Veja
[`docs/RELEASE_READINESS_v3.0.0-rc1.md`](docs/RELEASE_READINESS_v3.0.0-rc1.md)
para a verificação mecânica detalhada. Resumo:

- ✅ `mypy --strict` verde em `domain/` + `application/`
- ✅ Cobertura ≥ 90% em `domain/` (98.72%) + `application/` (100%)
- ✅ Zero `urllib.request` fora de `infrastructure/http_client.py`
- ✅ Zero `argparse` fora de `interface/cli/`
- ✅ Zero `datetime.now()` em `domain/`
- ✅ CHANGELOG completo com migration guide v2 → v3
- ✅ Tutorial: SLR do zero compila em <30 minutos
- ✅ Cowork mencionado como roadmap v4, não implementado
- ✅ 58 search adapters (`AdapterFactory`) + 2 Tier-0 OA resolvers
  (`OaResolverFactory`) — paridade com v2 (a contagem v2 original
  de "62 adapters" misturava as duas portas; em v3 estão separadas)
- ⚠️ RS-42 dogfooding: deferido para sprint entre rc1 e estável

### Pendências para v3.0.0 estável

1. Sprint de dogfooding RS-42 — execução real-network dos 58
   adapters + ciclo `render` → `finalize` completo.
2. Migrar steps concretos do `scripts/pipeline_finalize.py` para
   `infrastructure/pipeline/` (v3 `finalize` roda registry vazio
   no rc1).
3. Bump de `version` em `pyproject.toml` de `2.23.0` para `3.0.0`
   após dogfooding sign-off.

### Métricas

- **2146** testes verde, 1 skipped (DocxRenderer atrás do extra
  `[docx]`; CI roda).
- **58** adapters de busca registrados no `AdapterFactory`.
- **5** bounded contexts (`audit`, `compliance`, `pipeline`,
  `render`, `search`).
- **4** subcomandos CLI, **4** JSON-schemas, **4** citation styles,
  **3** renderers, **4** use cases.
- Cobertura geral do pacote v3: **87%**.

## [2.23.0] — 2026-05-04

**Release de auditoria iterativa #5 + análise SOLID/DRY.** Foco principal: **paridade mock vs real** (D3, raiz da #5), **Liskov substitution** em adapters (E1), **DRY de USER_AGENT** (E2), **Open/Closed em pipeline** (E10), **stderr informativo** (D5), **orquestrador summary** (D6). Aplicação rigorosa de TDD: 34 testes escritos ANTES dos fixes.

### Auditoria iterativa #5 — pendências consolidadas

A v2.22.0 detectou D1-D6 (auditoria #5) mas não consolidou em release. Ao mesmo tempo, o usuário pediu análise exploratória aplicando SOLID/DRY desde a primeira rodada. Resultado: 10 achados adicionais (E1-E10), muitos sendo **causa raiz** de inconsistências detectadas em rodadas anteriores.

### Sprint W1 — P0 críticos

- **D3 — Paridade mock vs real (CRÍTICO)**: arxiv `parse_entry()` ganha campos essenciais (`language`, `is_oa`, `url`, `venue`, `year` como int); crossref/dblp/s2 `normalize()` ganham `language`, `is_oa`. Antes da v2.23.0, mock tinha esses campos (C1/v2.22.0) mas real não — pós-processadores quebravam silenciosamente em produção.
- **E1 — source_tier Liskov violation**: tipos heterogêneos (`int 1` em paywall/legacy, `str 'tier1'` em retrofitted). Migrado para **string canônica em todos os 58 adapters**: `"tier0"`, `"tier1"`, `"tier2"`, `"tier3"`. `_adapter_base.SOURCE_TIER` agora é `str`. Testes legados atualizados.
- **D5 — stderr informativo**: helper `cli_exit_with_error_message(result, source_name)` em `_adapter_base.py`. Aplicado em **35 adapters** que tinham pattern `return 0 if not r.get("error") else 1` sem `print(file=sys.stderr)`. Antes da v2.23.0, orquestrador mostrava `[warn] eric — erro:` com mensagem vazia (A7 não generalizado).

### Sprint W2 — P1 schema unificado + DRY

- **D1+D2 — Schema legacy OA unificado**: `year_range` adicionado em **20 adapters** legacy que não tinham. SciELO migra de schema antigo (`n` apenas) para schema canônico (`total_results, n, method, year_start, year_end, year_range`).
- **E2 — USER_AGENT centralizado (DRY)**: novo módulo `scripts/_skill_version.py` com `VERSION = "2.23.0"` como single source of truth + `build_user_agent(contact_email)` helper. **36 adapters** migrados de `USER_AGENT = "ignorantia-skill/X.Y.Z"` hardcoded para `from _skill_version import VERSION`. **Distintos USER_AGENT: 10 → 1**. Antes da v2.23.0, adapters fossilizavam versões antigas (2.6.0, 2.9.0, 2.10.0, 2.10.1, 2.10.2, 2.11.0, 2.12.0...).
- **E5 — DEFAULT_THROTTLE/DEFAULT_TIMEOUT**: já existiam em `_adapter_base.py` mas adapters legacy hardcoded. Padrão de uso documentado.
- **E6 — AdapterMethod enum**: `class AdapterMethod(str, Enum)` em `_adapter_base.py` com valores `MOCK`, `REAL`, `REAL_PARTIAL`, `REAL_ERROR`. Substitui magic strings (41+ valores ad-hoc tipo `"BDTD_REAL_PARTIAL"`). Helper `from_string()` mapeia legados.

### Sprint W3 — P1 orquestrador + paridade declarativa

- **D6 — Orchestration summary**: orquestrador agora gera `orchestration_summary.json` (nome canônico) com campos `started_at`, `finished_at`, `adapters_run`, `tier1_total`, `compliance`, `schema_version`. `search_summary.json` mantido como alias retrocompat.
- **DIM 4 — Paridade declarativa**: SKILL.md "61 adapters" → "62 adapters" (contagem real). README ganha contadores quantitativos no status ("62 adapters · 57 TIER1_RUNNERS · 7 áreas · 13 DDs..."). Testes atualizados para contagem dinâmica via `os.listdir`.

### Sprint W4 — P2 Open/Closed + SRP

- **E10 — Pipeline registry (Open/Closed)**: `pipeline_finalize.py` migra de 6 chamadas hardcoded a `_step_*` para `PIPELINE_STEPS = [PipelineStep(name, label, fn), ...]`. `run_pipeline()` itera o registry. **Adicionar nova etapa = adicionar tupla**, não editar core. Princípio Open/Closed aplicado.

### TDD aplicado

A v2.23.0 é a **primeira release escrita em TDD estrito**: 34 testes em `tests/test_v2230_audit5_solid_dry.py` foram escritos ANTES dos fixes correspondentes. Status no momento do "TDD red phase":
- 30 testes PASSED (cobertura W1+W2 já existente da v2.22.0 ajudou)
- 4 FAILED (E6 enum, D6 summary, E10 registry, DIM 4 contagem)

Após implementação, todos os 34 ficam GREEN. Validação posterior: 359/359 testes totais (regressão completa).

### Adicionado

- **`scripts/_skill_version.py`** — single source of truth para VERSION + helper `build_user_agent`.
- **`tests/test_v2230_audit5_solid_dry.py`** — 34 testes cobrindo D1-D6 + E1-E10.
- **`references/audits/audit-5-strategy.md`** — plano consolidado D1-D6 + E1-E10 + boas práticas SOLID/DRY.
- **`references/V3_ARCHITECTURE_PLAN.md`** — plano detalhado para v3.0.0 (Clean Architecture + DDD + bounded contexts + roadmap em 9 fases). Cowork adiado para v4.

### Estado dos contadores

- Decisões editoriais: 33 (inalterado).
- Decisões de design (DD): 13 (inalterado).
- Adapters de busca: **62** (não 61; correção declarativa).
- Módulos auxiliares: 4 (inclui novo `_skill_version.py`).
- TIER1_RUNNERS: 57.
- Áreas: 7.
- Pipeline_finalize: 6 etapas (registry-based).
- Adapters em `_REAL_PARTIAL`: 11 (inalterado).
- **Testes: 359/359** (era 325; +34 v2.23.0).

### Limitações operacionais declaradas

- E3+E4 (argparse boilerplate em legacy) parcialmente aplicado. Migração completa requer classe base abstrata para legacy adapters → planejado para v3.0.0.
- E7 (funções gigantes — `search_orchestrator.main` tem 283 linhas) não refatorado nesta release. Refactoring estrutural fica para v3.0.0.
- E8 (timestamp injection para reprodutibilidade byte-a-byte) não implementado. Planejado para v3.0.0 onde reproducibility é first-class concern.
- E9 (`jsonschema.validate` em outputs) não implementado. v3.0.0 com schemas em `interface/manifests/`.
- D4 (`FetchedItem` migration de 16 paywall para todos 62 adapters) deliberadamente adiado para v3.0.0 — breaking change.

### Pendente para v3.0.0

**Refactoring arquitetural** documentado em `references/V3_ARCHITECTURE_PLAN.md`:
- Bounded contexts DDD: `domain/{slr,search,render,compliance,audit}/`.
- Ports & adapters: `AdapterPort`, `RendererPort`, `CitationFormatterPort`.
- Use cases: `SearchForStudiesUseCase`, `RenderManuscriptUseCase`, etc.
- TDD estrito com cobertura ≥90% em domain.
- `mypy --strict`, `ruff`, `bandit`, `pip-audit` em CI.
- Cowork adiado para v4.

### O significado da release

A v2.23.0 é onde **a auditoria iterativa formalmente convergiu**. A regra reforçada anteriormente — "integração ≠ implementação" (#3) e "schemas devem ser canônicos no real, mocks copiam" (#5) — agora tem suporte estrutural via:

1. **Liskov-conformância em source_tier** (E1).
2. **DRY de USER_AGENT centralizado** (E2).
3. **Open/Closed em pipeline_finalize** (E10).
4. **Schema mock = schema real** validado por testes (D3).
5. **Manual de auditoria com 27 dimensões** (criado na sessão anterior; agora referenciado em SKILL.md).

A v3.0.0 vai além: aplicar Clean Architecture/DDD desde o primeiro commit, eliminando categorias inteiras de bugs (heterogeneidade entre adapters, schemas implícitos, etc.) por design.

---

## [2.22.0] — 2026-05-04

**Release de auditoria iterativa #4 — fechamento dos 8 achados que a auditoria #3 deixou.** Foco principal: **paridade declarativa** + **expansão de cobertura ibero-americana**. Schema unificado entre 3 categorias de adapters (paywall/legacy OA/retrofitted), 4 novos parsers reais (CLACSO, Dialnet, PePSIC, SciELO Preprints), DD-13 documenta decisão arquitetural sobre renderers HTML.

### Sprint U1 (P1 — coerência declarativa + DeprecationWarning)

- **C1+C2**: schema unificado entre os 4 retrofitted (arxiv, crossref, dblp, semantic_scholar). Top-level: todos têm `year_range` (era ausente em arxiv). Item-level: arxiv ganha `year`/`language`/`is_oa`/`venue`; dblp ganha `doi`; crossref+s2 ganham `language`/`is_oa`. Antes da v2.22.0, schema divergente entre adapters quebrava pós-processadores que esperavam estrutura uniforme.
- **C4**: README.md ganha linha de status quantitativa: 61 adapters · 57 TIER1_RUNNERS · 7 áreas · 16 paywall · 6 etapas pipeline · 12 DDs · 33 decisões editoriais · 315+ testes. Antes: rastreabilidade da versão atual exigia inspeção do CHANGELOG/SKILL.md.
- **C5**: `render_manuscript.py` emite `DeprecationWarning` em runtime ao ser importado (B11 da v2.21.0 marcou DEPRECATED apenas no docstring). Mensagem: usar `render_chunks.py` (canônico) ou `render_v2.py` (alternativo). Será removido em v3.0.0.

### Sprint U2 (P1 — parsers reais ibero-americanos, Decisão 25)

Implementados 4 novos parsers reais para os adapters mais críticos da Decisão 25 (bases ibero-americanas obrigatórias):

- **C3.1 — CLACSO** (`search_clacso.py`): parser DSpace via regex. Extrai `<div class="artifact-description">` blocks com título, autores (publisher/author), ano, idioma, URL handle. Schema normalizado completo. Idiomas: `spa`/`por`/`eng`/`fra` → `es`/`pt`/`en`/`fr`. Sai de `_REAL_PARTIAL`.
- **C3.2 — Dialnet** (`search_dialnet.py`): parser HTML para busca pública sem chave (`<li class="documento">` blocks). Schema normalizado. Antes da v2.22.0, fallback HTML retornava `_REAL_PARTIAL` com `results=[]`. Agora retorna items parseados; quando usuário tem `DIALNET_API_KEY`, JSON estruturado continua funcionando preferencialmente.
- **C3.3 — PePSIC** (`search_pepsic.py`): reusa `_parse_bvs_html` de `search_lilacs.py` (mesma estrutura BVS portal). Adiciona campos `source_indexer="PePSIC"`, `country="BR"`, `subject_area="psicologia"`. Cobertura sobreposta com LILACS — deduplicação recomendada downstream por título+autor.
- **C3.4 — SciELO Preprints** (`search_scielo_preprints.py`): parser OJS HTML via regex. Extrai `<div class="obj_article_summary">` blocks. Schema com `publication_type="preprint"`, `is_oa=True` por design. OAI-PMH alternativo declarado para harvest programático estruturado.

### Sprint U3 (P2/P3 — refinamento)

- **C6**: 3 adapters que retornavam `results=[]` mas declaravam `method=*_REAL` agora declaram honestamente `*_REAL_PARTIAL`: `bdtd`, `scioteca`, `grey_lit` (todos providers). Diferença schema-level entre adapters com parser real (REAL) vs sem parser (REAL_PARTIAL) agora é rastreável.
- **C7**: referência cross-doc em CHANGELOG corrigida: `references/AUDIT2_FIXES_STRATEGY.md` → `references/audits/audit-2-strategy.md` (caminho consolidado em B12/v2.21.0).
- **C8**: nova **DD-13** em `references/DECISIONS.md` documenta decisão arquitetural sobre renderers HTML. `render_chunks.py` é canônico (Decisão 18; usado pelo pipeline; 254 linhas); `render_v2.py` é alternativo standalone (4-tabs; 1042 linhas; não migrar features pelo custo>benefício); `render_manuscript.py` é DEPRECATED. SKILL.md atualizado para 13 DDs.

### Adicionado

- `tests/test_v2220_audit4_fixes.py` — **18 testes** cobrindo C1, C2, C3 (4 parsers), C4, C5, C6, C8.
- `references/audits/audit-4-strategy.md` — plano persistido de 3 sprints da auditoria #4.

### Bug corrigido durante a sessão

- Durante implementação de C3 (parser Dialnet), regex de `str_replace` removeu acidentalmente a função `def search()` em `search_dialnet.py`. Função restaurada antes do empacotamento; teste `test_dialnet_mock` (pré-existente) detectou e validou o fix.

### Estado dos contadores

- Decisões editoriais: 33 (inalterado).
- Decisões de design (DD): **13** (era 12; +DD-13 sobre renderer canônico).
- Adapters de busca: 61.
- Módulos auxiliares: 3.
- TIER1_RUNNERS: 57.
- Áreas: 7.
- Pipeline_finalize: 6 etapas.
- Adapters em `_REAL_PARTIAL`: **11** (era 15; saíram clacso, dialnet, pepsic, scielo_preprints).
- **Testes: 325/325** (era 307; +18 v2.22.0).

### Limitações operacionais declaradas

- Parsers ibero (CLACSO, Dialnet, PePSIC, SciELO Preprints) usam regex conservadora; estrutura HTML dos portais pode mudar quebrando o parser. Quando isso ocorrer, adapter retorna lista vazia honestamente em vez de blob.
- 11 adapters ainda em `_REAL_PARTIAL`: `bdtd, catalogo_teses_capes, cochrane_central, dabi, e_lis, grey_lit, jane, jstor_oa, proquest_oa, scioteca, spell`. Ficam para v2.23.0+.
- DeprecationWarning em `render_manuscript.py` quebra testes que usem `-W error::DeprecationWarning`. Mitigação: testes legados (`test_v28_eliminations.py`) usam suppressing de warnings ou modo padrão.

### Pendente para v2.23.0+

- Parsers reais para os 11 adapters restantes em `_REAL_PARTIAL`. Padrão estabelecido (regex conservadora + fallback honesto + filtro temporal local + schema normalizado) replicável.
- Teste E2E que compila PDF real (requer TeX Live no CI).
- Reexecução do estudo RS-42 com cobertura premium completa.

### O significado da release

A auditoria #3 detectou **integração ≠ implementação** (pipeline não propagava preâmbulo). A auditoria #4 detecta **schema declarado ≠ schema entregue** (4 retrofitted divergiam entre si). Ambas categorias só aparecem em comparação cruzada — testes unitários por adapter passariam.

A regra reforçada: **paridade declarativa importa**. Se 3 categorias de adapters (paywall, legacy OA, retrofitted) coexistem, schema item-level deveria ter um conjunto comum mínimo. v2.22.0 estabelece esse conjunto comum: `title, authors, year, doi, url, language, is_oa, venue` para todos os 61 adapters (com flexibilidade para campos específicos por categoria).

A v2.22.0 também é a **segunda release consecutiva sem bugs introduzidos pela própria iteração** (auditoria #4 detectou 0 bugs introduzidos pela v2.21.0). O erro de implementação durante o sprint (def search() removida em search_dialnet.py) foi detectado por teste pré-existente — exatamente o comportamento esperado de um sistema com cobertura adequada.

---

## [2.21.0] — 2026-05-04

**Release de auditoria iterativa #3 — fechamento dos 13 achados que a auditoria #2 deixou.** Foco principal: **integração arquitetural**. Os fixes da v2.20.0 funcionavam em renderers individuais mas o pipeline_finalize (caminho principal) **não propagava o preâmbulo contextual** aos artefatos finais. Esta release fecha esse ciclo.

### Sprint T1 (P0 — vitrine quebrada arquitetural)

- **B1**: `pipeline_finalize.py` propaga `contextual_preamble_markdown`/`_html` aos 3 renderers (chunks, docx, latex). Função `_generate_contextual_preamble()` cria o preâmbulo uma única vez e injeta via `args._preamble_html`/`._preamble_markdown`. Flags `--contextual-preamble`, `--preamble-topic`, `--preamble-area`, `--preamble-language`, `--preamble-mock` adicionadas ao CLI. Antes da v2.21.0, integração existia nos renderers individuais mas pipeline não passava — usuário rodando o caminho principal nunca obtinha preâmbulo nos artefatos finais.
- **B2**: `render_chunks.py` (renderer HTML usado pelo pipeline) ganha parâmetro `contextual_preamble_html`. Injeta o bloco antes do primeiro chunk (Introdução). Antes da v2.21.0, F4 atualizou apenas `render_v2.py`, mas pipeline usa `render_chunks.py`.
- **B3**: `pipeline_finalize.py` docstring atualizada para "6 outputs" (era "5 outputs"). Etapa 6 (`screening_pipeline.py`) foi adicionada em v2.19.0 mas docstring não havia sido atualizada.
- **B5**: SKILL.md placeholder "+N" preenchido (`v2.20.0: +25 = 291; v2.21.0: +16 = 307`).
- **B6**: `search_la_referencia.py` docstring de uso: `results_lareferencia.json` → `results_la_referencia.json` (alinha com a chave runner padronizada em F11/v2.19.0).

### Sprint T2 (P1 — coerência + teste E2E)

- **B4**: 4 adapters retrofitted (arxiv, crossref, dblp, semantic_scholar) agora retornam `total_results` no JSON output, mantendo `n` como alias para retrocompatibilidade. Antes da v2.21.0, esses 4 usavam apenas `n` enquanto os outros 57 adapters usavam `total_results` — schema inconsistente.
- **B8**: `tests/test_v21_modes.py` substituiu `yaml.safe_load(open(X))` por `yaml.safe_load(Path(X).read_text())`. Antes: 182 ResourceWarnings em CI por file descriptors não fechados; agora: 2.
- **B11**: `render_manuscript.py` marcado como **DEPRECATED em v2.21.0** com aviso explícito no topo do arquivo. Mantido apenas para compatibilidade com `test_v28_eliminations.py::test_decision_19_render_manuscript_default_interface_is_protected` (Decisão 33). Será removido em v3.0.0 ou quando teste migrar.
- **B13**: novo arquivo `tests/test_v2210_e2e_pipeline.py` com **16 testes E2E** que rodam `pipeline_finalize.py` via subprocess com fixtures e validam que artefatos finais (HTML, docx, tex) contêm preâmbulo contextual. Princípio reforçado: testes em renderers individuais NÃO garantem que o pipeline propaga features.

### Sprint T3 (P2/P3 — refinamento)

- **B7**: parser real para `search_redalyc.py` via JSON+HTML fallback (Decisão 25 — bases ibero-americanas). Estratégia conservadora: tenta JSON primeiro, fallback regex HTML, fallback honesto se ambos falharem. Schema normalizado: title/authors/year/venue/language/country/url/doi/is_oa/abstract_excerpt. Sai de `_REAL_PARTIAL`.
- **B9**: análise de asteriscos órfãos em `_markdown_to_latex` documentada como decisão. Input mal-formado (`*italic** ambíguo*`) é raro e LaTeX aceita `*` como literal; não complicar regex para edge case.
- **B10**: SKILL.md documenta o **renderer canônico**: `render_chunks.py` é o usado pelo pipeline_finalize; `render_v2.py` é alternativa 4-tabs standalone; `render_manuscript.py` é DEPRECATED.
- **B12**: arquivos `AUDIT*_FIXES_STRATEGY.md` consolidados em `references/audits/` com índice `AUDIT_LOG.md`. Facilita rastreabilidade em auditorias futuras.

### Adicionado

- `tests/test_v2210_e2e_pipeline.py` — **16 testes** cobrindo B1, B2, B3, B4, B5, B6, B7, B11.
- `references/audits/AUDIT_LOG.md` — índice das 3 auditorias.
- `references/audits/audit-{1,2,3}-strategy.md` — estratégias persistidas.

### Estado dos contadores

- Decisões editoriais: 33 (inalterado).
- Decisões de design (DD): 12 (todas implementadas).
- Adapters de busca: 61.
- Módulos auxiliares: 3.
- TIER1_RUNNERS: 57.
- Áreas: 7.
- Pipeline_finalize: 6 etapas.
- Adapters em `_REAL_PARTIAL`: **15** (era 16; saiu redalyc).
- **Testes: 307/307** (era 291; +16 v2.21.0).

### Limitações operacionais declaradas

- Sandbox bloqueia Wikipedia (HTTP 403 universal). B1 validado via mock e via flag `--preamble-mock` no E2E.
- B7 cobre apenas redalyc dentro dos 16 adapters em `_REAL_PARTIAL`. Os outros 15 (bdtd, catalogo_teses_capes, clacso, cochrane_central, dabi, dialnet, e_lis, grey_lit, jane, jstor_oa, pepsic, proquest_oa, scielo_preprints, scioteca, spell) ficam para v2.22.0+.
- Parser Redalyc é conservador (JSON+HTML fallback) — estrutura do endpoint pode mudar quebrando o parser. Quando isso ocorrer, adapter retorna lista vazia honestamente.
- E2E test não compila PDF real (TeX Live ausente no CI) nem testa render_docx_abnt sem python-docx (etapa retorna `skipped` se ausente).

### Pendente para v2.22.0+

- B7 resto: parsers reais para os 15 adapters restantes em `_REAL_PARTIAL`.
- Teste E2E que compila PDF real (requer TeX Live no CI).
- Reexecução do estudo RS-42 com cobertura premium completa.
- Avaliar remoção de `render_manuscript.py` quando testes legados forem migrados.

### O significado da release

A v2.20.0 entregou 9 fixes, mas a auditoria #3 detectou que **2 fixes (F4) ficaram em renderers individuais e nunca chegaram ao pipeline real**. Usuário rodando `pipeline_finalize.py` (caminho principal) não obtinha preâmbulo. Isso é categoria de bug que só aparece em smoke E2E real, não em testes unitários.

A v2.21.0 fecha esse ciclo com **16 testes E2E** que rodam o pipeline completo via subprocess. **A regra reforçada: integração ≠ implementação. Testes verdes em módulos individuais não garantem que o pipeline propaga os features.** Próximas auditorias terão menos pegada graças a essa cobertura.

---

## [2.20.0] — 2026-05-04

**Release de auditoria iterativa #2 — fechamento dos 9 achados que a auditoria #1 deixou.** Consolida 3 sprints (H1-H3) que corrigiram bugs introduzidos pela própria v2.19.0 (vitrine quebrada por correção, ironicamente) e gaps declarativos restantes. **Versão estável.**

### Sprint H1 (P0 — vitrine quebrada introduzida pela v2.19.0)

- **A1**: version stamps consistentes. `README.md` → 2.20.0; `contextual_preamble.py` `VERSION` → "2.20.0". Antes: README dizia v2.18.1 mesmo após v2.19.0; User-Agent enviado para Wikimedia mostrava versão errada.
- **A2**: F4 LaTeX bug — conversor `_markdown_to_latex()` completo. Trata corretamente: `*texto*` → `\textit{}`, `**texto**` → `\textbf{}`, `- item` → `\begin{itemize}\item ... \end{itemize}`, `[text](url)` → `\href{url}{text}` (URLs http/https). Pré-coalesce de linhas em parágrafos para italic/bold multi-linha. Antes da v2.20.0: PDF compilado tinha asteriscos crus visíveis e Markdown não convertido.
- **A3**: `search_arxiv.py` aceita `--year-start`/`--year-end` (compatível com orquestrador) E mantém `--start-date`/`--end-date` (retrocompat). Convert year→date YYYY-01-01/YYYY-12-31 internamente. Antes: orquestrador chamava `--year-start 2023` mas adapter declarava só `--start-date`, falhando completamente; arxiv era silenciosamente excluído de todas as buscas via orquestrador.

### Sprint H2 (P1 — coerência declarativa)

- **A4**: SKILL.md ganha seção "Estado quantitativo da skill (v2.20.0)" com contadores explícitos: 61 adapters, 57 TIER1_RUNNERS, 7 áreas, 6 etapas no pipeline, 270+ testes, 33 decisões editoriais, 12 DDs. Antes: rastreabilidade da versão atual exigia inspeção do CHANGELOG.
- **A5**: DOIs mock em `search_la_referencia.py` padronizados: `lareferencia-mock-XXX` → `la_referencia-mock-XXX` (alinhamento com a chave runner padronizada em F11/v2.19.0). URLs do site (lareferencia.info) ficam — é o domínio real.
- **A6**: 4 adapters legacy retrofitted com `--mock` no CLI: `search_arxiv.py`, `search_crossref.py`, `search_dblp.py`, `search_semantic_scholar.py`. Cada um tem fixture determinística com schema próprio. Antes: rodavam standalone só com rede real, impedindo CI determinístico.

### Sprint H3 (P2/P3 — refinamento)

- **A7**: `search_grey_lit.py` `_cli` imprime mensagem de erro em stderr antes de `return 1`. Permite ao orquestrador mostrar mensagem útil em `[warn]`, em vez de mensagem vazia. Comportamento auditável já existia (JSON com `_REAL_ERROR`); mensagem diagnóstica completa o ciclo.
- **A8**: `search_arxiv.py` `fetch_page()` ganha backoff exponencial em HTTP 429 (Too Many Requests). Retry 3x com `time.sleep(2**(attempt+1))`: 2s, 4s, 8s. arXiv tem rate limit estrito; antes da v2.20.0 falhava imediatamente em 429.
- **A9**: parser HTML real para `search_lilacs.py` via regex conservadora. Extrai `<div class="reference">` blocks do portal BVS, normaliza title/authors/year/language (Dublin Core: por→pt, spa→es, eng→en), filtra por janela temporal local. Sai do modo `_REAL_PARTIAL` (raw_size_bytes apenas). Estrutura HTML do iAH/BVS pode mudar; em caso de zero resultados, fallback honesto.

### Adicionado

- `tests/test_v2200_audit2_fixes.py` — **25 testes** cobrindo A1 a A9. Validação end-to-end (subprocess) para A2 (TeX sem Markdown cru), A3 (CLI args), A6 (4 adapters), e mocks (LILACS parser).
- `references/audits/audit-2-strategy.md` — plano persistido de 3 sprints da auditoria iterativa #2 (consolidado em `references/audits/` na v2.21.0 via B12).

### Estado dos contadores (v2.20.0)

- Decisões editoriais: 33 (inalterado).
- Decisões de design (DD): 12.
- Adapters de busca: 61.
- Módulos auxiliares: 3.
- TIER1_RUNNERS: 57.
- Áreas: 7.
- Pipeline_finalize: 6 etapas.
- Adapters em `_REAL_PARTIAL`: 16 (era 17; saiu LILACS após A9).
- **Testes: 291/291** (era 266; +25 v2.20.0).

### Limitações operacionais declaradas

- Sandbox de desenvolvimento bloqueia Wikipedia (HTTP 403 universal). A1 verifica que User-Agent agora declara versão correta; smoke real precisa ambiente com rede aberta + `IGNORANTIA_CONTACT_EMAIL`.
- A9 cobre apenas LILACS dentro dos 17 adapters em `_REAL_PARTIAL`. Os outros 16 (bdtd, catalogo_teses_capes, clacso, cochrane_central, dabi, dialnet, e_lis, jane, jstor_oa, pepsic, proquest_oa, redalyc, scielo_preprints, scioteca, spell, grey_lit) ficam para v2.21.0+.
- Parser LILACS é conservador via regex — estrutura HTML do BVS pode mudar quebrando o parser. Quando isso ocorrer, adapter retorna lista vazia honestamente e usuário deve combinar com PubMed (Cochrane CENTRAL pattern).

### Pendente para v2.21.0+

- A9 resto: parsers reais para os 16 adapters restantes em `_REAL_PARTIAL` (priorizar `redalyc` via OAI-PMH, `scielo_preprints` via OJS API).
- Testes E2E render_docx + render_latex compilando PDF real (requer `python-docx` + TeX Live no ambiente).
- Reexecução do estudo RS-42 com cobertura premium completa (medir delta empírico vs versões anteriores).

### O significado da release

A v2.19.0 entregou 23 fixes da auditoria #1 mas **introduziu 2 bugs novos** (A1 version stamps esquecidos; A2 conversor Markdown→LaTeX incompleto) e **deixou 1 bug pré-existente passar despercebido** (A3 arxiv argparse). Auditoria #2 detectou esses + 6 gaps declarativos. **A v2.20.0 fecha esse ciclo: testes agora cobrem versão stamps, smoke E2E de TeX gerado, e CLI subprocess dos 4 adapters legacy.** Próximas auditorias terão menos pegada por causa dessa cobertura mais rigorosa.

A regra reforçada: **toda correção precisa de regressão E smoke real**, não só "testes verdes".

---

## [2.19.0] — 2026-05-04

**Release de auditoria — fechamento dos 17 achados.** Consolida 4 sprints (S1-S4) que corrigiram os achados da auditoria v2.18.0. Sem novas funcionalidades vitrine; foco em **vitrine quebrada → vitrine funcional**, **promessas → realidade**, **funcionalidades isoladas → integradas ao pipeline**.

### Sprint 1 (P0 críticos)

- **F1**: `contextual_preamble.py` reescrito. User-Agent compliant Wikimedia (`<tool>/<version> (<contact>) <library>` formato), aceita `IGNORANTIA_CONTACT_EMAIL` via env. Resolução de título via Wikidata `wbsearchentities` + sitelinks (não exige mais título exato case-sensitive). Erros propagam via `WikimediaFetchWarning` + populam `self.fetch_errors`. Antes: silently `return None` em qualquer falha.
- **F2**: `SKILL.md` atualizado. Nova seção "Arquitetura v2.15-v2.18 — cobertura premium, logs, preâmbulo" inserida. Documenta cascata, 16 adapters paywall com nomes técnicos, disclosure 4-categorias, logs em duas camadas, preâmbulo Wikipedia/Wikidata. Antes: invisível para skill em runtime.
- **F3**: `README.md` atualizado: `2.0.0-alpha25` → `2.18.1+ estável`. Diferenciais incluem cobertura premium, logs, preâmbulo.
- **F4**: integração de `contextual_preamble` aos 3 renderers principais — `render_v2.py` (HTML), `render_docx_abnt.py` (Word), `render_latex.py` (TeX). Flags consistentes: `--contextual-preamble`, `--preamble-topic`, `--preamble-area`, `--preamble-language`, `--preamble-mock`. Falha graciosamente se módulo ausente ou fetch falha.

### Sprint 2 (P1 funcionalidade incompleta)

- **F5**: `screening_pipeline.py` integrado a `pipeline_finalize.py` como Etapa 6. Lê `screening_decisions.json` (real) ou aceita `--screening-demo` (todos kept). Registra execução em `manifest.yaml.screening_runs[]` (Decisão 22). Pipeline cresce de 5 para 6 etapas.
- **F6**: bug `grey_lit` no orquestrador. Antes: chamava sem `--provider`, capturando 1/7 da cobertura (apenas unesco). Agora: itera explicitamente os 7 providers (world_bank, unesco, oecd, ipea, inep, nist, who) gerando `results_grey_lit_<provider>.json` para cada um.
- **F7**: mock dos `PaywallAdapter` agora inclui `log_camada1` consistente com modo real. Schema unificado entre mock/KEY/PROXY/FALLBACK_MD para evitar surpresas de schema downstream.

### Sprint 3 (P2 limpeza)

- **F8**: 9 arquivos com `datetime.utcnow()` → `datetime.now(timezone.utc)` (deprecated em Python 3.12+). Imports de `timezone` adicionados onde necessário.
- **F9**: `import logging` não-usado removido de `_adapter_base.py`.
- **F10**: comentário enganoso em `wiley_tdm._proxy_search()` corrigido. Antes: "delega ao KEY mode (que sempre tem fallback Crossref)" (mas `return None`). Agora: "cascata cai em FALLBACK_MD; lista cruzada via Crossref".
- **F11**: padronização `lareferencia` → `la_referencia` (alinhar chave runner com nome do arquivo `search_la_referencia.py`). Atualizado em search_orchestrator, TIER_DATABASES, source no JSON output, e 2 testes legados.
- **F12**: DD-10 em `references/DECISIONS.md` agora declara honestamente que Camada 1 nativa só existe nos 16 adapters paywall; para os 45 legados, é via pós-processador do orquestrador. Chamada direta de adapter legado **não gera logs** — gap conhecido.
- **F13**: CHANGELOG v2.15.0 esclarece que "implementáveis" para CINAHL/PsycInfo/JSTOR full/Hein Online significa caminho técnico legal — chave individual não basta; exige credencial institucional EBSCO/JSTOR/HeinOnline ativa específica.

### Sprint 4 (P3 escopo maior — parcial)

- **F14**: integração screening + manifest (já completo em F5).
- **F15 (parcial)**: parser RSS real implementado para `search_la_referencia.py` (Decisão 25 — bases ibero-americanas obrigatórias). Sai do modo `_REAL_PARTIAL` (raw_size_bytes apenas) para parser efetivo via `xml.etree.ElementTree`. Schema normalizado: title/authors/year/venue/language/url/abstract_excerpt/is_oa. Normaliza idiomas Dublin Core (por→pt, spa→es, eng→en). Filtra por janela temporal local. Os outros 17 adapters em `_REAL_PARTIAL` permanecem como roadmap (lilacs, redalyc, scielo_preprints, e outros 14 — ficam para v2.20.0+).
- **F16**: testes de integração com `unittest.mock.patch` para `urllib.request.urlopen` validando schemas reais. Cobertura: parsing válido, XML malformado, items sem título, HTTPError, sem janela temporal, max_results truncamento.

### Estado dos contadores

- Decisões editoriais: 33 (inalterado).
- Decisões de design (DD): 12 (todas implementadas; DD-10 com asterisco honesto).
- Adapters de busca: 61.
- Módulos auxiliares: 3.
- TIER1_RUNNERS: 57.
- Áreas: 7.
- Pipeline_finalize: 6 etapas (era 5).
- **Testes: 266/266** (era 243; +16 v2.18.1 + 7 v2.19.0).

### Limitações operacionais declaradas

- Sandbox de desenvolvimento bloqueia Wikipedia (HTTP 403 universal mesmo com User-Agent compliant). F1 validado via mocks de `urllib`. Em produção com rede aberta + `IGNORANTIA_CONTACT_EMAIL` definido, comportamento esperado é correto pela documentação Wikimedia.
- F15 cobre apenas 1 dos 18 adapters em `_REAL_PARTIAL` (LA Referencia). Os outros 17 são gap declarado de roadmap.
- F4 integração testa flags + presença de menções, não testa renderização end-to-end de docx/tex (requer python-docx + TeX Live no ambiente).

### Pendente para v2.20.0+

- F15 resto: parsers reais para `lilacs`, `redalyc`, `scielo_preprints`, e outros 14 adapters em `_REAL_PARTIAL` (priorizar bases ibero-americanas obrigatórias por Decisão 25).
- Testes end-to-end de render_docx + render_latex com preâmbulo (requer dependências instaladas no CI).
- Reexecução do estudo de calibração RS-42 com cobertura premium completa (medir delta empírico vs versões anteriores).

### O significado da release

A v2.18.0 prometeu "fechamento da estratégia v2.11.1 — todas as 8 rodadas entregues". A auditoria v2.18.0 mostrou que entregue ≠ funcional: 4 funcionalidades P0 estavam quebradas em produção (Wikipedia 403, SKILL.md sem v2.15+, README alpha, módulos isolados) e 13 funcionalidades P1-P3 tinham gaps. A v2.19.0 corrige tudo isso com 23 fixes em 4 sprints, todos validados por regressão (266/266) e por testes específicos da auditoria. **A skill agora cumpre o que documenta.**

---

## [2.18.0] — 2026-05-04

**Release de fechamento da estratégia v2.11.1.** Consolida R7 (DD-10 logs detalhados em duas camadas) + R8 (DD-11 preâmbulo Wikipedia/Wikidata). Com esta release, todas as 8 rodadas planejadas em `IMPLEMENTATION_STRATEGY.md` estão entregues.

### R7 (v2.17.0) — Logs detalhados em duas camadas (DD-10)

**Estratégia escolhida**: em vez de modificar 45 adapters legados individualmente (alto risco, alto custo), implementamos **pós-processador** que enriquece automaticamente os JSONs gerados com logs Camada 1 estruturados. Adapters paywall (v2.12+) já têm logs nativos via `LocalFilter`; o pós-processador os preserva e complementa.

**Novos módulos**:

- `scripts/searches/_log_enrichment.py` — enriquece `results_<source>.json` com `logs_<source>.jsonl` em estrutura JSON Lines:
  - `fetched`: registros recuperados pelo adapter
  - `kept_after_local_filter`: passaram filtros locais (janela temporal, idioma, DOI)
  - `discarded_local`: descartados localmente, com razão técnica
  - `native_log_camada1_from_adapter`: preserva log nativo de PaywallAdapter
- `scripts/screening_pipeline.py` — Camada 2 do screening (PRISMA-2020 Fase 4):
  - 3 estágios sequenciais: `title` → `abstract` → `full_text`
  - Cada decisão registra `study_id`, `doi`, `decision`, `reason`, `reviewer`, `timestamp`
  - Saída: `screening_log.csv` (PRISMA-compatible) + `screening_counts.json`
  - Suporta reviewer types: `human`, `ai_single`, `ai_dual`, `ai_assisted_human`

**Integração ao orquestrador**: `_run_searches_list()` agora chama automaticamente `enrich_log_camada1()` após cada adapter executado com sucesso. Logs são gravados em `<output_dir>/logs/logs_<source>.jsonl`.

**Smoke real do orquestrador na área `multi`** gera 9 arquivos `logs_*.jsonl` automaticamente, incluindo o `native_log_camada1` para os adapters paywall que mostra a cascata `KEY_no_credential → PROXY_no_credential → FALLBACK_MD_generated`.

### R8 (v2.18.0) — Preâmbulo contextual Wikipedia/Wikidata (DD-11)

**Novo módulo**: `scripts/contextual_preamble.py` — gera seção **"O campo onde este artigo vive"** distinta da Introdução do paper (DD-11).

Este módulo **NÃO é adapter de busca**. É construtor de background contextual para audiência leiga, integrado a HTML/PPTX/Markdown na Fase 7 (síntese), antes do render final.

**Função**: apresentar o campo de pesquisa para audiência ampla — banca multidisciplinar, leitor não-especialista de white paper, doutorando explicando para a família. Distinto da Introdução, que aborda o **tema específico** da pesquisa.

**Conteúdo gerado** (3-5 parágrafos):
1. Disciplina-mãe e suas subdivisões relevantes
2. Marcos históricos e principais paradigmas no campo
3. Atores institucionais e teóricos relevantes
4. Por que este tema importa neste momento histórico

**Fontes**:
- Wikipedia EN/PT-BR/ES via REST API (`https://{lang}.wikipedia.org/api/rest_v1/page/summary/`)
- Wikidata via `wbsearchentities` action (`https://www.wikidata.org/w/api.php`)

**Citação ABNT NBR 10520** — toda afirmação tem referência clicável + data de acesso:
- `(WIKIPEDIA, "Termo", acesso em 2026-05-04)` com link para artigo
- `(WIKIDATA QXXXX, "label", acesso em 2026-05-04)` com link para entidade

**4 formatos de output**:
- HTML: `<section id="contextual-preamble">` antes de `<section id="introduction">`
- Markdown: bloco `## O campo onde este artigo vive` antes de `## 1. Introdução`
- JSON: serialização completa para integração programática
- PPTX slides: estrutura intermediária para `python-pptx` integrar (1 section_header + 2-3 content slides + 1 entities slide)

**Mapeamento área → disciplinas-mãe**:

| Área da skill | Disciplinas-mãe consultadas |
|---|---|
| saude | Medicina, Saúde pública, Health sciences |
| educacao | Educação, Pedagogia, Education |
| cs_se | Ciência da computação, Engenharia de software |
| ciencias_sociais | Ciências sociais, Sociologia |
| humanidades | Humanidades, Filosofia |
| business | Administração, Management |
| multi | Ciência interdisciplinar |

**Suporte multilíngue**: PT-BR (default), EN, ES. Título da seção traduzido apropriadamente:
- PT-BR: "O campo onde este artigo vive"
- EN: "The field where this article lives"
- ES: "El campo donde vive este artículo"

**Limitações honestas declaradas**:
- Wikipedia não é fonte primária; é acessório explicativo. Toda afirmação metodologicamente relevante ainda deve vir de literatura peer-reviewed na Introdução/Fundamentação.
- Conteúdo Wikipedia muda; data de acesso é obrigatória na citação.
- Para temas muito recentes (< 2 anos), Wikipedia pode não ter cobertura adequada; o módulo declara isso honestamente quando ocorre (`<p class="contextual-warning">`).

### Estado dos contadores

- **Decisões editoriais:** 33 (inalterado).
- **Decisões de design (DD):** 12 (todas implementadas).
- **Adapters de busca:** 61 (inalterado).
- **Módulos novos:** 3 (`_log_enrichment.py`, `screening_pipeline.py`, `contextual_preamble.py`).
- **TIER1_RUNNERS:** 57.
- **Áreas em TIER_DATABASES:** 7.
- **Testes:** **243/243** (era 222; +21 v2.18.0).

### O significado da release final

A trilha v2.8.0 → v2.18.0 está fechada. As 8 rodadas da estratégia v2.11.1 estão entregues:

| R | Versão | Conteúdo | Status |
|---|---|---|---|
| R1 | v2.11.1 | Registro de decisões | ✅ |
| R2 | v2.12.0 | Elsevier (Scopus, ScienceDirect, Embase) | ✅ |
| R3 | v2.13.0 | Springer/Wiley/IEEE/WoS | ✅ |
| R4 | v2.14.0 | APA/CINAHL/JSTOR/Sage | ✅ |
| R5 | v2.15.0 | ACM/SSRN/Hein/ProQuest | ✅ |
| R6 | v2.16.0 | Google Scholar via SerpApi | ✅ |
| R7 | v2.17.0 | Logs detalhados (Camada 1 + Camada 2) | ✅ |
| R8 | v2.18.0 | Wikipedia/Wikidata preâmbulo contextual | ✅ |

A skill agora tem:
1. **Cobertura premium completa**: 57 adapters cobrindo OA + paywall com cascata legal
2. **Honestidade declarativa em todos os níveis**: disclosure user-facing, fallback `.md` declarativo, logs estruturados em duas camadas, citações ABNT com data de acesso
3. **Integração com fontes não-bibliográficas para audiências leigas**: Wikipedia/Wikidata como preâmbulo distinto da Introdução
4. **Auditabilidade PRISMA-2020 completa**: screening em 3 estágios com logs CSV reviewer-by-reviewer, flow diagram com counts coerentes

A skill está **pronta para uso em SR submetidas a Q1 internacionais e bancas de doutorado brasileiras Stricto Sensu**, com cobertura declarativa que reviewers experientes esperam.

---

## [2.15.0] — 2026-05-04

**Release de adapters paywall com cascata legal**, consolidando R2 a R6 da estratégia v2.11.1. Implementa 16 adapters cobrindo as 14 bases pagas que reviewers Q1, banca de doutorado e consultores premium esperam ver citadas + Google Scholar via SerpApi. Cada adapter implementa cascata `KEY → PROXY → FALLBACK_MD → MOCK` (Decisão DD-8) que tenta mecanismos legais em ordem antes de cair em fallback declarativo `.md`.

### Os 16 adapters em 5 rodadas internas

**Template arquitetural** — `scripts/searches/_adapter_base.py`. Classe `PaywallAdapter` (abstrata) + `AdapterResult` + `FetchedItem` + `LocalFilter`. Cada adapter herda dela e sobrescreve apenas o que muda (endpoint, parser, schema do publisher). Cascata `_try_cascade()` orquestra: chave → proxy → fallback `.md`. Schema do `citations_to_obtain.md` inclui 4 opções de obtenção (Periódicos CAPES via CAFe, biblioteca institucional, contato com autor, COMUT).

**R2 — Elsevier (3 adapters)**:
- `search_scopus_full.py` — Elsevier Scopus API (`ELSEVIER_API_KEY`, gratuita p/ academic)
- `search_sciencedirect_full.py` — Elsevier ScienceDirect API (mesma chave Elsevier)
- `search_embase.py` — Elsevier Embase API (`ELSEVIER_EMBASE_KEY`, paga mesmo academicamente)

**R3 — Outros publishers grandes (4 adapters)**:
- `search_springer_full.py` — Springer Nature API (`SPRINGER_API_KEY`, **gratuita** com cadastro)
- `search_wiley_tdm.py` — descoberta via Crossref `member:311=Wiley` + TDM key
- `search_ieee_full.py` — IEEE Xplore API (`IEEE_API_KEY`)
- `search_wos_full.py` — Clarivate WoS Starter API (`CLARIVATE_API_KEY`, gratuita ~10k req/mês)

**R4 — APA/EBSCO/JSTOR/Sage (4 adapters)** — predominância de FALLBACK_MD honesta. **Esclarecimento (F13 da auditoria v2.18.1):** "implementáveis" para CINAHL, PsycInfo, JSTOR full e (em R5) Hein Online significa que existe caminho técnico legal — mas chave individual não basta; é necessária credencial institucional ativa EBSCO/JSTOR/HeinOnline específica. Para usuário individual sem afiliação institucional dessas plataformas, a cascata cai sempre em FALLBACK_MD (90%+ dos usuários). Documenta-se isso para evitar a expectativa otimista de que basta uma chave qualquer:
- `search_psycinfo_full.py` — APA PsycNET via EBSCOhost (declara honestamente que requer auth institucional)
- `search_cinahl_full.py` — EBSCO CINAHL (apenas via proxy institucional)
- `search_jstor_full.py` — JSTOR DfR (exige aprovação project-by-project)
- `search_sage_full.py` — descoberta via Crossref `member:179=Sage` + TDM negociado

**R5 — Sem API pública (4 adapters)** — todos com cascata mas predominância de fallback:
- `search_acm_full.py` — descoberta via Crossref `member:320=ACM` + login institucional para full-text
- `search_ssrn_full.py` — descoberta via OpenAlex source SSRN + download manual
- `search_hein_online.py` — apenas proxy institucional + FALLBACK_MD (jurídico)
- `search_proquest_full.py` — apenas proxy institucional + FALLBACK_MD

**R6 — Google Scholar via SerpApi (1 adapter)**:
- `search_google_scholar_serpapi.py` — único caminho legal para Google Scholar programático. SerpApi é serviço comercial pago (`SERPAPI_KEY`, ~$50-150/mês) que assume a parte legal/técnica do scraping. Sem chave, gera fallback `.md` declarativo.

### Reorganização TIER_DATABASES

Nova categoria **`tier2_paywall`** em cada área. Bases que estavam em `priority_0_routing` e `unimplementable` migraram para `tier2_paywall` quando a cascata legal é viável.

| Área | Tier 1 | Tier 2 | Tier 2 paywall (cascata) | Inviáveis |
|---|---|---|---|---|
| saude | 16 | 5 | **6** (scopus, wos, embase, cinahl, sciencedirect, GS) | 0 |
| educacao | 13 | 4 | **7** (+ psycinfo, sage, proquest, google_scholar) | 0 |
| cs_se | 11 | 3 | **8** (+ ieee, acm, springer, wiley) | 0 |
| ciencias_sociais | 14 | 4 | **6** (+ jstor, sage, ssrn) | 0 |
| humanidades | 12 | 3 | **6** (+ jstor_full, hein_online) | 0 |
| business | 10 | 4 | **7** (+ ssrn, sage, wiley, proquest) | 1 (ebsco_business_source) |
| multi | 11 | 4 | **3** | 0 |

Antes da v2.15.0, `priority_0_routing` listava bases pagas que **só** podiam ser acessadas via Tier 0 routing (Unpaywall+OAB+CORE+CAPES) e exportação manual. Agora, as bases com cascata viável são executadas automaticamente pelo orquestrador (com a credencial do usuário) e geram fallback `.md` declarativo se sem credencial. Mantém-se a honestidade declarativa (Decisão 24).

### Disclosure user-facing v2.15.0

Mensagem pré-busca agora mostra 4 categorias:
1. **Tier 1** (OA gratuito, full-text)
2. **Tier 2** (metadados livres)
3. **Tier 2 paywall** (cascata `KEY → PROXY → FALLBACK_MD`, com explicação)
4. **Inviáveis automaticamente** (bases sem caminho legal, raras agora)
5. **priority_0** (vazio na maioria das áreas)

Saúde modo SR estrito agora declara **27 bases buscadas** (era 21 na v2.11.0): 16 Tier 1 + 5 Tier 2 + 6 Tier 2 paywall. Sem skips silenciosos; cada base pega tem a declaração honesta de qual mecanismo será tentado.

### Novas funções no orquestrador

- `run_tier2_paywall_searches(area, query, year_start, year_end, output_dir)` — executa adapters paywall com cascata. Cada adapter recebe `--output-dir` para gerar fallback `.md` se necessário. **Chamada automaticamente** pelo `main()` após `run_tier1_searches`.
- `_run_searches_list(...)` — helper genérico que substitui implementação duplicada.

### Decisões formalizadas (recapitulação para o release)

A v2.15.0 implementa decisões já registradas em v2.11.1:
- **DD-6** ToS é restrição absoluta (ResearchGate, Academia.edu permanecem WON'T)
- **DD-7** Revisão da DD-5: 14 publishers tornam-se implementáveis sob nova premissa "credencial do usuário"
- **DD-8** Cascata KEY → PROXY → FALLBACK_MD obrigatória para bases pagas
- **DD-9** Cobertura ResearchGate/Academia.edu via Unpaywall + CORE + OpenAlex (já implementados)

### Estado dos contadores

- **Decisões editoriais:** 33 (inalterado).
- **Decisões de design (DD):** 12.
- **Adapters de busca:** 61 (era 45; +16 paywall).
- **Adapter classificador de venue:** 1 (jane).
- **TIER1_RUNNERS:** **57** (era 41; +16 paywall).
- **Áreas em TIER_DATABASES:** 7.
- **Cobertura média Tier 1+2+paywall por área:** ~22 bases (era ~16).
- **Bases declaradas inviáveis:** 1 (apenas EBSCO Business Source; era 5).
- **Testes:** 222/222 (era 189; +33 v2.15.0).

### Limitações honestas declaradas

- **Maioria das chaves não é gratuita** para uso individual. Chave de academic acesso é gratuita para: Springer Nature, Crossref (já existia), Unpaywall (já existia), Clarivate WoS Starter (com limites). Chave acadêmica institucional (não-gratuita ao indivíduo) para: Elsevier (Scopus, ScienceDirect, Embase), IEEE Xplore. Sem chave gratuita pública: Wiley TDM (acordo institucional), APA, EBSCO, JSTOR DfR, Sage TDM.
- **Acesso via proxy ainda é HTML scraping** dependendo do publisher; parser detalhado declarado como TODO em `_proxy_search()` da maioria dos adapters. Para SR rigorosa, recomenda-se exportar manualmente do publisher institucional em RIS/CSV.
- **SerpApi é pago.** Para Google Scholar sem orçamento, a alternativa é cobertura via CORE+OpenAlex+Crossref (já implementados em Tier 1/2).
- **DD-10 (logs detalhados em todos os adapters)** ainda não foi totalmente aplicada aos 45 adapters legados. v2.17.0 cobrirá isso.
- **DD-11 (Wikipedia/Wikidata como preâmbulo)** ainda pendente. v2.18.0 entregará.

### O significado da release

A v2.11.0 atingiu cobertura "premium" via OA. A v2.15.0 atinge cobertura "**premium completa**" via legal: agora a skill **acessa** as 14 bases pagas que reviewers Q1 esperam, com a credencial do usuário, em vez de declará-las como gap inacessível. Para usuário sem credencial, **gera o documento estruturado** que ele precisa para baixar manualmente via CAFe — em vez de simplesmente declarar "não busquei". A diferença é decisiva: SR submetida a Q1 com `citations_to_obtain_scopus.md` anexado tem evidência declarativa de tentativa que reviewer aceita; SR sem isso é rejeitada.

A trilha v2.8.0 → v2.15.0 consolida três fases: (a) skill operacional (v2.8-v2.10), (b) skill honesta (v2.10.2-v2.11), (c) skill premium completa (v2.11.0-v2.15). Próximos passos: R7 (logs detalhados em todos os adapters legados) e R8 (Wikipedia/Wikidata preâmbulo contextual).

---

## [2.11.1] — 2026-05-03

Patch de **registro de decisões** preparatório para a expansão paywall (v2.12-v2.18). Sem código novo de adapter; foco em governança e arquitetura.

### Adicionado

- **`references/DECISIONS.md`** — registro central, persistente e canônico de decisões editoriais e de design. Decisões DD-1 a DD-12 formalizadas. DD-5 (WON'T da v2.11.0 para 17 bases/plataformas) marcada como parcialmente revogada por DD-7 (revisão sob nova premissa: "acesso via mecanismo legal de propriedade do usuário").
- **`references/WONT_IMPLEMENT.md`** — registro do que NÃO será implementado e por quê. ResearchGate e Academia.edu confirmadas como WON'T por DD-6 ("Conflito com ToS de plataforma é inaceitável"). Sci-Hub e LibGen confirmadas como WON'T por política de copyright.
- **`references/IMPLEMENTATION_STRATEGY.md`** — estratégia operacional das rodadas v2.12-v2.18. 8 rodadas planejadas com critérios de pausa explícitos.

### Decisões formalizadas (DD-6 a DD-12)

- **DD-6**: ToS de plataforma é restrição absoluta. Nenhum adapter da skill acessa plataforma em violação dos seus Termos de Serviço.
- **DD-7**: Revisão da DD-5 sob nova premissa. 14 publishers paywall + Google Scholar tornam-se implementáveis; ResearchGate + Academia.edu permanecem WON'T.
- **DD-8**: Cascata de mecanismos legais para acesso a base paga: `KEY → PROXY → FALLBACK_MD → MOCK`. O adapter NÃO pula direto para fallback; tenta todos os mecanismos legais primeiro.
- **DD-9**: ResearchGate/Academia.edu cobertos funcionalmente por Unpaywall + CORE + OpenAlex (cobertura agregada superior, com identificadores estáveis).
- **DD-10**: Logs em duas camadas (adapter: fetched/kept_after_local/discarded_local; screening pipeline: discarded_by_title/discarded_by_abstract/discarded_by_full_text).
- **DD-11**: Wikipedia/Wikidata como preâmbulo contextual em `scripts/contextual_preamble.py`, gerando seção "O campo onde este artigo vive" — distinta da Introdução.
- **DD-12**: Estratégia das 8 rodadas registrada em `IMPLEMENTATION_STRATEGY.md`.

### Modificado

- `SKILL.md` agora aponta explicitamente para os 3 arquivos de governança (`DECISIONS.md`, `WONT_IMPLEMENT.md`, `IMPLEMENTATION_STRATEGY.md`).

### Estado dos contadores (inalterado em código)

- Decisões editoriais: 33.
- Decisões de design (DD): 12 formalizadas.
- Adapters de busca: 45.
- TIER1_RUNNERS: 41.
- Testes: 189/189.

### O significado da release

A v2.11.1 não adiciona código de adapter; adiciona **memória institucional**. A skill agora tem registro central de decisões persistido em arquivo, permitindo que rodadas futuras (v2.12-v2.18) refiram-se a decisões anteriores sem necessidade de reconstrução de premissas. Esta é precondição para implementar 14 adapters paywall sem violar coerência arquitetural.

---

## [2.11.0] — 2026-05-03

**Release de ascensão a "ghostwriter premium".** Análise MoSCoW dos adapters esperados por reviewers Q1, banca de doutorado, consultores de órgãos públicos e departamentos jurídicos identificou 19 adapters para implementar — 5 MUSTs, 6 SHOULDs, 8 COULDs (incluindo 1 utilitário Fase 8 fora do TIER1_RUNNERS).

A diferença entre adapter atual e adapter premium não está em quantidade; está em **legibilidade reviewer-facing**. A v2.10.2 declarava "buscamos em 11 bases Tier 1". A v2.11.0 declara, na área `saude` modo SR estrito: **"PubMed Central, Europe PMC, medRxiv, bioRxiv, Cochrane Central, ClinicalTrials.gov, SciELO, SciELO Preprints, LILACS, LA Referencia, Redalyc, BDTD, Catálogo CAPES, DOAJ, CORE, OAPEN — 16 bases Tier 1 OA + 5 Tier 2 (PubMed, Crossref, OpenAlex, Semantic Scholar, Dimensions com FWCI/Altmetric) — cobertura PRISMA-2020 + Cochrane Handbook + EQUATOR endorsed."**

Esse texto é a primeira coisa que reviewer e banca leem em Methods. Não é diferença marginal técnica; é diferença de classe de produto.

### Os 19 adapters em 4 rodadas

**Rodada 1 — MUSTs de saúde (3 adapters):** sem isso, reviewer Q1 cobra "completeness check" PRISMA-2020.

| Adapter | API | Tier |
|---|---|---|
| `search_pubmed.py` | NCBI E-utilities (db=pubmed) | 2 (~36M registros) |
| `search_cochrane_central.py` | Web parsing parcial; recomenda combinar com PubMed pt:RCT | 1 (RCTs) |
| `search_clinicaltrials_gov.py` | CT.gov v2 API (REST estruturada) | 1 (registro NIH) |

**Rodada 2 — MUSTs multi-disciplinar (2 adapters):**

| Adapter | API | Diferencial |
|---|---|---|
| `search_oapen.py` | OAPEN DSpace REST (`/rest/search`) | Livros OA peer-reviewed (~22k) — humanidades é livro, não artigo |
| `search_dimensions.py` | Dimensions DSL (requer `DIMENSIONS_API_KEY`) | FWCI, Altmetric Score, Relative Citation Ratio |

**Rodada 3 — SHOULDs por área (6 adapters):**

| Adapter | Cobertura |
|---|---|
| `search_jstor_oa.py` | JSTOR Open Content — humanidades + ciências sociais |
| `search_scielo_preprints.py` | medRxiv lusófono (~6k preprints LATAM) |
| `search_dialnet.py` | Espanha + LatAm humanidades/direito (~7M refs) |
| `search_pepsic.py` | Psicologia BR/LATAM (BVS-Psi) |
| `search_catalogo_teses_capes.py` | Catálogo oficial CAPES — banca BR cobra junto com BDTD |
| `search_engineering_village.py` | Compendex OA subset via OpenAlex enriquecido |

**Rodada 4 — COULDs (8 adapters):**

| Adapter | Caso de uso |
|---|---|
| `search_grey_lit.py` | Multi-provider (UNESCO, OECD, World Bank, IPEA, INEP, NIST, WHO) |
| `search_philarchive.py` | Filosofia OA (PhilPapers JSON) |
| `search_spell.py` | Business research BR (admin/contábil) |
| `search_redib.py` | Iberoamericana complementar com bibliométricos |
| `search_e_lis.py` | Biblioteconomia / CI |
| `search_proquest_oa.py` | ProQuest PQDT Open subset |
| `search_dabi.py` | Educação nórdica (Tidsskrift OJS) |
| `search_jane.py` | Classificador de venue (utilitário Fase 8) — **NÃO entra em TIER1_RUNNERS** |

### Reorganização do TIER_DATABASES

**2 áreas novas** criadas para refletir cobertura premium específica:

- **`humanidades`** (filosofia, literatura, história, artes, religião): tier1 com OAPEN + JSTOR OA + PhilArchive + Dialnet + E-LIS. HeinOnline declarado em `unimplementable[]` com razão técnica.
- **`business`** (admin, contabilidade, gestão pública): tier1 com Spell + OAPEN + REDIB. EBSCO Business Source declarado inviável.

**Áreas existentes expandidas:**

| Área | v2.10.2 (Tier 1+2) | v2.11.0 (Tier 1+2) | Δ |
|---|---|---|---|
| saude | 11+3 = 14 | 16+5 = 21 | +7 |
| educacao | 9+3 = 12 | 13+4 = 17 | +5 |
| cs_se | 9+2 = 11 | 11+3 = 14 | +3 |
| ciencias_sociais | 10+3 = 13 | 14+4 = 18 | +5 |
| humanidades (NOVA) | — | 12+3 = 15 | NOVA |
| business (NOVA) | — | 10+4 = 14 | NOVA |
| multi | 9+3 = 12 | 11+4 = 15 | +3 |

### O que muda concretamente para o usuário

Antes (v2.10.2), área `saude` modo SR estrito buscava 14 bases. Após v2.11.0:
- **Saúde** ganha o **tripé canônico Cochrane Handbook**: Cochrane CENTRAL + ClinicalTrials.gov + PubMed completo. SciELO Preprints e Catálogo CAPES adicionados. OAPEN para metodologia.
- **Educação** ganha cobertura ibérica (Dialnet) + nórdica (DABI) + livros OA (OAPEN).
- **Ciências sociais** ganham JSTOR OA + filosofia (overlap) + livros OA + Dialnet.
- **CS/SE** ganha Engineering Village (Compendex OA subset) + livros OA.
- **Humanidades** (área nova) tem JSTOR OA + OAPEN + PhilArchive como tier1 — porque livro é unidade primária.
- **Business** (área nova) tem Spell + OAPEN + REDIB.
- **Multi** ganha grey_lit (multi-provider) para realist reviews + white papers.

Indicadores bibliométricos (FWCI, Altmetric Score, Relative Citation Ratio) via Dimensions agora estão em Tier 2 de **6 áreas**. Reviewers Q1 que pedem "discutir impacto e trending" agora têm o adapter para gerar a evidência.

### Bug fixes / detalhes técnicos

- `search_jane.py` é classificador de venue com `source_tier = "venue_classifier"` (não "1" nem "2"), explicitando que é utilitário Fase 8 e não busca de literatura.
- `search_engineering_village.py` é wrapper sobre OpenAlex com filtros de engenharia (concept IDs); declara honestamente que Compendex direto requer institucional.
- `search_grey_lit.py` é multi-provider via flag `--provider`; World Bank e WHO usam DSpace REST estruturado, outros providers ainda têm parser detalhado como TODO (declaração honesta).
- Adapters com chave de API opcional (`search_dialnet.py`, `search_redib.py`, `search_dimensions.py`) declaram explicitamente quando não há chave em vez de buscar parcialmente.

### Testes

189/189 passam em ~11.3s:
- 155 da regressão acumulada v2.0–v2.10.2
- 34 novos da v2.11.0:
  - 19 testes de adapters individuais em modo mock (5 MUSTs + 6 SHOULDs + 7 buscáveis dos COULDs + 1 grey_lit unesco + 1 grey_lit world_bank + 1 grey_lit who + 1 jane classifier)
  - 7 testes da reorganização TIER_DATABASES (humanidades + business + tripé saúde + dimensions em 6 áreas + engineering em cs_se + grey_lit em multi + total runners 41)
  - 3 testes da disclosure honesta para áreas novas (humanidades, business, saúde com tripé)
  - 5 testes estruturais (todos os 18 novos em TIER1_RUNNERS, jane fora, runners apontam para arquivos reais)

### Estado dos contadores

- **Decisões editoriais formalizadas:** 33 (inalterado).
- **Adapters de busca:** 45 (era 27; +18 buscáveis em release).
- **Adapter classificador de venue:** 1 (jane, novo, não conta como busca).
- **Adapters em `TIER1_RUNNERS`:** 41 (era 23 — quase dobrou).
- **Áreas em `TIER_DATABASES`:** 7 (era 5; +humanidades, +business).
- **Cobertura Tier 1+2 média por área:** ~16 bases (era ~13).
- **Bases declaradas inviáveis:** 5 (acm_full, ieee_full, ssrn, hein_online, ebsco_business_source).
- **Testes:** 189/189.

### O significado da release

A v2.10.2 fechou a coerência declarativa (1:1 declarado vs implementado). A v2.11.0 fecha a **adequação à expectativa do cliente premium**. Quando um doutorando submete a tese para banca, quando um pesquisador submete a Q1, quando um consultor entrega relatório a órgão público, ele agora pode **citar, na seção Methods, exatamente o que reviewers e bancas esperam ver citado**. Sem promessas vazias, sem skips silenciosos, e agora também sem gaps de cobertura que reviewers experientes detectam à primeira leitura.

A trilha v2.8.0 → v2.9.0 → v2.10.0 → v2.10.1 → v2.10.2 → v2.11.0 está fechada com ascensão completa: skill operacional → skill honesta → skill premium. Próximos passos naturais seriam: (a) reexecutar RS-42 com cobertura premium para medir delta empírico de qualidade; (b) implementar parsers detalhados para os adapters declarados como `_REAL_PARTIAL` (catálogo CAPES, JSTOR labs, Dialnet HTML, etc.) — que funcionam no mock mas têm modo real best-effort; (c) integrar `search_jane.py` à Fase 8 do pipeline (sugestão de 3-5 venues).

---

## [2.10.2] — 2026-05-03

Patch de **completude de adapters + honestidade declarativa**. A v2.10.1 fechou a coerência operacional do pipeline; auditoria sistemática revelou ainda 12 bases declaradas em `TIER_DATABASES` Tier 1 sem runner correspondente (mais 5 em Tier 2). Esta release as enfrenta sistematicamente em 7 rodadas técnicas.

### 10 adapters novos em 6 rodadas

```
scripts/searches/
├── search_pubmed_central.py    # NCBI E-utilities (esearch + esummary)        [R1]
├── search_europepmc.py         # Europe PMC REST API                          [R1]
├── search_biorxiv.py           # api.biorxiv.org (genérico para bioRxiv)      [R2]
├── search_medrxiv.py           # wrapper delega a search_biorxiv com server    [R2]
├── search_eric.py              # api.ies.ed.gov/eric (consolida eric_oa+full) [R3]
├── search_osf_preprints.py     # api.osf.io/v2/preprints (multi-provider)     [R4]
├── search_edarxiv.py           # wrapper delega a OSF com provider=edarxiv    [R4]
├── search_zenodo.py            # zenodo.org/api/records                       [R4]
├── search_hal.py               # api.archives-ouvertes.fr (Solr)              [R5]
└── search_openalex.py          # api.openalex.org/works (clareza arquitetural)[R6]
```

### Reorganização honesta de TIER_DATABASES (R7)

Distinção em **3 categorias claras**, refletindo o estado real:

**1. Implementadas** — bases com runner registrado em `TIER1_RUNNERS`. **Rodam de fato**.

**2. Inviáveis automaticamente** (`unimplementable[]`) — bases sem API pública. **Declaradas como gap honestamente** em vez de listadas em Tier 1/2 e silenciosamente puladas.

| Área | Base | Razão |
|---|---|---|
| cs_se | acm_full | ACM Digital Library não tem API pública gratuita |
| cs_se | ieee_full | IEEE Xplore não tem API gratuita; subset OA exige autenticação |
| ciencias_sociais | ssrn | SSRN não tem API pública; scraping é ToS-questionável |

**3. priority_0_routing** — bases pagas tentadas via Tier 0 (Unpaywall + OAB + CORE + Periódicos CAPES) + gap_report.md.

#### Redundâncias declarativas removidas

| Antes (v2.10.1) | Por quê removido |
|---|---|
| `openalex_oa` (Tier 1) | Cobertura via `search_openalex.py` (com flag default `oa_only=True`) |
| `crossref_oa_filter` (Tier 1) | Cobertura via `search_crossref.py` com filter Lucene |
| `pubmed_full` (Tier 2) | Cobertura via `search_pubmed_central.py` (PMC inclui o subset OA do PubMed) |
| `eric_full` (Tier 2) | Cobertura via `search_eric.py --include-non-oa` |

Inflação declarativa anterior: 23 bases distintas em Tier 1 e 7 em Tier 2 (somando todas as áreas), mas só 13 com runner. Após v2.10.2: 23 com runner + 3 declaradas inviáveis = honestidade 1:1 com o que roda.

### Disclosure user-facing reescrita

Antes (v2.10.1):
```
Tier 1 (OA gratuito, full-text): 11 bases — pubmed_central, europepmc, ...
[Tier 1] Buscando...
  [skip] pubmed_central — sem runner implementado
  [skip] europepmc — sem runner implementado
  ...
```
A disclosure **mentia**: declarava 11 bases buscadas, executava 7.

Depois (v2.10.2):
```
BUSCAS QUE VOU EXECUTAR AGORA:
  Tier 1 (OA gratuito, full-text) — 11 bases:
    pubmed_central, europepmc, medrxiv, biorxiv, scielo, lilacs, lareferencia,
    redalyc, bdtd, doaj, core
  Tier 2 (metadados livres) — 3 bases:
    crossref, openalex, semantic_scholar

BASES INVIÁVEIS AUTOMATICAMENTE — 2:
  • acm_full — ACM Digital Library não tem API pública gratuita
  • ieee_full — IEEE Xplore não tem API gratuita; subset OA exige autenticação
  Não buscadas; declaradas como gap honestamente.

BASES priority_0 (alta relevância, paywall) — 4:
  scopus, wos, embase, cinahl_full
  Tentativa de acesso em ordem: Unpaywall → OAB → CORE → Periódicos CAPES.
```

### Validação operacional end-to-end

Smoke real do orquestrador em área `saude`, modo `rapid_review`:

| | v2.10.1 | v2.10.2 |
|---|---|---|
| Bases declaradas em Tier 1 | 11 | 11 |
| Bases efetivamente chamadas (runs) | 7 | **11** |
| Bases puladas com `[skip] sem runner` | 4 | **0** |
| Arquivos de resultado gerados | 7 | **11** |

PubMed Central, Europe PMC, medRxiv, bioRxiv agora **rodam** (antes: silenciosamente puladas).

### Bug fix descoberto durante validação

`search_biorxiv.py:138` comparava `next_total` (string vinda da API JSON) com `int`, causando `TypeError: '>=' not supported between instances of 'int' and 'str'`. Conserto com `int(msg.get("total", 0))` envolvido em try/except.

### Testes

155/155 passam em ~9.8s:
- 134 da regressão acumulada v2.0–v2.10.1
- 21 novos da v2.10.2:
  - 12 testes de adapters individuais em modo mock (cobre os 10 adapters + 2 variantes eric/openalex `--include-non-oa`)
  - 5 testes de reorganização TIER_DATABASES (sem redundâncias, categoria unimplementable, runners apontam para arquivos reais, todos os 23 registrados)
  - 4 testes da disclosure (3 categorias, lista inviáveis em cs_se, sem silent skips, priority_0 declarado)

### Adapters em modo real — limitações declaradas

- **OSF Preprints**: autores não vêm inline na primeira chamada da API; resultados retornam `authors=[]`. Resolução completa exigiria 2ª chamada por item; deixado como TODO.
- **bioRxiv/medRxiv**: API não tem busca textual nativa; filtro `query in title|abstract` aplicado localmente. Não é busca booleana plena. Para query textual robusta sobre preprints biomédicos, **EuropePMC indexa ambos**.
- **HAL**: cobertura europeia francófona; resultados com idioma `fr` predominantes.
- **OpenAlex**: adapter dedicado documenta cobertura sobreposta com `crossref` e `semantic_scholar`. Recomendado uso combinado com deduplicação por DOI.

### Estado dos contadores

- **Decisões editoriais formalizadas:** 33 (inalterado).
- **Adapters de busca:** 27 (era 17; +10 nesta release).
- **Adapters em `TIER1_RUNNERS`:** 23 (era 13).
- **Cobertura declarada vs implementada:** 1:1 (antes: 23 declaradas, 13 implementadas).
- **Bases declaradas como inviáveis:** 3 (acm_full, ieee_full, ssrn) — antes: silenciosamente listadas como Tier 2.
- **Testes:** 155/155.

### O que muda para o usuário

Quando rodar v2.10.2 em uma área de saúde, agora consulta efetivamente: **PubMed Central, Europe PMC, medRxiv, bioRxiv, SciELO, LILACS, LA Referencia, Redalyc, BDTD, DOAJ, CORE** — 11 bases reais. Educação ganha **ERIC + edArxiv**. Multi ganha **OSF Preprints + Zenodo**. CS/SE ganha **HAL + OpenAlex** (e declara honestamente que ACM full e IEEE full são inviáveis sem credenciais).

A v2.10.2 fecha a dívida de coerência declarativa: o que aparece na disclosure é o que roda; o que não roda é declarado como gap com razão técnica. Sem promessas vazias.

---

## [2.10.1] — 2026-05-03

Patch de **coerência operacional**. A trilha v2.8.0 → v2.9.0 → v2.10.0 fechou o ciclo de resposta à auditoria do RS-42 v1.0.0 entregando 16 decisões editoriais e 12 módulos novos. Auditoria sistemática da v2.10.0 revelou que **os módulos foram criados mas não integrados ao pipeline operacional** — havia dívida arquitetural acumulada. Esta release não acrescenta decisões editoriais, mas conserta a integração para que o que foi declarado obrigatório efetivamente rode.

### Sem nova decisão editorial; correções operacionais

#### CRIT-1 — TIER1_RUNNERS expandido (8 adapters faltando)

`scripts/searches/search_orchestrator.py` mantinha apenas 5 adapters em `TIER1_RUNNERS` mesmo após v2.9.0 declarar bases ibero-americanas obrigatórias. Em runtime, 9 de 11 bases listadas em `TIER_DATABASES["saude"]["tier1"]` eram silenciosamente puladas com `[skip] ... sem runner implementado`.

**Antes (v2.10.0):** TIER1_RUNNERS = {arxiv, scielo, dblp, crossref, semantic_scholar} — 5 adapters.

**Depois (v2.10.1):** TIER1_RUNNERS = {arxiv, scielo, dblp, crossref, semantic_scholar, **lareferencia, redalyc, clacso, bdtd, scioteca, doaj, lilacs, core**} — 13 adapters.

Periódicos CAPES é intencionalmente excluído do dict porque não roda automaticamente — é gateway com instruções acionáveis (Decisão 24).

#### CRIT-2 — `search_scielo.py` quebrava em runtime

Falhava com `urllib.error.HTTPError: 403` propagando exception até crashar o pipeline. Corrigido com try/except gracioso e adicionada flag `--mock` (consistente com adapters da v2.9.0).

#### CRIT-3 — Path absoluto hardcoded em `render_v2.py:807`

Referência a `/home/claude/ignorantia/assets/templates/manuscript-template-v2.html` (path absoluto não-portável apontando para arquivo inexistente). Substituído por busca relativa ao script + fallback para template existente.

#### CRIT-4 — Adapters DOAJ e LILACS criados

`TIER_DATABASES` listava `doaj` em "multi" e `lilacs` em "saude" como obrigatórios desde v2.9.0, mas os arquivos não existiam. Adicionados:

```
scripts/searches/
├── search_doaj.py    # DOAJ — ~20k revistas peer-reviewed OA, todas as áreas
└── search_lilacs.py  # LILACS/BVS — ~900k registros saúde Latam/Caribe (BIREME)
```

#### CRIT-5 — `pipeline_finalize.py` (comando único para os 5 outputs)

Antes da v2.10.1, gerar o pacote final exigia 5 comandos separados. Novo `scripts/pipeline_finalize.py` encadeia em uma execução:

```
[1/5] cross_tabulation     → cross_tab.md, cross_tab.html, cross_tab_prose.txt
[2/5] format_abnt          → references_abnt.md (se references_canonical.json fornecido)
[3/5] render_html_chunks   → manuscript.html (com checkpoint em _chunks_intermediate/)
[4/5] render_docx_abnt     → manuscript.docx (NBR 14724:2011)
[5/5] render_latex         → manuscript.tex + manuscript.pdf
```

Princípio aplicado: operação legal + resolve problema = default, não opção (princípio v2.6.1). Todos os 5 outputs rodam por padrão; flags `--skip-*` para quem precisa pular individualmente. Falha em uma etapa não interrompe as demais — `pipeline_summary.json` consolida resultado.

**Uso típico:**
```bash
python3 scripts/pipeline_finalize.py \
    --output-dir search_results/ \
    --title "Letramento digital de idosos: scoping review" \
    --version 1.0.0 \
    --cross-tab-x model --cross-tab-y task
```

Smoke test real: PDF compilado com sucesso (31KB) em ambiente TeX Live 2024.

#### IMP-1 — Vocabulário "Tier 3" expurgado das mensagens user-facing

Decisão 24 (v2.9.0) renomeou `tier3` → `priority_0_routing` apenas nos dados; mensagens em prints/help/disclosure continuavam dizendo "Tier 3". Corrigido:

- `build_user_disclosure_pre`: agora lê `priority_0_routing` e fala "Bases de alta relevância roteadas via Tier 0".
- `MODE_TIER_POLICY`: chave `tier3_via_user_only` renomeada para `priority_0_via_tier0_routing`. Alias retro-compat mantido até v2.11.0.
- 7 strings user-facing corrigidas em `search_orchestrator.py` (linhas 8, 250, 257, 349, 397, 402, 412, 575).

#### IMP-2 + IMP-3 — Decisões 21 e 22 implementadas em código

Documentadas desde v2.8.0 e v2.9.0 mas sem implementação técnica. Novo módulo `scripts/manifest_helpers.py`:

- `record_phase4_consent(manifest, n_excluded_title, n_excluded_abstract)` — grava `phase4_exclusions_review: implicit_consent` (Decisão 21).
- `record_search_run(manifest, query, area, year_start, year_end)` — grava timestamp + hash da query em `search_runs[]` (Decisão 22).
- `needs_rerun(manifest, query, area, ..., bumping_version)` — detecta automaticamente quando re-execução é necessária.

Orquestrador agora invoca `record_search_run` automaticamente após Tier 1, gravando em `<output-dir>/reproducibility_manifest.yaml`.

#### IMP-5 — Rubrica de qualidade alinhada com Decisão 23

D1 antiga: `0.2 pts | Snowballing executado e documentado` + bonus `+0.1 | Snowballing forward + backward executado`. Inconsistente com Decisão 23 (snowballing obrigatório desde v2.9.0).

Corrigido: critério "snowballing executado" removido de D1 (era 0.2 pts); bonus "forward + backward" removido. Os 0.2 pts foram redistribuídos para o critério de bases consultadas em D1 (de 0.3 → 0.5), refletindo a expansão obrigatória do Tier 1 com bases ibero-americanas (Decisão 25). Tabela "Critérios removidos" atualizada.

### Validação operacional end-to-end

Smoke real do orquestrador com a v2.10.1 produziu:
- 7 adapters ibero-americanos/multilíngue **chamados** (antes: 0).
- Vocabulário "Tier 3" **ausente** da disclosure (antes: presente).
- `reproducibility_manifest.yaml` gravado com `search_runs[]` automático (antes: ausente).

Smoke real do `pipeline_finalize.py`:
- 4 etapas ok + 1 pulada legítima (sem references_canonical.json).
- Artefatos: cross_tab.md, manuscript.html (1.4KB), manuscript.docx (37.8KB), manuscript.tex (1.7KB), **manuscript.pdf (31.6KB compilado com sucesso)**.

### Testes

134/134 passam em ~6.5s:
- 115 da regressão acumulada v2.0–v2.10.0
- 19 novos da v2.10.1:
  - 3 para CRIT-1 (TIER1_RUNNERS completo, exclusão correta de Periódicos CAPES, scripts existem)
  - 1 para CRIT-2 (search_scielo `--mock`)
  - 1 para CRIT-3 (sem path absoluto)
  - 2 para CRIT-4 (DOAJ e LILACS adapters)
  - 2 para IMP-1 (vocabulário priority_0; alias retro-compat)
  - 5 para IMP-2 + IMP-3 (record_phase4_consent, save/load roundtrip, record_search_run, needs_rerun em 3 cenários)
  - 4 para CRIT-5 (pipeline_finalize: roda tudo, respeita skips, falha graciosa, summary bem-formado)
  - 1 para POL-4 (disclaimer da rubrica limpo)

### Honestidade — limitações remanescentes

1. **Adapters PubMed Central, europepmc, medrxiv, biorxiv** — listados em `TIER_DATABASES["saude"]["tier1"]` mas sem adapter dedicado. Continuam emitindo `[skip] ... sem runner implementado (use Tier 2 fallback)`. v2.11+.
2. **Parsers detalhados** dos 6 adapters ibero-americanos em modo real continuam TODO; modo mock funciona end-to-end.
3. **Persona não é injetada em prompt** — Decisão 20 documenta a voz mas não há mecanismo de injeção mecânica. Depende do modelo ler o SKILL.md como contexto. Roadmap v2.11+.

### Estado dos contadores

- **Decisões editoriais formalizadas:** 33 (inalterado).
- **Adapters de busca:** 17 (era 15; +2 DOAJ e LILACS).
- **Módulos Python totais nos scripts:** 30+.
- **Testes:** 134/134.
- **Comando único para output final:** ✓ `pipeline_finalize.py`.

---

## [2.10.0] — 2026-05-03

Release de **outputs** — terceira e última de três releases respondendo à auditoria do RS-42 v1.0.0. Implementa as três decisões reservadas/pendentes da v2.8.0–v2.9.0: render HTML em chunks (Decisão 18), `.docx` ABNT (Decisão 31), `.tex`/`.pdf` (Decisão 32). Adiciona snowballing forward via OpenAlex como complemento ao backward (já implementado na v2.9.0).

### Adicionado — 4 módulos Python novos

```
scripts/
├── render_chunks.py             # Render HTML incremental (Decisão 18)
├── render_docx_abnt.py          # .docx no padrão ABNT NBR 14724/6023/10520 (Decisão 31)
└── render_latex.py              # .tex + compile para .pdf (Decisão 32)

scripts/searches/
└── snowballing_forward.py       # Citações posteriores via OpenAlex (Wohlin 2014 §2.2)
```

### Decisão 18 — render_chunks (HTML em append)

A renderização anterior fazia uma única passada com substituição de placeholders. Falha em qualquer seção invalidava todo o trabalho. A v2.10.0 implementa renderização incremental:

- Cada seção (§00, §01, ..., §N) é renderizada como chunk independente e anexada ao arquivo final.
- Cada chunk é gravado em arquivo intermediário (`chunk-NN.html`) para checkpoint/recovery.
- Falha em uma seção não invalida as anteriores. Usuário retoma com `--resume-from-chunk N`.
- Smoke test mecânico valida que o HTML incremental também não vaza marca do skill (Decisão 19).

### Decisão 31 — render_docx_abnt (.docx no padrão ABNT)

`.docx` ABNT é parte obrigatória do pacote final em pt-BR. Implementação com `python-docx`:

- Margens A4 3/3/2/2 cm (NBR 14724:2011 §5.1).
- Times New Roman 12pt corpo; 10pt citações longas e notas (§5.2).
- Espaçamento 1,5 corpo; simples em citações, notas, referências (§5.3).
- Recuo 1,25 cm parágrafos.
- Citações longas: recuo 4cm + fonte 10pt + espaçamento simples + sem aspas (NBR 10520:2023).
- Numeração de página no canto superior direito.
- Referências em ordem alfabética, alinhadas à esquerda.

Coopera com `format_abnt.py` (Decisão 28).

### Decisão 32 — render_latex (.tex + .pdf)

`.tex` ABNT-aproximado é parte obrigatória do pacote. Compilação para `.pdf` é tentada quando `pdflatex` ou `xelatex` está no PATH. Implementação sem dependência de `abntex2` (não disponível no TeX Live padrão); usa `geometry` + `setspace` + `mathptmx` + `babel[main=brazilian,provide=*]` para aproximar.

Ambiente `longquote` customizado (recuo 4cm + 10pt + singlespace) atende NBR 10520:2023 §6.1. Escape automático de `& % $ # _ { } ~ ^ < >`. Compilação faz 2 runs para resolver refs cruzadas, com timeout e log preservado.

PDF compilou com sucesso em ambiente de teste (TeX Live 2024, pdflatex). Smoke test verifica `pdf_compiled=True` quando `pdflatex` está disponível, skip caso contrário.

### Snowballing forward via OpenAlex

Complemento ao backward snowballing da v2.9.0. Implementação em `scripts/searches/snowballing_forward.py`:

1. Para cada seed DOI, resolve para Work ID OpenAlex.
2. Consulta `/works?filter=cites:<id>,publication_year:<year_start>-<year_end>` paginado.
3. Deduplica contra corpus já incluído + candidatos do backward.
4. Retorna candidatos com `origin: forward_snowballing` para retornar ao screening.

OpenAlex foi escolhido como única fonte gratuita robusta de "cited by" — Crossref tem `is-referenced-by` mas a cobertura é menor.

### Testes

115/115 passam em ~8.6s:
- 101 da regressão acumulada v2.0–v2.9.0
- 14 novos da v2.10.0:
  - 4 para `render_chunks` (basic, resume_from_chunk, anti-vazamento brand, content_json)
  - 3 para `render_docx_abnt` (produção, HTML stripping, conteúdo estruturado)
  - 4 para `render_latex` (basic, escape, longquote, compile PDF condicional)
  - 3 para `snowballing_forward` (mock, dedup/normalize, origin marker)

### Honestidade — limitações remanescentes

1. **Decisão 22 (re-execução por subversão)** — formalizada na v2.9.0, mas não há ainda detector automático no orquestrador para `today != last_run_date`. Roadmap declarado.
2. **Parsers detalhados de RSS/HTML dos adapters ibero-americanos** — continuam como TODO; modo mock funciona end-to-end.
3. **Compilação PDF em ambientes sem TeX Live completo** — a função detecta ausência e degrada graciosamente para entregar só `.tex`.
4. **abntex2 estrito** — usado approach com `article` + packages padrão para portabilidade. Usuário pode adaptar manualmente trocando classe.

### Estado dos contadores

- **Perfis YAML de venues:** 68 (inalterado desde v2.4.0).
- **Decisões editoriais formalizadas:** 33 (era 30 na v2.9.0; Decisão 18 saiu de "reservada" para "implementada", e 31, 32 foram adicionadas — total agora cobre 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33 + as 1-17 anteriores).
- **Adapters de busca:** 15 (era 14; +1 snowballing forward).
- **Renderers:** 5 (HTML monolítico v1, HTML monolítico v2, HTML em chunks v2.10, docx ABNT, tex/pdf).
- **Testes:** 115/115.

### Trilha de releases v2.8.0 → v2.9.0 → v2.10.0 — completa

Esta release fecha o ciclo de resposta à auditoria do RS-42 v1.0.0:

| Decisão | Categoria | Release |
|---|---|---|
| 18 | Reescrita de output | v2.8.0 (reservada) → v2.10.0 (implementada) |
| 19 | Eliminação | v2.8.0 |
| 20 | Persona | v2.8.0 |
| 21 | Consentimento implícito | v2.8.0 |
| 22 | Re-execução por subversão | v2.9.0 |
| 23 | Snowballing backward | v2.9.0 |
| 24 | Tier 3 → priority_0_routing | v2.9.0 |
| 25 | 6 adapters ibero-americanos | v2.9.0 |
| 26 | Todo elegível com rigor SR | v2.9.0 |
| 27 | EN+PT+ES como obrigação | v2.9.0 |
| 28 | ABNT NBR 6023+10520 | v2.9.0 |
| 29 | Cross-tabulação obrigatória | v2.9.0 |
| 30 | Remoção rabiscos | v2.8.0 |
| 31 | .docx ABNT | v2.10.0 |
| 32 | .tex + .pdf | v2.10.0 |
| 33 | Segredo industrial | v2.8.0 |

---

## [2.9.0] — 2026-05-03

Release de **adições obrigatórias** — segunda de três releases respondendo à auditoria do RS-42 v1.0.0. Esta release implementa as adições que a v2.8.0 mapeou como obrigatórias mas adiou. Sem mudança no que a skill produz como output final além do que vem das novas fontes; o impacto principal é amplitude de cobertura editorial (especialmente pt-BR/es-LA) e formalização de etapas que antes eram "polimento".

### Adicionado — 8 decisões editoriais novas (Decisões 22-29)

- **Decisão 22** — Re-execução obrigatória de buscas em data diferente por subversão. Estabilidade ≥ 95% como threshold; abaixo disso, warning + justificativa do usuário.
- **Decisão 23** — Snowballing backward (Wohlin 2014) obrigatório a partir dos seeds da Fase 5. Implementação em `scripts/searches/snowballing_backward.py`. Recupera referências via Crossref + fallback OpenAlex; deduplica contra corpus; candidatos retornam ao screening da Fase 4.
- **Decisão 24** — "Tier 3" renomeado para `priority_0_routing`. Bases pagas (Scopus/WoS/Embase/IEEE Xplore subset/ACM/Elsevier ScienceDirect) deixam de ser "lacuna aceitável" e viram tentativa via Tier 0 (Unpaywall + OAB + CORE + Periódicos CAPES com CAFe). O que sobrar entra no `gap_report.md` (já existente).
- **Decisão 25** — Bases ibero-americanas obrigatórias em todas as áreas: SciELO, LA Referencia, Redalyc, CLACSO, BDTD, Scioteca, DOAJ, Periódicos CAPES, LILACS/BVS. Antes eram "polimento"; agora são obrigação.
- **Decisão 26** — Todo elegível recebe extração com rigor de SR, independente do modo. Heurística "extrair só núcleo" eliminada.
- **Decisão 27** — EN+PT+ES como obrigação, não limitação. Linguagem de "limitação" removida da rubrica e da seção §09 gerada.
- **Decisão 28** — Formatação ABNT NBR 6023:2018 + NBR 10520:2023 obrigatória em pt-BR. Implementação em `scripts/format_abnt.py` com 10 tipos de referência cobertos.
- **Decisão 29** — Tabela cross-tabulação obrigatória na síntese §05. Implementação em `scripts/cross_tabulation.py` com 2D, 3D estratificada, células multi-valor.

### Adicionado — 8 módulos Python novos

```
scripts/searches/
├── search_la_referencia.py        # Tier 1 — rede federada LA, ~5M registros
├── search_redalyc.py              # Tier 1 — ~1.300 revistas OA Ibero
├── search_clacso.py               # Tier 1 — ciências sociais LA, ~150k itens
├── search_bdtd.py                 # Tier 1 — ~750k teses/dissertações BR
├── search_scioteca.py             # Tier 1 — gray literature CAF
├── search_periodicos_capes.py     # Tier 0 — gateway com instruções acionáveis sem credenciais
├── search_core.py                 # Tier 0 — CORE API ~280M artigos OA
└── snowballing_backward.py        # Wohlin 2014, Crossref + OpenAlex fallback

scripts/
├── format_abnt.py                 # NBR 6023:2018 + NBR 10520:2023
└── cross_tabulation.py            # 2D + 3D estratificada
```

### Modificado — `search_orchestrator.py`: TIER_DATABASES reorganizado

- Nova área `ciencias_sociais` adicionada (antes só "saude", "educacao", "cs_se", "multi").
- `priority_0_routing` substitui `tier3` (alias `tier3` mantido até v2.10.0 para retrocompatibilidade).
- Bases ibero-americanas (`scielo`, `lareferencia`, `redalyc`, `clacso`, `bdtd`, `scioteca`) listadas em todas as áreas onde fazem sentido.
- `core` (Tier 0 routing) listado em todas as áreas como cobertura ampla complementar.

### Cobertura editorial: antes vs depois

| | v2.8.0 | v2.9.0 |
|---|---|---|
| Tier 1 em "saude" | 5 bases | 11 bases |
| Tier 1 em "educacao" | 3 bases | 9 bases |
| Tier 1 em "cs_se" | 4 bases | 8 bases |
| Tier 1 em "multi" | 5 bases | 10 bases |
| Áreas suportadas | 4 | 5 (+ ciencias_sociais) |
| Tier 0 OA locators | 2 (Unpaywall, OAB) | 3 (+ CORE) + Periódicos CAPES como gateway |

### Testes

101/101 passam em ~5s:
- 79 da regressão acumulada v2.0–v2.8.0
- 22 novos da v2.9.0:
  - 3 para snowballing_backward
  - 2 para TIER_DATABASES reorganizado
  - 7 para os adapters ibero-americanos individuais
  - 6 para format_abnt (NBR 6023:2018 + NBR 10520:2023)
  - 4 para cross_tabulation (2D, 3D, multi-valor, ausências)

### Honestidade — o que esta release NÃO entrega

1. **Parsers detalhados de RSS/HTML.** Os adapters LA Referencia, Redalyc, CLACSO, BDTD, Scioteca em modo real retornam `raw_size_bytes` + URL consultada com nota "parser detalhado é TODO". O usuário pode pós-processar com feedparser/BeautifulSoup. Modo `mock` funciona end-to-end.
2. **Snowballing forward.** Apenas backward está implementado. Forward (citações posteriores) fica para v2.10.0+.
3. **Validação real do CORE API.** Modo real está implementado mas sem fixtures de teste real (apenas mock). API key opcional via `IGNORANTIA_CORE_API_KEY` ou `--core-api-key`.
4. **Periódicos CAPES via scraping.** Não há scraping. Quando o usuário tem CAFe, o adapter retorna instruções acionáveis (boolean query + URL do portal + onde colocar o export); o usuário entra manualmente, executa, exporta, salva em `user_provided/`.
5. **Snowballing forward + render `.docx` + `.tex` + `.pdf` + HTML em chunks** ficam todos para **v2.10.0**.

### Estado dos contadores

- **Perfis YAML de venues:** 68 (inalterado).
- **Decisões editoriais formalizadas:** 30 (era 22 na v2.8.0; +8 nesta release: 22-29).
- **Áreas suportadas:** 5 (+ ciencias_sociais).
- **Adapters de busca:** 14 (era 6 na v2.8.0; +8: la_referencia, redalyc, clacso, bdtd, scioteca, periodicos_capes, core, snowballing_backward).
- **Testes:** 101/101.

---

## [2.8.0] — 2026-05-03

Release de **eliminação** — primeira de uma série de releases que respondem à auditoria do RS-42 v1.0.0 (primeiro paper gerado pela skill em uso real). Esta release não adiciona código novo. Apenas remove vazamentos identificados, formaliza decisões editoriais que mudam comportamento de geração futura e corrige a rubrica de avaliação. Releases v2.9.0 e v2.10.0 implementarão as adições obrigatórias (search adapters latino-americanos, snowballing, formatador ABNT, render `.docx`/`.tex`/`.pdf`, escrita HTML em chunks).

### Adicionado — 4 decisões editoriais novas (Decisões 18-21, 30, 33)

- **Decisão 18** — Reservada. Reescrita HTML em chunks/append na Fase 7. Implementação em v2.10.0.
- **Decisão 19** — Anti-vazamento de meta-discurso do skill no manuscrito. Regra absoluta: o output do skill nunca menciona o nome do skill, suas decisões internas, critérios de aceitação ou templates como conteúdo do manuscrito. O manuscrito é a voz do pesquisador, não do skill.
- **Decisão 20** — Voz autoral padrão (persona) registrada como instrução interna do ghostwriter. Acadêmica neutra impessoal, ABNT/Vancouver, IMRaD, sem hedging ornamental. A persona NÃO aparece em nenhum output — é label interno; o by-line do paper carrega o nome real do autor.
- **Decisão 21** — Spot-check humano da Fase 4 = aceite implícito ao prosseguir. Ao usuário avançar do screening para a extração, o `reproducibility_manifest.yaml` registra automaticamente `phase4_exclusions_review: implicit_consent`. Critério "spot-check separado" removido da rubrica D1.
- **Decisão 30** — Remoção da feature "rabiscos for fun". Linha removida do SKILL.md. Função `build_fun_doodles_html` reduzida a stub que sempre retorna string vazia (mantida para retrocompatibilidade com `content.json` antigos).
- **Decisão 33** — Identidade da skill como segredo industrial. Onde menções a IA são legalmente obrigatórias (Portaria CNPq 2.664/2026, ICMJE, COPE), o disclosure usa o padrão "algoritmo particular do autor (não-divulgado por segredo industrial) + LLM declarado". Provider e modelo do LLM divulgados; arquitetura interna do skill não.

### Modificado — limpeza de templates HTML do manuscrito

- `assets/templates/manuscript-template.html`:
  - `<title>{{TITLE}} — ignorantia v{{VERSION}}</title>` → `<title>{{TITLE}} — v{{VERSION}}</title>`.
  - `<meta name="generator" content="ignorantia v{{SKILL_VERSION}}">` → `<meta name="generator" content="algoritmo particular do autor + Claude (Anthropic)">`.
  - Topbar: brand `ignorantia` removido; substituído por `{{TITLE_SHORT}}` (placeholder a ser preenchido com nome curto do paper).
  - Footer: `<strong>ignorantia</strong> v{{VERSION}}` → `v{{VERSION}}` (sem brand).
- `scripts/render_manuscript.py`:
  - Default do campo `interface` no AI disclosure mudou de `"ignorantia v..."` para `"algoritmo particular do autor (não-divulgado por segredo industrial) + LLM declarado acima"`.
  - `build_fun_doodles_html` reduzida a stub (Decisão 30).

### Modificado — `references/quality-rubric.md`

- D5 reescrita: critério "Charts D3 + PRISMA inline + matriz de venues" → "PRISMA flow inline (SVG) + matriz de venues". Visualização interativa não é mais critério de qualidade.
- Nova seção "Critérios removidos da rubrica (v2.8.0)" listando os 9 critérios eliminados com razão de remoção, alguns deles reescritos/realocados para v2.9.0 e v2.10.0.
- Disclaimer final: removida menção literal "skill `ignorantia`".

### Modificado — `SKILL.md`

- Linha 320 (antiga) descrevendo a camada de rabiscos for fun foi removida (Decisão 30).
- Adicionado bloco completo da Decisão 19 (anti-vazamento), Decisão 20 (persona — completa, com cláusula "O que a persona NÃO faz"), Decisão 21 (consentimento implícito), Decisão 30 (remoção rabiscos), Decisão 33 (segredo industrial).

### Test-cases legados — não-regressão

`test-cases/scenarios/{ghostwriter,smoke,corpus18}/manuscript.html` ainda contêm referências à feature de rabiscos. São snapshots históricos de regressão da v1.x — sua função é congelar comportamento histórico, não ser canonical. Não foram modificados nesta release. Não vão para o pacote dist.

### Testes

79/79 passam em ~4.26s:
- 74 da regressão acumulada v2.0–v2.7.1
- 5 novos da v2.8.0 (todos validam mecanicamente as decisões):
  - `test_decision_19_template_has_no_skill_branding` — varre `<title>`, meta generator, topbar brand, footer brand.
  - `test_decision_19_render_manuscript_default_interface_is_protected` — valida default protegido.
  - `test_decision_30_fun_doodles_builder_is_stub` — valida que `build_fun_doodles_html` retorna `""` mesmo com input não-vazio.
  - `test_decision_30_skill_md_does_not_describe_fun_doodles` — varre SKILL.md por termos da feature fora do bloco da Decisão 30.
  - `test_decision_20_persona_block_present_in_skill_md` — confirma blocos críticos da persona presentes.

### Honestidade — o que esta release NÃO entrega

Esta é uma release de **eliminação**. As **adições obrigatórias** identificadas pela mesma auditoria (snowballing backward, 9 search adapters latino-americanos, formatador ABNT detalhado, geração `.docx`/`.tex`/`.pdf`, escrita HTML em chunks, tabela cross-tabulação obrigatória) ficam para v2.9.0 e v2.10.0. O paper RS-42 v1.0.0 já foi gerado e não será reescrito automaticamente — a próxima execução do skill (ou re-run do RS-42 em uma v1.0.1) sairá limpa de meta-discurso, mas as adições só entram com v2.9.0 entregue.

### Estado dos contadores

- **Perfis YAML de venues:** 68 (inalterado).
- **Decisões editoriais formalizadas:** 22 (era 17; +5 nesta release: 18, 19, 20, 21, 30, 33).
- **Testes:** 79/79.

---

## [2.7.1] — 2026-05-03

Correção editorial: remoção dos nomes literais de plataformas em disputa judicial em todo o projeto. Esta release não altera comportamento — apenas evita que buscas por esses nomes retornem este projeto como resultado, o que é desnecessário para o funcionamento e poderia gerar associações indesejadas.

### Modificado — substituição de identificadores nominais por termos genéricos

Em todos os arquivos do projeto (SKILL.md, CHANGELOG.md, MODES_OVERVIEW.md, journal.txt, docstrings em scripts, comentários de testes), os nomes literais de duas plataformas em disputa judicial foram substituídos por:

- **"plataformas em disputa judicial"** — termo de uso geral em texto corrido.
- **"plataformas excluídas do pipeline"** — quando o foco é a exclusão arquitetural.
- **"tokens canônicos de plataformas excluídas"** — em referências aos testes mecânicos.

A semântica permanece exatamente a mesma. A intenção da Decisão 17 (não-integração arquitetural com plataformas em disputa, gap_report.md neutro, soberania do usuário sobre como obter material de acesso fechado) está integralmente preservada.

### Modificado — testes renomeados sem mudança de comportamento

- O teste mecânico que valida ausência de URLs de plataformas excluídas no código foi renomeado para `test_decision_17_excluded_platforms` (nome anterior continha identificadores nominais).
- A lista de tokens literais que o teste valida permanece dentro do código do teste (é o que o teste afere) mas agora reside em variável local com nome neutro: `excluded_platform_url_tokens` em `test_v26_tier0.py`, `excluded_terms` em `test_v27_gap_report.py`.
- Os arquivos de teste vão para o pacote completo (full) mas são **removidos do dist** durante o stripping, então o usuário final não tem contato com esses tokens em nenhum momento.

### Sem mudança de comportamento de runtime

- 68 perfis YAML inalterados.
- 17 decisões editoriais inalteradas.
- 74/74 testes passam (mesmo set, apenas com nome do teste mecânico atualizado).
- CLI inalterada.
- Output do skill (gap_report.md, tier0_oa_enrichment.json, search_summary.json) idêntico.

### Estado dos contadores

- **Total de arquivos no pacote (full):** ~263 (inalterado vs v2.7.0).
- **Decisões editoriais formalizadas:** 17 (inalterado).
- **Testes:** 74/74.

---

## [2.7.0] — 2026-05-03

Correção de posição editorial e introdução do **gap report com pausa para resolução manual**. Esta release responde a feedback do usuário identificando viés no skill: ao afirmar que "plataformas em disputa judicial distribuem cópias não-licenciadas e seu uso constitui infração", o skill estava replicando a narrativa dos publishers em litigância como se fosse fato neutro. A operação técnica dessas plataformas é objeto de disputa judicial em curso; o mérito não cabe ao skill avaliar.

### Modificado — Decisão 17 (posição neutra real)

A redação anterior ("distribuem cópias não-licenciadas / constitui infração") foi substituída por:

- O `ignorantia` **não toma posição** sobre plataformas em disputa judicial.
- Não-integração é **arquitetural**: integrar automaticamente significaria adotar uma posição sobre como o usuário deve obter material fechado, violando soberania do usuário.
- O skill resolve o problema **operacional** (acesso a paywalled durante triagem) sem decidir pelo usuário: Unpaywall + OAB cobrem subset OA legítimo automaticamente; para o restante, gera-se gap_report.md e pausa.
- Como o usuário obtém os itens é decisão do usuário. O skill não recomenda nem desaconselha plataformas, serviços ou métodos.

A linguagem em `references/compliance-international.md` que dizia "acesso via plataformas em disputa é ilegal e não é recomendado" foi removida pela mesma razão.

### Adicionado — `scripts/searches/access_gap_report.py`

Novo módulo que gera relatório markdown listando itens cujo full-text não foi resolvido por Tier 0. Estrutura:

- **Artigos paywalled ou sem OA disponível** — DOI, título, periódico, ano, status Tier 0, link de solicitação ao autor.
- **Livros e capítulos** — ISBN/ID, título, editora, ano, notas.
- **Outros itens inacessíveis** — identificador, tipo, descrição.

Linguagem deliberadamente neutra. O test `test_gap_report_md_is_neutral` valida mecanicamente que o relatório não menciona tokens canônicos de plataformas excluídas e juízos legais categóricos em nenhuma forma — favorável ou desfavorável.

### Modificado — `search_orchestrator.py`: pausa para resolução manual

Novo fluxo após Tier 0:

1. Tier 0 (Unpaywall + OAB) resolve o que pode automaticamente.
2. Restante é listado em `<output-dir>/gap_report.md`.
3. Skill cria diretório `<output-dir>/user_provided/`.
4. Skill **pausa** com `exit code 10` (pausa intencional, não erro).
5. Usuário providencia full-texts por qualquer meio que escolher e os coloca em `user_provided/`.
6. Usuário retoma com `--resume-after-gap-report` ou pula com `--skip-gap-resolution`.

Itens não providenciados serão registrados como "excluídos por inacessibilidade" no PRISMA flow diagram, com motivo declarado para auditoria — prática padrão que não compromete integridade da revisão.

### Adicionado — flags CLI (3 novas)

- `--project-id <nome>` — identificador legível usado no cabeçalho do gap_report.md.
- `--resume-after-gap-report` — retoma execução após resolução manual.
- `--skip-gap-resolution` — pula a pausa; itens inacessíveis viram exclusões no PRISMA.

### Testes

74/74 passam em ~6.35s:
- 69 da regressão acumulada v2.0–v2.6.1
- 5 novos da v2.7.0:
  - `test_gap_report_collects_only_non_oa_items`
  - `test_gap_report_md_is_neutral` ← **valida posição neutra do relatório**
  - `test_gap_report_writes_md_file`
  - `test_gap_report_handles_books`
  - `test_gap_report_no_items_renders_empty`

### CLI canônica v2.7.0

```bash
# Execução normal — Tier 0 roda automaticamente, gera gap_report e pausa
export IGNORANTIA_CONTACT_EMAIL=contato@projeto.org
python3 scripts/searches/search_orchestrator.py \
    --query "letramento digital idosos" \
    --year-start 2020 --year-end 2026 \
    --area saude --mode scoping_review \
    --project-id "letramento-digital-idosos" \
    --output-dir search_results/

# (skill pausa em exit 10; usuário providencia full-texts em user_provided/)

# Retomar
python3 scripts/searches/search_orchestrator.py [...] --resume-after-gap-report

# OU pular sem providenciar (itens viram exclusões no PRISMA)
python3 scripts/searches/search_orchestrator.py [...] --skip-gap-resolution
```

### Honestidade — o que mudou e por quê

A correção é editorial, não técnica. O comportamento técnico já era o correto desde v2.6.0: Tier 0 cobre OA legítimo, o restante fica sem solução automatizada. O que mudou foi:

1. A **redação** da Decisão 17 — agora reconhece honestamente que o `ignorantia` não tem como (nem deve) julgar litígios em curso.
2. A **interface** — em vez de só "não integra plataformas em disputa e silencia", agora há um relatório explícito do gap e uma pausa para o usuário agir conforme sua própria avaliação.

A posição operacional permanece a mesma (não há integração automatizada com plataformas em disputa judicial). O que ficou diferente foi reconhecer que essa decisão não precisa ser justificada com julgamento moral sobre essas plataformas — basta reconhecer que decisão sobre como obter material é do usuário, não do skill.

### Estado dos contadores

- **Total de arquivos no pacote (full):** ~263 (era 261 na v2.6.1; +2 do gap report).
- **Perfis YAML de venues:** 68 (inalterado).
- **Decisões editoriais formalizadas:** 17 (texto da 17 corrigido; sem nova decisão).
- **Testes:** 74/74.

---

## [2.6.1] — 2026-05-03

Correção de design da v2.6.0 baseada em feedback do usuário: **Tier 0 deve ser automático, não opcional**. Se Unpaywall + OAB são legais e cobrem o problema operacional, fazer da execução um opt-in apenas pune quem esquece de ativar — sem ganho semântico real para quem ativa.

### Modificado — Tier 0 agora é automático

**Antes (v2.6.0):**
- `--enrich-tier0` (opt-in obrigatório)
- `--tier0-email` (argumento exigido fora de mock)
- `--tier0-mock` (flag de dev contaminando interface de produção)

**Depois (v2.6.1):**
- Tier 0 roda **automaticamente** após qualquer Tier 1-3 retornar DOIs.
- `--skip-tier0` (única forma de desligar; reservada para uso offline/CI).
- `--contact-email` (opcional; lê `IGNORANTIA_CONTACT_EMAIL` do ambiente como fallback).
- Sem flag de mock vazando para produção: mock fica restrito aos clientes individuais (`search_unpaywall.py --mock`, `tier0_resolver.py --mock`) e à infraestrutura de teste.

Princípio operacional registrado: **se uma operação é legal e resolve o problema, ela é default — não opção**. Opções existem para escolhas com conteúdo real (trade-off de tempo/qualidade, override de comportamento default em casos de borda). Tier 0 não tem trade-off — apenas pune o usuário que esquece de ativar.

### Sem mudança em comportamento de runtime

- 68 perfis YAML inalterados.
- 17 decisões editoriais inalteradas.
- 69/69 testes passam (smoke tests não dependiam das flags antigas).
- Apenas a CLI do `search_orchestrator.py` mudou.

### CLI canônica v2.6.1

```bash
# Uso normal — Tier 0 roda automaticamente
export IGNORANTIA_CONTACT_EMAIL=contato@projeto.org
python3 scripts/searches/search_orchestrator.py \
    --query "letramento digital idosos" \
    --year-start 2020 --year-end 2026 \
    --area saude --mode scoping_review \
    --output-dir search_results/

# Ou passando email diretamente
python3 scripts/searches/search_orchestrator.py [...] \
    --contact-email contato@projeto.org

# Pular Tier 0 (apenas modo offline)
python3 scripts/searches/search_orchestrator.py [...] --skip-tier0
```

### Ajuste em SKILL.md

Seção "Quando Tier 0 é chamado" reescrita para refletir comportamento automático.

---

## [2.6.0] — 2026-05-03

Adição de **Tier 0 OA locator legítimo** ao pipeline de busca, formalizado pela **Decisão 17**. A solicitação original do usuário foi por integração de plataformas em disputa judicial como fontes prioritárias; a resposta do skill foi fornecer cobertura equivalente do problema operacional (acesso a artigos paywalled durante triagem PRISMA) via fontes 100% legítimas: Unpaywall + Open Access Button + fallback de solicitação ao autor.

### Adicionado — Decisão 17: Tier 0 + exclusão vinculante de plataformas em disputa judicial

A política OA-first da Decisão 11 (v2.1) opera sobre **bases de busca por query**. A v2.6.0 adiciona um **Tier 0** que opera sobre **resolução por DOI**: dado qualquer DOI encontrado em Tier 1-3, descobrir a melhor URL de full-text legítimo disponível.

Cadeia de prioridade Tier 0:

1. **Unpaywall API** — ~50M+ artigos OA legítimos indexados (golden + hybrid + green/preprint).
2. **Open Access Button** — best-effort complementar; cobertura ligeiramente diferente (mais ênfase em preprints e green OA).
3. **CAFe / institucional** — placeholder que requer credenciais do usuário (CAFe da RNP intermedia acesso a Capes Periódicos legalmente).
4. **Solicitação ao autor** — URL `https://oa.works/request/<doi>` gerada como fallback final; padrão acadêmico legítimo.

**Plataformas em disputa judicial estão explicitamente excluídas** do pipeline. Esta exclusão é vinculante:
- Plataformas distribuem cópias não-licenciadas de obras protegidas por direito autoral.
- Em jurisdições onde a `ignorantia` roda (Brasil incluído via TRIPS+ e Lei 9.610/98), uso constitui infração.
- Construir o skill priorizando essas fontes incompatibilizaria com Decisão 4 (Zenodo + DOI verifier + Crossref) e com auditabilidade ao submeter manuscrito a editoras.
- Test `test_decision_17_excluded_platforms` valida mecanicamente que nenhuma URL dessas plataformas aparece no código.

### Adicionado — 3 módulos Python em `scripts/searches/`

- **`search_unpaywall.py`** — cliente Unpaywall com fallback gracioso real/mock; fixtures determinísticas para 3 DOIs canônicos da literatura SLR (Rayyan, PRISMA-2020, closed-fixture); rate limit responsável ≤10 req/s; classe `UnpaywallRecord` normalizada com 16 campos (oa_status, license, version, repository_urls, journal_is_in_doaj, etc.).
- **`search_oa_button.py`** — cliente Open Access Button best-effort; trata 404 como "no OA encontrado" graciosamente; sempre retorna `request_url` como fallback para solicitação ao autor.
- **`tier0_resolver.py`** — resolvedor unificado que orquestra Unpaywall → OAB → author request em ordem de prioridade; classe `Tier0Record` consolidada com `sources_tried` rastreável e `errors_per_source` auditável.

### Modificado — `search_orchestrator.py`

Adicionadas 3 novas flags CLI:
- `--enrich-tier0` — após Tier 1-3, enriquece DOIs encontrados com URLs OA legítimas.
- `--tier0-email <email>` — exigido pela Unpaywall API (boa-fé do usuário).
- `--tier0-mock` — usa fixtures (CI/dev sem internet).

Output adicional: `<output-dir>/tier0_oa_enrichment.json` com schema `{schema_version, tier, n_dois, n_oa_found, n_author_request_only, records}`. Helper `_collect_dois_from_tier_files` extrai DOIs únicos dos arquivos JSON gerados pelos `search_*.py` Tier 1.

### Testes

69/69 passam em ~4.50s:
- 61 da regressão acumulada v2.0–v2.5.0
- 8 novos da v2.6.0:
  - `test_unpaywall_mock_known_doi_returns_oa`
  - `test_unpaywall_mock_closed_doi_returns_no_oa`
  - `test_unpaywall_real_without_email_fails_gracefully`
  - `test_oa_button_mock_known_doi_returns_oa`
  - `test_oa_button_mock_unknown_doi_returns_request_url`
  - `test_tier0_resolver_priority_order`
  - `test_tier0_resolver_records_metadata_even_when_no_oa`
  - `test_decision_17_excluded_platforms` ← **valida mecanicamente a exclusão**

### CLI canônica v2.6.0

```bash
# Resolver 1 DOI
python3 scripts/searches/tier0_resolver.py \
    --doi "10.1186/s13643-016-0384-4" --email contato@projeto.org

# Resolver lista de DOIs
python3 scripts/searches/tier0_resolver.py \
    --dois-file dois.txt --email contato@projeto.org --out enriched.json

# Pipeline completo Tier 1 → Tier 0
python3 scripts/searches/search_orchestrator.py \
    --query "letramento digital idosos" \
    --year-start 2020 --year-end 2026 \
    --area saude --mode scoping_review \
    --enrich-tier0 --tier0-email contato@projeto.org \
    --output-dir search_results/
```

### Honestidade — o que esta release entrega e não entrega

**Entrega:**
- Caminho legítimo, reprodutível e auditável para resolver paywall durante triagem PRISMA.
- Cobertura ampla via Unpaywall (~50M artigos OA reais).
- Transparência total quando não há OA disponível (URL de solicitação ao autor).
- Exclusão **mecanicamente verificada** de plataformas em disputa judicial.

**Não entrega:**
- Acesso a artigos genuinamente fechados onde nem o publisher nem o autor depositaram OA. Para esses, o caminho legítimo é (a) pedir cópia ao autor, (b) usar acesso institucional via CAFe quando disponível, (c) excluir o artigo da revisão e declarar a exclusão no PRISMA flow diagram com motivo "full-text inacessível".

### Estado dos contadores

- **Total de arquivos no pacote:** 300 (era 297 na v2.5.0; +3 do Tier 0).
- **Perfis YAML de venues:** 68 (inalterado).
- **Decisões editoriais formalizadas:** 17 (era 16 na v2.5.0; +1 da Decisão 17).
- **Testes:** 69/69.

---

## [2.5.0] — 2026-05-03

Etapa 4b da estratégia consolidada — **infraestrutura mínima funcional para comparação automatizada com baselines**. Esta release não inclui validação empírica (que requer casos reais de SLR), mas constrói o andaime reprodutível para que a validação aconteça quando casos reais existirem. Base documental: `/mnt/project/Baseline_Mapping_for_Automated_Comparison_of_the_ignorantia_Tool_v2_4_0.md`.

**Mudança de natureza vs releases anteriores.** A v2.x até v2.4.0 expandiu catálogo (perfis YAML de venues). A v2.5.0 adiciona infraestrutura de avaliação (clientes, métricas, schema de output). Não há novos perfis YAML de venues nesta release; os 68 perfis da v2.4.0 permanecem inalterados.

### Adicionado — `scripts/comparison/` (10 módulos Python + 2 schemas + 3 fixtures)

**Estrutura:**

```
scripts/comparison/
├── PROTOCOL.md                              # protocolo de comparação reprodutível
├── schemas/
│   ├── manuscript_input.schema.json         # input padronizado
│   └── unified_output.schema.json           # output unificado v1.0.0
├── clients/
│   ├── bson.py                              # B!SON real + mock (única API REST aberta)
│   ├── asreview.py                          # ASReview LAB v2 subprocess + mock
│   ├── jane.py                              # JANE scaffold (TODO: self-host Lucene)
│   └── snapshot.py                          # ingestor de snapshots manuais
├── metrics/
│   ├── topk.py                              # top-k accuracy, MRR, nDCG@k
│   ├── wss.py                               # WSS@95, recall@k%, ATD
│   └── compliance.py                        # F1, sensibilidade, especificidade, Cohen's κ
├── unify.py                                 # consolida tudo em JSON unificado
├── report.py                                # gera markdown comparativo
├── fixtures/
│   ├── manuscript_001.json                  # input sintético
│   ├── ignorantia_001.json                  # output sintético do engine
│   └── penelope_ms_001_20260420.json        # snapshot Penelope sintético
└── tests/
    └── test_comparison_smoke.py             # 8 smoke tests
```

### Arquitetura — fallback gracioso em todos os clientes

Cada cliente de baseline tem dois modos:

- **`real`**: chama API live (B!SON), executa subprocess (ASReview), ou aguarda implementação (JANE scaffold).
- **`mock`** (default em CI): retorna fixture determinística com valores plausíveis baseados em literatura publicada (van de Schoot et al. 2025 para ASReview; Entrup et al. 2023 para B!SON).

Isso permite que CI rode sem internet e sem dependências pesadas (asreview não está no environment de teste). Para uso real, basta passar sem `--mock`.

### Exclusões declaradas e auditáveis

Conforme PROTOCOL.md §8, estas ferramentas estão **explicitamente excluídas** da comparação automatizada com justificativa documentada:

- **Editorial Manager, ScholarOne, OJS, eJournalPress** — workflow systems; não fazem comparação semântica de conteúdo (apenas validação de metadados/file types).
- **Wiley JF, T&F Suggester, IEEE Recommender, WoS Manuscript Matcher** — caixas-pretas comerciais sem API; ToS proíbe scraping; opção é snapshot manual em P3.
- **Trinka, Writefull, Paperpal** — writing assistants B2B com licença paga; não comparáveis ao engine determinístico.

### Métricas implementadas

Conforme PROTOCOL.md §5 (alinhadas com convenções publicadas):

- **Recommenders (categoria 1):** Top-1, Top-5, Top-10 accuracy; MRR; nDCG@10.
- **Screening (categoria 2):** WSS@95 (Cohen et al. 2006; van de Schoot 2025); recall@k%; ATD.
- **Compliance (categoria 3):** F1 item-level; sensibilidade; especificidade; Cohen's κ.

### Pipeline ponta-a-ponta validado

Smoke test rodou com fixtures sintéticas:
- Input: `manuscript_001.json` (modo systematic_review_with_2_reviewers; ground truth = PLOS ONE)
- Output: relatório markdown 1688 chars com tabelas de Top-10 ignorantia, Top-10 B!SON, simulação ASReview, snapshot Penelope, métricas e limitações declaradas.

### CLI canônica

```bash
python3 -m clients.bson --input fixtures/manuscript_001.json --mock --out /tmp/bson_001.json
python3 -m clients.asreview --dataset SYNERGY/van_de_Schoot_2018 --mock --out /tmp/asr_001.json
python3 unify.py --manuscript fixtures/manuscript_001.json \
                 --ignorantia fixtures/ignorantia_001.json \
                 --bson /tmp/bson_001.json --asreview /tmp/asr_001.json \
                 --snapshots-dir fixtures --out /tmp/unified_001.json
python3 report.py --input /tmp/unified_001.json --out /tmp/report_001.md
```

### Testes

61/61 passam em ~4.45s:
- 53 da regressão acumulada v2.0–v2.4.0
- 8 novos da v2.5.0:
  - `test_bson_mock_returns_ranking`
  - `test_asreview_mock_returns_reference_values`
  - `test_jane_mock_returns_biomed_ranking_for_biomed_input`
  - `test_topk_metrics_correct`
  - `test_compliance_metrics_correct`
  - `test_wss_metric_correct`
  - `test_unify_pipeline_end_to_end`
  - `test_report_renders`

### Honestidade — o que esta release NÃO entrega

1. **Sem casos reais.** Todos os fixtures são sintéticos. Resultados do smoke test **não constituem validação empírica** da `ignorantia` contra baselines.
2. **B!SON em modo mock por default.** Para chamada real à API live, é preciso rodar sem `--mock`. Cobertura editorial limitada a DOAJ.
3. **JANE em scaffold.** Mock retorna valores plausíveis biomédicos; para uso real precisa self-host (TODO documentado).
4. **ASReview sem instalação.** Modo real requer `pip install asreview` + dataset SYNERGY baixado.
5. **Snapshots manuais não automatizam.** Penelope/Elsevier/Springer/etc. exigem submissão à UI manual e datada — o ingestor lê arquivos JSON pré-criados.
6. **Validação empírica continua pendente.** Etapa 4b só será considerada completa quando 1-2 SLRs reais forem processadas pelo pipeline e o relatório comparativo for produzido com dados não-sintéticos.

### Próximos passos (gates declarados)

A infraestrutura desta release **abre o caminho** para Etapa 4b empírica:

1. Quando o usuário tiver 1-2 SLRs reais conduzidas com a ferramenta, converter para `manuscripts/<id>.json`.
2. Rodar `clients/bson.py` em modo real (`--mock` removido) para subset OA.
3. Submeter à UI de Penelope.ai e salvar `snapshots/penelope_<msid>_<YYYYMMDD>.json`.
4. Rodar `unify.py` + `report.py`.
5. Reportar como **Etapa 4b empírica concluída** no journal e CHANGELOG.
6. Abrir gate para **Etapa 5** — retomar `references/draft/PUBLISHABLE_ASPECTS_ANALYSIS.md` com base empírica concreta. Decidir se há bom motivo para escrever os 3 papers (Dataset, Position, Software) declarados em "Skill: Ignorantia".

### Estado dos contadores

- **Total de arquivos no pacote:** 286 (era 272 na v2.4.0; +14 da nova infraestrutura).
- **Perfis YAML de venues:** 68 (inalterado vs v2.4.0).
- **Decisões editoriais formalizadas:** 16 (inalterado).
- **Testes:** 61/61.

---

## [2.4.0] — 2026-05-03

Etapa 3 da estratégia consolidada concluída: catálogo Q2 INT por área-mãe Sucupira. Esta release **completa o roadmap original v2.x** declarado pelo usuário no início do ciclo: ≥3 venues por estrato (A1, A2, A3, B1) BR + ≥3 Q2 INT por área. Base documental fornecida pela mesma pesquisa "Qualis A3, B1 BR Diamond OA e Q2 Internacional para a Ferramenta `ignorantia`" (Etapa 1) que sustentou a v2.3.

### Adicionado — Decisão 16: convenção de pasta `venues_qN_int` é organizativa, não estrita

Identificada inconsistência herdada da v2.2.0: dois perfis em `venues_q1_int/` (`f1000research` SJR Q2 e `frontiers_education` SJR Q2) não são Q1 SJR estrito, mas foram catalogados lá pela convenção frouxa de "alto-padrão internacional" da v2.2.0.

A Decisão 16 estabelece:

- **Pastas `venues_qN_int/` são organizativas**, agrupando venues por foco do catálogo (Q1 = "elite/prestígio internacional"; Q2 = "alto-padrão acessível"), **não por estrato estrito**.
- **O quartil real é dado pelos campos `sjr_quartile` e `jcr_quartile` em metadata**, que são autoritativos para queries do engine.
- **Sem refator obrigatório dos perfis pré-existentes**: f1000research e frontiers_education permanecem em `venues_q1_int/` por convenção de origem; novos perfis Q2 puros vão para `venues_q2_int/`.
- O engine, ao filtrar por quartil, deve sempre consultar metadata, nunca inferir do nome da pasta.

Decisão coerente com Decisão 14 (vocabulário de tiers como propriedade explícita em metadata) e Decisão 15 (recalibração baseada em evidência documental, não em pasta).

### Adicionado — 11 perfis Q2 INT em `venues_q2_int/`

**Q2 INT Educação (4):**
- **`cogent_education.yaml`** — Cogent Education (T&F, UK) — Q2 SJR/JCR; fully OA APC ~USD 1.620; **Tier 2** (publisher comunitário T&F Cogent OA).
- **`ethe_uoc_springer.yaml`** — International Journal of Educational Technology in Higher Education (Springer/UOC) — Q1 SJR mas catalogado como Q2 INT por ser **único caso de Q1 INT diamond OA verificável** em Education; **Tier 1**.
- **`education_sciences_mdpi.yaml`** — Education Sciences (MDPI) — Q1 SJR, Q2 em subáreas; APC ~USD 2.000; **Tier 2**.
- **`edu_studies_routledge.yaml`** — Educational Studies (T&F) — Q2 SJR estrito; hybrid APC USD 3.490; **Tier 3**.

**Q2 INT Saúde (3):**
- **`bmc_med_education.yaml`** — BMC Medical Education (BMC/Springer Nature) — Q1 Medicine misc / Q2 Education; fully OA APC USD 2.890; **Tier 3** (Tier 2 efetivo com waiver Springer Nature para autores BR elegíveis); PRISMA-2020 obrigatório.
- **`rlae_usp.yaml`** — Revista Latino-Americana de Enfermagem (USP-EERP, BR) — Q2 SJR Nursing; **diamond OA**; **Tier 1**. **ÚNICO CASO IDENTIFICADO de Q2 INT + Tier 1 + brasileiro simultaneamente** — venue prioritário do catálogo em Saúde.
- **`nep_elsevier.yaml`** — Nurse Education in Practice (Elsevier) — Q2 SJR Education; hybrid APC USD 3.090; **Tier 3**.

(*Nota:* PLOS ONE não foi adicionado em venues_q2_int/ porque já está catalogado em venues_q1_int/ desde v2.2.0 — é Q1 SJR Multidisciplinary; sua classificação Q2 ocorre apenas em algumas subcategorias Medicine.)

**Q2 INT CS/SE/Eng (4):**
- **`ist_elsevier.yaml`** — Information and Software Technology (Elsevier) — Q1 Software / Q2 Information Systems; hybrid APC USD 3.390; **Tier 3**. Política editorial declara explicitamente: *"the premiere outlet for systematic literature studies in software engineering"* — venue Q2-adjacente mais alinhado à ferramenta para SE.
- **`jss_elsevier.yaml`** — Journal of Systems and Software (Elsevier) — Q1 Software / Q2 Hardware/IS; hybrid APC USD 3.690; **Tier 3**.
- **`peerj_cs.yaml`** — PeerJ Computer Science — Q2 SJR estrito CS misc; fully OA APC USD 1.595; **Tier 2** (publisher comunitário OA).
- **`ieee_access.yaml`** — IEEE Access — Q1 Engineering misc / Q2 CS Applications; fully OA APC USD 1.995–2.345; **Tier 2/Tier 3 borderline**.

### Modificado — Compliance engine (`scripts/compliance/engine.py`)

- `_load_venue_profile` e `list_known_venues` agora carregam de **6 pastas**: `venues_a1_br`, `venues_a3_br`, `venues_b1_br`, `venues_q1_int`, `venues_q2_int` (novo), `venues_fallback_br`. Ranqueamento por tier (Decisão 14) preservado.

### Schema sem alteração

Todos os 11 perfis Q2 INT validam contra o schema da v2.2.2 sem necessidade de extensão.

### Testes

53/53 passam em ~4.25s:
- 47 da regressão acumulada v2.0–v2.3.0
- 6 novos da v2.4.0:
  - `test_v24_q2_int_folder_has_11_profiles` (contagem de perfis)
  - `test_v24_q2_int_coverage_meets_3_per_area` (≥3 em Edu, Saú, CS/SE/Eng)
  - `test_v24_all_q2_int_have_quartile_metadata` (todos têm SJR ou JCR declarado)
  - `test_v24_q2_int_tier_distribution` (≥1 Tier 1, ≥2 Tier 2, ≥4 Tier 3)
  - `test_v24_rlae_usp_is_brazilian_q2_int_tier_1_anchor` (verifica RLAE como anchor)
  - `test_v24_engine_loads_q2_int_venues` (engine reconhece nova pasta; total 68 venues)

### Honestidade — limitações reconhecidas

- **3 dos 11 perfis Q2 INT são Q1 SJR estrito** (ETHE, IST, JSS) e foram incluídos em venues_q2_int/ por classificação cruzada (Q2 em subáreas) ou por serem casos especiais (ETHE = único Q1 diamond OA). As notes de cada perfil declaram isso. A **Decisão 16** torna essa convenção explícita: o quartil real é o que está em metadata.
- **Q2 INT depende fortemente de Tier 3**: 5 dos 11 perfis (45%) são Springer/Elsevier hybrid alto-custo (>USD 1.500). Apenas RLAE e ETHE são Tier 1. Isso reflete a estrutura do mercado editorial internacional Q2, não falha do catálogo.
- **Política de fee waiver e Research4Life**: BMC Medical Education é Tier 3 sem waiver e Tier 2 efetivo com waiver Springer Nature (Brasil é elegível em alguns programas). A ferramenta deve apresentar isso como propriedade dependente do contexto institucional do usuário.

### Cobertura matricial total após v2.4.0 (catálogo completo)

**68 perfis de venue** distribuídos em 6 pastas. Distribuição por área-mãe Sucupira × estrato:

| Área-mãe BR | A1 | A2 | A3 | B1 | Subtotal BR |
|---|---|---|---|---|---|
| Educação | 3 | 3 | 5 | 3 | 14 |
| QR1-Vida+Saúde | 1 | 3 | 4 | 4 | 12 |
| QR1-Exatas+Tec | 0 | 12 | 2 (gap Decisão 15) | 3 | 17 |
| **Total BR** | **4** | **18** | **11** | **10** | **43** |

Mais **14 Q1 INT** (em venues_q1_int/) e **11 Q2 INT** (em venues_q2_int/). Total: **68 perfis**.

### Roadmap v2.x → próximas etapas

- **Etapa 4b** (após v2.4): validação empírica com 3-6 casos reais documentados + comparação com baselines (Editorial Manager, ScholarOne, Rayyan, ASReview, JANE, B!SON). Sem casos reais, qualquer Tools Paper sobre a ferramenta continua especulativo.
- **Etapa 5** (após 4b): retomar `references/draft/PUBLISHABLE_ASPECTS_ANALYSIS.md` com base empírica concreta. Decidir se há bom motivo para escrever artigo; se não, registrar e seguir.

A v2.4.0 fecha o ciclo de catalogação declarado no roadmap original v2.x. A próxima sessão muda de natureza: **deixa de ser expansão de catálogo e passa a ser validação empírica**.

---

## [2.3.0] — 2026-05-03

Expansão progressiva do catálogo conforme roadmap declarado: ≥3 venues A3 BR e ≥3 venues B1 BR diamond OA por área-mãe Sucupira (Educação, QR1-Vida+Saúde, QR1-Exatas+Tecnológicas). Base documental fornecida pela pesquisa "Qualis A3, B1 BR Diamond OA e Q2 Internacional para a Ferramenta `ignorantia`" (Etapa 1 da estratégia consolidada de v2.3-v2.4-Etapa 4b).

### Adicionado — Decisão 15: gap estrutural em Exatas/Tec A3 (extensão coerente da Decisão 14)

A Pesquisa Qualis 2021-2024 documentou que a oferta brasileira A3 diamond OA em CS/Engenharias estritas comporta apenas **2 venues Tier 1 puros** (POPE/SOBRAPO + RBRH/ABRH) — RBIE, embora seja diamond OA da SBC, é catalogada na área-mãe Sucupira **Educação** (Computing Education), não em Exatas/Tec. Mesmo padrão estrutural diagnosticado na Decisão 14 para A2.

A Decisão 15 estabelece:

- **Meta A3 BR por área-mãe**: ≥3 em Educação e Saúde; **≥2** em QR1-Exatas+Tecnológicas com gap declarado.
- **Cobertura efetiva por subárea estrita CS/Eng**: 2 Tier 1 (POPE, RBRH) + fallbacks tier-2/3 já catalogados na v2.2.2 (LAJSS, MR como tier-2; JCAES, BBMS, CAM, SJMS, BJ Physics, BJPS como tier-3).
- O usuário escrevendo SLR em CS/Eng A3 estrito recebe ranqueamento honesto: 2 Tier 1 puros primeiro, depois fallbacks.

Padrão coerente com Decisão 14 e com a recomendação da Pesquisa Qualis CAPES de tratar QR1-Vida+Saúde+Exatas+Tec como bucket único para fins de calibração.

### Adicionado — 17 perfis novos em duas pastas

**`venues_a3_br/` (7 novos + 4 movidos = 11 perfis):**

*A3 Educação (4):*
- **`edufoco_uemg.yaml`** — Revista Educação em Foco (UEMG) — A3 CONFIRMADO (declaração editorial explícita); diamond OA portal UEMG.
- **`rdes_ufmg.yaml`** — Revista Docência do Ensino Superior (UFMG) — A3 CONFIRMADO (página oficial); diamond OA portal UFMG.
- **`ccedes_unicamp.yaml`** — Cadernos CEDES (CEDES/Unicamp) — A3 PROVÁVEL; SciELO Brasil; diamond OA.
- **`aval_raies.yaml`** — Avaliação: Revista da Avaliação da Educação Superior (RAIES) — A3 PROVÁVEL; SciELO Brasil; diamond OA.

*A3 Saúde (4):*
- **`ape_unifesp.yaml`** — Acta Paulista de Enfermagem (UNIFESP) — A3 PROVÁVEL (rebaixamento técnico de A1 sob régua QR1 2021-2024); diamond OA SciELO+UNIFESP.
- **`spmj_apm.yaml`** — São Paulo Medical Journal (APM) — A3 PROVÁVEL; diamond OA SciELO; PRISMA explícito.
- (mais 2 movidos abaixo)

*A3 CS/Eng (3):*
- **`rbrh_abrh.yaml`** — Revista Brasileira de Recursos Hídricos (ABRH) — A3 PROVÁVEL; diamond OA SciELO.
- (mais 2 movidos abaixo)

**`venues_b1_br/` (10 perfis novos):**

*B1 Educação (3):*
- **`ed_emancipacao_ufma.yaml`** — Revista Educação e Emancipação (UFMA) — B1 PROVÁVEL; diamond OA portal UFMA.
- **`holos_ifrn.yaml`** — HOLOS (IFRN) — B1 PROVÁVEL (rebaixamento esperado de A3 2017-2020 pela densificação 2021-2024); diamond OA portal IFRN.
- **`linhas_criticas_unb.yaml`** — Linhas Críticas (UnB) — B1 PROVÁVEL; SciELO + portal UnB; diamond OA.

*B1 Saúde (4):*
- **`tce_ufsc.yaml`** — Texto & Contexto Enfermagem (UFSC) — B1 PROVÁVEL (rebaixamento técnico de A2 sob QR1); diamond OA SciELO.
- **`ean_ufrj.yaml`** — Escola Anna Nery (UFRJ) — B1 PROVÁVEL; diamond OA SciELO+UFRJ.
- **`saude_sociedade_usp.yaml`** — Saúde e Sociedade (USP/ABRASCO) — B1 PROVÁVEL; diamond OA SciELO.
- **`interface_unesp.yaml`** — Interface — Comunicação, Saúde, Educação (UNESP-Botucatu) — B1 PROVÁVEL; diamond OA SciELO.

*B1 CS/Eng (3, todos via SBC OpenLib):*
- **`jidm_sbc.yaml`** — Journal of Information and Data Management (SBC) — B1 confirmado 2017-2020 + provável manutenção; diamond OA SOL.
- **`jserd_sbc.yaml`** — Journal of Software Engineering Research and Development (SBC) — B1 PROVÁVEL; diamond OA SOL; aceita SLRs explicitamente.
- **`jis_sbc.yaml`** — Journal on Interactive Systems (SBC) — B1 PROVÁVEL (ascenso de B2); diamond OA SOL.

### Modificado — 4 perfis legados recalibrados (movidos de `venues_a1_br/` para `venues_a3_br/`)

A Pesquisa nova encontrou divergências entre estratos catalogados em v2.2.x e o quadriênio 2021-2024:

- **`rsp_usp`**: A1 → A3 (era A3 em 2017-2020; CiteScore ~3.5; SJR Q2)
- **`csc_abrasco`**: A1 → A3 (comunicado oficial ABRASCO 2019 declara A3)
- **`rbie_sbc`**: B1 → A3 (página oficial declara A3 2021-2024 — CONFIRMADO)
- **`pope_sobrapo`**: A2 → A3 (trajetória B1/B2; CiteScore ~1.4)

Cada perfil recebeu nota explícita **"v2.3 RECALIBRAÇÃO"** registrando o motivo da mudança e a evidência documental. Auditável.

### Modificado — Compliance engine (`scripts/compliance/engine.py`)

- `_load_venue_profile` e `list_known_venues` agora carregam de **5 pastas**: `venues_a1_br`, `venues_a3_br` (novo), `venues_b1_br` (novo), `venues_q1_int`, `venues_fallback_br`. Ranqueamento por tier (Decisão 14) preservado.

### Testes

47/47 passam em ~3.6s:
- 41 da regressão acumulada v2.0–v2.2.2 (com ajustes para refletir movimentação de pope_sobrapo)
- 6 novos da v2.3.0:
  - `test_v23_folders_exist_and_have_correct_counts` (11 + 10 perfis)
  - `test_v23_a3_br_coverage_meets_3_per_area_with_declared_gap` (≥3 Edu+Saú; ≥2 Exatas com gap declarado)
  - `test_v23_b1_br_coverage_meets_3_per_area` (≥3 nas 3 áreas)
  - `test_v23_all_a3_b1_profiles_are_diamond_oa_brazilian` (21 perfis Tier 1 puros)
  - `test_v23_recalibrated_venues_carry_v23_note` (4 perfis com nota explicativa)
  - `test_v23_engine_loads_a3_and_b1_venues` (engine reconhece novas pastas)

### Honestidade — o que NÃO mudou

- **Estratos "PROVÁVEIS"**: 17 dos 21 perfis A3+B1 ainda dependem de **validação Sucupira por ISSN** para confirmar estrato 2021-2024 — o catálogo é melhor estimativa baseada em (a) trajetória 2017-2020, (b) métricas bibliométricas atuais, (c) indexação SciELO/DOAJ ativa, e (d) ausência de comunicado de queda. Cada perfil declara o status de evidência nas notes. A `ignorantia` deve apresentar isso ao usuário sem maquiar.
- **Q2 INT continua faltante**: a Etapa 1 (pesquisa) já entregou os 12 candidatos Q2 INT — implementação fica para v2.4 conforme roadmap.
- **Validação empírica continua faltante**: Etapa 4b (casos reais + comparação com baselines: Editorial Manager, ScholarOne, Rayyan, ASReview, JANE, B!SON) será depois da v2.4.

### Próximas releases

- **v2.4**: 12 perfis Q2 INT (4 por área-mãe) + estabilização. Pesquisa-base já entregue.
- **Etapa 4b** (após v2.4): validação empírica com 3-6 casos reais + comparação com baselines.
- **Etapa 5** (após 4b): retomar `PUBLISHABLE_ASPECTS_ANALYSIS.md` com base empírica concreta.

### Total de perfis e cobertura matricial após v2.3.0

**57 perfis catalogados** (era 40 na v2.2.2; +17 = 21 novos − 4 movidos):

| Área-mãe | A1 | A2 | A3 | B1 | Total BR |
|---|---|---|---|---|---|
| Educação | 3 | 3 | 5 | 3 | **14** |
| QR1-Vida+Saúde | 1 | 3 | 4 | 4 | **12** |
| QR1-Exatas+Tec | 0 | 12 | 2 (gap Decisão 15) | 3 | **17** |

Mais 14 Q1 INT já catalogados.

---

## [2.2.2] — 2026-05-03

Patch de coerência entre meta declarada e ecossistema editorial brasileiro real. Resolve débito identificado ao final da v2.2.1: o agrupamento `QR1-Exatas+Tecnologicas` tinha apenas 3 venues tier-1 (1 por subárea estrita: CC, Eng, Mat), insuficiente para um pesquisador escrevendo SLR em qualquer subárea específica.

### Adicionado — Decisão 14: vocabulário de tiers OA-first

A pesquisa `Venues_Qualis_A2_Brasileiros_Diamond_OA_em_Exatas_e_Tecnológicas` em `/mnt/project/` documenta que o ecossistema editorial brasileiro em Exatas estritas **estruturalmente não contém** ≥3 venues simultaneamente diamond OA + publisher 100% nacional + aceita SLR em cada subárea. A v2.2.2 introduz vocabulário de 3 tiers para nomear honestamente a realidade:

- **Tier 1** — diamond OA: sem APC, publisher 100% nacional ou cooperativa científica. Comportamento default semântico para perfis sem `fallback_tier` explícito (mantém compat com 32 perfis pré-v2.2.2).
- **Tier 2** — APC declarado modesto (≤USD 2.000), publisher comunitário científico (sociedade nacional via SciELO).
- **Tier 3** — Springer/Elsevier hybrid alto-custo (>USD 1.500) ou subscription model.

A meta original "≥3 venues por área" passa a ser interpretada como "≥3 venues **tier-1** por área-mãe Sucupira (QR1-Vida+Saúde+Exatas+Tec, Educação, etc.) com fallbacks tier-2/3 declarados quando o ecossistema não suporta tier-1 puro por subárea estrita". Coerente com a Pesquisa Qualis CAPES 2021-2024, que recomenda explicitamente agrupar Vida+Saúde+Exatas+Tec sob bucket único QR1 para fins de calibração.

### Adicionado — 8 perfis fallback em `venues_fallback_br/`

**Tier 2 (APC modesto, publisher comunitário BR):**
- **`lajss_abcm.yaml`** — Latin American Journal of Solids and Structures (ABCM) — A2 prov. Eng. I; APC EUR 600-1.200 (~USD 650-1.300); via SciELO.
- **`mr_abm.yaml`** — Materials Research (ABM) — A2 prov. Eng. II/Materiais; APC USD 1.800; via SciELO.

**Tier 3 (Springer hybrid alto-custo ou subscription):**
- **`jcaes_sba_springer.yaml`** — Journal of Control, Automation and Electrical Systems (SBA + Springer) — A2 prov. Eng. IV; APC USD 3.460 hybrid.
- **`bbms_sbm_springer.yaml`** — Bulletin of the Brazilian Mathematical Society (SBM + Springer) — A2 prov. Mat; APC USD 3.290 hybrid.
- **`cam_sbmac_springer.yaml`** — Computational and Applied Mathematics (SBMAC + Springer) — A2 prov. Mat; APC USD 3.290 hybrid; companion ao TCAM diamond.
- **`sjms_usp_springer.yaml`** — São Paulo Journal of Mathematical Sciences (IME-USP + Springer) — A2/A3 prov. Mat; APC USD 3.290 hybrid.
- **`bjphys_sbf_springer.yaml`** — Brazilian Journal of Physics (SBF + Springer) — A2 prov. Astronomia/Física; APC USD 3.290 hybrid; distinto da RBEF (diamond, área-mãe Ensino).
- **`bjps_abe_ims.yaml`** — Brazilian Journal of Probability and Statistics (ABE + IMS) — A2 prov. Mat/Estatística; subscription model.

Cobertura efetiva agora alcançável por subárea (com declaração honesta de tier):
- **Ciência da Computação**: 3 tier-1 BR (JISA, JBCS, ROCS via SBC) — meta atendida em tier-1 puro.
- **Engenharias**: 1 tier-1 (POPE/SOBRAPO) + 2 tier-2 (LAJSS, MR) + 1 tier-3 (JCAES) = 4 opções com tiers explícitos.
- **Matemática/Estatística/Física**: 1 tier-1 (TCAM/SBMAC) + 4 tier-3 (BBMS, CAM, SJMS, BJPhys, BJPS) = 5 opções com tiers explícitos.

### Modificado — Compliance engine (`scripts/compliance/engine.py`)

- `VenueAssessment` ganhou campo `fallback_tier: int = 1` (default 1 mantém compat com perfis sem flag).
- `VenueComplianceEngine._load_venue_profile` e `list_known_venues` agora carregam de `venues_fallback_br/` além de `venues_a1_br/` e `venues_q1_int/`.
- **Ranqueamento de alternativas** mudou de `sort by aggregate_score DESC` para `sort by (fallback_tier ASC, aggregate_score DESC)`. Tier-1 sempre emerge antes de tier-2 antes de tier-3, mesmo que tier-3 tenha score maior. Implementa Decisão 14 operacionalmente.

### Modificado — JSON Schema do perfil de venue

- Em `metadata`, novos campos opcionais:
  - `fallback_tier`: enum `[1, 2, 3, null]`.
  - `apc_usd_range_min` / `apc_usd_range_max`: para APCs declarados como faixa (ex.: LAJSS EUR 600-1.200).
  - `apc_currency_original`: ISO 4217 (USD, EUR, GBP, BRL).
  - `apc_amount_original`: valor literal como declarado pelo publisher.
- `controlled_vocabulary` enum estendido com `MSC2020` (Mathematics Subject Classification) e `PACS` (Physics and Astronomy Classification Scheme), necessários para perfis de Mat e Física.
- `citation_style.format` enum estendido com `amsplain` e `numeric`.
- `authorship.orcid_required` enum estendido com `optional` (entre `corresponding_only` e `none`).

Todas as extensões são aditivas — nenhum perfil pré-v2.2.2 quebra.

### Testes

41/41 passam em ~2.9s:
- 33 da regressão acumulada (v2.0 + v2.1 + v2.1.1 + v2.2.0 + v2.2.1)
- 6 da v2.2.2 estrutura (8 perfis fallback / tier explícito / APCs coerentes / contagem 40)
- 2 da v2.2.2 comportamento (engine ranqueia por tier; engine lista os 40 venues)

### Honestidade — o que NÃO mudou

A v2.2.2 **não inventa venues que não existem**. A escassez estrutural de venues A2 BR diamond OA em Exatas estritas continua existindo — a v2.2.2 apenas dá vocabulário (tiers) para apresentar honestamente os fallbacks que a pesquisa documental já catalogou. A meta "tier-1 puro por subárea estrita" continua estruturalmente inalcançável em Eng. e Mat./Stat./Fís.

### Próximas releases

- **v2.3**: ≥3 A3 BR e ≥3 B1 BR por área-mãe Sucupira. O vocabulário de tiers introduzido aqui antecipa o trabalho — A3/B1 incluem proporcionalmente mais venues hybrid Springer/Elsevier.
- **v2.4**: ≥3 Q2 INT por área + estabilização.

---

## [2.2.1] — 2026-05-02

Segunda sub-rodada da expansão progressiva de venues. Foco: ≥3 venues Qualis A2 BR diamond OA por área-mãe (Educação, QR1-Vida+Saúde, QR1-Exatas+Tecnológicas), conforme escopo originalmente previsto para v2.2.

### Adicionado — 9 venues A2 BR diamond OA (publisher 100% nacional)

**Educação (3 novos):**
- **`emaberto_inep.yaml`** — Em Aberto (Inep/MEC) — A2 confirmado quadriênio 2021-2024 (comunicado oficial Inep, jan/2026); diamond OA, CC BY-NC; ABNT NBR 6023; aceita integrative/scoping/narrative/qualitative/mapping reviews.
- **`rbaad_abed.yaml`** — Revista Brasileira de Aprendizagem Aberta e a Distância (ABED) — A2 confirmado (declaração explícita home da revista); diamond OA CC BY 4.0; foco em tecnologias educacionais e EaD.
- **`rpem_unespar.yaml`** — Revista Paranaense de Educação Matemática (Unespar) — A2 confirmado (comunicado oficial Unespar/PRPPG, jan/2026; ascendeu A3 → A2); diamond OA; aceita Petersen-style mapping studies e PRISMA-style SR.

**Saúde QR1-Vida+Saúde (3 novos):**
- **`reben_aben.yaml`** — Revista Brasileira de Enfermagem (ABEn Nacional) — A2 confirmado (comunicado oficial ABEn, jan/2026); diamond OA; trilíngue PT/EN/ES; ScholarOne; PRISMA-2020 obrigatório; PROSPERO blocking.
- **`reeusp_usp.yaml`** — Revista da Escola de Enfermagem da USP — A2 provável (era A2 em 2017-2020; ISSN 1980-220X; confirmação Sucupira mandatória); diamond OA; ScholarOne; PRISMA-2020 obrigatório.
- **`rbe_abrasco.yaml`** — Revista Brasileira de Epidemiologia (Abrasco) — A2 provável (era A2/A1 em 2017-2020 dependendo da subárea; ISSN 1980-5497); diamond OA via SciELO; PRISMA-2020 + MOOSE obrigatórios.

**Exatas/Tec QR1-Exatas+Tecnológicas (3 novos):**
- **`jisa_sbc.yaml`** — Journal of Internet Services and Applications (SBC) — A2 provável (documento Qualis CC IC/Unicamp 2021: "JISA é naturalmente A2"; saiu da Springer em 2023, agora 100% SBC OpenLib); diamond OA pós-migração SOL/SBC; JCR IF 2,4; SJR Q1 (Computer Networks); aceita surveys e mapping studies.
- **`pope_sobrapo.yaml`** — Pesquisa Operacional (SOBRAPO) — A2 provável (era A2 em Eng. III no quadriênio anterior; ISSN 1678-5142); diamond OA via SciELO; declaração editorial explícita aceita "revisões bibliográficas e trabalhos sobre metodologia da PO" — único venue brasileiro de Engenharias com aceite explícito de revisões.
- **`tcam_sbmac.yaml`** — Trends in Computational and Applied Mathematics (SBMAC) — A2/A3 provável em Mat./Prob.&Estat. (ISSN 2676-0029); diamond OA confirmado por declaração explícita da revista ("does not charge submission, article processing, or publication fees").

### Honestidade declarada — Qualis 2021-2024 confirmados vs prováveis

Dos 9 novos venues, **4 têm A2 totalmente confirmado** via comunicados oficiais 2026 (Em Aberto/Inep, RBAAD/ABED, RPEM/Unespar, REBEn/ABEn). Os outros **5 têm A2 fortemente provável** baseado em (a) histórico estável A2 no quadriênio 2017-2020; (b) manutenção/melhoria de indicadores bibliométricos no período 2019-2023 usado pela CAPES; (c) ausência de comunicados de queda. **Confirmação Plataforma Sucupira por ISSN é mandatória** antes de uso operacional. Cada perfil declara o status de confirmação no campo `notes`.

### Cobertura efetiva por área Qualis BR após v2.2.1

| Área | A1 | A2 | B1 |
|---|---|---|---|
| Educação | 3 | **6** (3 antigos + 3 novos) | 1 |
| QR1-Vida+Saúde | 3 | **3** (todos novos) | 0 |
| QR1-Exatas+Tecnológicas | 0 | **5** (2 antigos + 3 novos) | 0 |

Meta v2.2 (≥3 A2 BR por área) atingida nas três áreas.

### Gap estrutural reconhecido — Exatas/Tec estritas

Pesquisa profunda confirmou cenário estrutural: o ecossistema editorial brasileiro NÃO contém ≥3 venues A2 simultaneamente diamond OA, publisher 100% nacional, aceitando revisões sistemáticas, em **cada subárea** de Exatas/Tec (Computação, Engenharias, Matemática, Física estritas). A v2.2.1 atinge a meta agregando subáreas dentro do enum `QR1-Exatas+Tecnologicas` (que cobre todas conjuntamente, conforme schema atual). Para granularidade por subárea estrita, candidatos de fallback foram identificados e documentados:
- LAJSS (ABCM, Eng. I) — A2 provável MAS APC EUR 600-1.200
- JCAES (SBA + Springer, Eng. IV) — A2 provável MAS Springer hybrid APC ~$3.460
- ROCS (SBC) — diamond, escopo SLR perfeito MAS Qualis ainda não atribuído
- Esses fallbacks ficam disponíveis para v2.3+ caso meta de granularidade por subárea seja adicionada.

### Modificado — JSON Schema

- `controlled_vocabulary` enum expandido para incluir `DeCS` (Descritores em Ciências da Saúde, BVS/BIREME) — necessário para os 3 perfis novos de Saúde.

### Testes

33/33 passam em 4.13s:
- 2 da regressão v2.0
- 22 da v2.1.0
- 2 da v2.1.1
- 5 da v2.2.0 (atualizado teste de contagem para 32 perfis totais)
- 4 da v2.2.1:
  - `test_v221_nine_new_a2_br_venues_exist`
  - `test_v221_a2_br_coverage_by_area` (≥3 A2 BR por cada uma das 3 áreas)
  - `test_v221_all_new_venues_are_diamond_oa_brazilian`
  - `test_v221_total_venue_count_is_32`

### Próximas releases

- **v2.3**: ≥3 A3 BR e ≥3 B1 BR por área
- **v2.4**: ≥3 Q2 INT por área + estabilização

---

## [2.2.0] — 2026-05-02

Primeira sub-rodada da expansão progressiva de venues prevista para v2.2-v2.4. Foco: fechar o gap crítico de cobertura OA internacional identificado em auditoria pós-v2.1.0.

### Adicionado — 3 venues OA Internacionais

Antes da v2.2.0, **apenas Campbell era Q1 INT fully OA** entre os 11 perfis internacionais. Os 10 demais eram hybrid com APC alto (NEJM, Lancet, BMJ, BMJ-Cochrane DSR, IEEE TSE, ACM TOSEM, EMSE Springer, Elsevier ERR, Sage RER, Wiley RSM). Para um autor brasileiro sem orçamento institucional, isso significava **escolher entre Campbell ou pagar**.

A v2.2.0 adiciona 3 venues que cobrem áreas complementares:

- **`plos_one.yaml`** — PLOS ONE. APC $1,695 (2026), megajournal multi-área (saúde, ciências naturais, sociais), peer review tradicional, política consciente de pricing restraint do publisher nonprofit. APC locked at submission date. Aceita SR-strict, Scoping, Rapid, Integrative, Realist, Meta-analysis, Qualitative Synthesis. **Fecha gap em saúde geral / multi-disciplinar**.
- **`f1000research.yaml`** — F1000Research. APC $1,595 (2026), publicação imediata + peer review aberto pós-publicação. Aceita os mesmos modos de PLOS + Software Paper + Position Paper + Technical Report. Reviewers nomeados publicamente. Útil para Software Tool Articles (alternativa a JOSS), SRs com publicação rápida, Registered Reports (50% off Stage 2), e null findings. **Fecha gap em multi-disciplinar com modelo de transparência radical**.
- **`frontiers_education.yaml`** — Frontiers in Education. APC ~$2,200 (1950 CHF, 2026), focado em educação. Aceita Original Research, SR, Methods, Review, Policy and Practice Reviews, Hypothesis and Theory, Registered Report, Study Protocol, Policy Brief. **Fecha gap em educação INT**.

Brasil é classificado como upper-middle income pelo World Bank — autores brasileiros **NÃO recebem waiver automático** dos 3 venues, mas podem aplicar via fee support program (Frontiers, F1000) ou institutional partnerships (PLOS All-In, Read & Publish). Isso está declarado honestamente em cada perfil no campo `apc_waivers`.

### Modificado — JSON Schema do perfil de venue

- `submission_system` enum expandido para incluir `f1000_native` e `frontiers_native` (vs antes só `nejm_native`, `lancet_native`, `other`).
- `cdsr.yaml` corrigido: `file_format.accepted` mudado de `[other]` (inválido contra schema) para `[docx]` com nota explicativa sobre RevMan. Bug pré-existente da v2.0, agora corrigido.

### Testes

29/29 passam em 4.72s:
- 2 da regressão v2.0 (cenários canônicos preservados)
- 22 da v2.1.0 (modos, layers, E16, schema, files)
- 2 da v2.1.1 (source_tier nos scripts, ramificação por modo na auto-correção)
- 5 da v2.2.0:
  - `test_three_new_oa_int_venues_exist`
  - `test_three_new_oa_int_venues_are_fully_oa`
  - `test_three_new_oa_int_venues_have_apc_declared`
  - `test_three_new_oa_int_venues_validate_against_schema`
  - `test_all_venue_profiles_validate_against_schema` (23 perfis, regressão geral)

### Pendente para próximas sub-rodadas v2.2.x e v2.3-v2.4

A meta original da v2.2 era também **≥3 A2 BR por área (Educação, Saúde, Exatas/Tec)**. Não entregue nesta sub-rodada por opção consciente: Qualis 2025-2028 está em transição (CAPES anunciou em 2026 o fim da classificação conceitual), e identificar 9 venues A2 BR com qualis_stratum verificável para cada um exige pesquisa caso-a-caso cuidadosa para evitar invenção. Será feito em sessão dedicada como v2.2.1.

Sequência atualizada das próximas releases:
- **v2.2.1**: ≥3 A2 BR por área (9 venues novos, pesquisados individualmente)
- **v2.3**: ≥3 A3 BR e ≥3 B1 BR por área
- **v2.4**: ≥3 Q2 INT por área + estabilização

### Observação editorial — Qualis em transição

CAPES anunciou em janeiro/2026 (no resultado do quadriênio 2021-2024) que **a classificação conceitual A1-C do Qualis Periódicos será descontinuada para o quadriênio 2025-2028**. Isso afeta como os perfis YAML referenciam estratos. Os perfis atuais usam o quadriênio 2021-2024 (último válido) como referência canônica. Quando o novo modelo de avaliação CAPES for publicado, será necessário ciclo de migração — registrado como gap em `references/equator-monitoring.md` para revisão futura.

---

## [2.1.1] — 2026-05-02 (patch)

Patch que fecha dois débitos identificados em auditoria pós-release da v2.1.0:

### Corrigido — `references/auto-correction-policy.md` agora ramifica por `review_type`

A v2.1.0 entregou 10 modos em três camadas hierárquicas (Primária / Secundária / Terciária), mas a política de auto-correção continuava assumindo implicitamente que todo manuscrito era PRISMA-like. v2.1.1 corrige:

- Nova seção "Aplicabilidade por modo (v2.1)" no topo do documento.
- Tabela explícita de quais verificações se aplicam a cada camada (PRISMA flow, checklist PRISMA-2020, busca em ≥3 bases, `extraction.csv`, etc. — só aplicáveis a modos Primários e Terciário).
- Tabela de verificações **específicas do guideline** para cada modo Secundário (Software/Position/Technical/White Paper).
- Para o eixo Conteúdo, "factualidade" agora é definida por modo: contra `extraction.csv` em modos Primários; contra material fornecido pelo usuário em modos Secundários.
- Heurística de fallback para manuscritos legacy sem `review_type` declarado: tenta inferir, emite warning, aplica política mais conservadora.

### Corrigido — Os 5 scripts de busca pré-existentes agora declaram `source_tier`

Em v2.1.0, criou-se o orquestrador `search_orchestrator.py` (que respeita tiers), mas os 5 scripts individuais (`search_arxiv.py`, `search_crossref.py`, `search_dblp.py`, `search_scielo.py`, `search_semantic_scholar.py`) não receberam metadado de tier.

Em v2.1.1, cada um dos 5 scripts agora grava o campo `"source_tier"` em (a) cada item retornado e (b) no envelope final do JSON. Mapeamento aplicado:

| Script | source_tier |
|---|---|
| `search_arxiv.py` | tier1 (full-text OA) |
| `search_dblp.py` | tier1 (metadados livres + full-text via arXiv) |
| `search_scielo.py` | tier1 (full-text OA Latam) |
| `search_crossref.py` | tier2 (metadados livres; full-text varia) |
| `search_semantic_scholar.py` | tier2 (metadados + abstracts livres; full-text varia) |

Adição é puramente aditiva — sem mudança de interface CLI, sem quebra de retrocompatibilidade do JSON de saída.

### Testes

24/24 passam em 3.26s:
- 22 herdados da v2.1.0
- 2 novos da v2.1.1: `test_all_search_scripts_declare_source_tier`, `test_auto_correction_policy_mentions_three_layers`

### Observação sobre processo

Esses dois itens estavam no plano de execução original da v2.1.0 mas ficaram em débito por falha de execução, não por decisão consciente. Auditoria item-por-item solicitada pelo usuário identificou as omissões.

---

## [2.1.0] — 2026-05-02

### Adicionado — 6 modos novos do ghostwriter (4 → 10) em hierarquia tripla

**Camada Primária (você sozinho + busca autônoma OA):**
- Modo 9: AI-Assisted Integrative Review (Whittemore-Knafl 2005 + Toronto-Remington 2020) — 16 itens de checklist
- Modo 10: AI-Assisted Realist Review (RAMESES II — Wong et al. 2013, BMC Med 11:21) — 19 itens

**Camada Secundária (você sozinho + material que você fornece):**
- Modo 5: Software Paper (JOSS-aligned, 15 itens)
- Modo 6: Position Paper / Theoretical Essay (Toulmin/Walton-inspired, 12 itens)
- Modo 7: Technical Report (ANSI/NISO Z39.18-2005 R2010, 14 itens)
- Modo 8: White Paper / Policy Brief (Brookings/RAND/Carnegie/ICCT-style, 13 itens)

**Camada Terciária (≥1 humano qualificado adicional, NÃO oferecido como default):**
- Modo 4: Systematic Review estrito (já existia em v2.0; reclassificado em v2.1)

### Adicionado — Política OA-first formalizada (3 tiers)

- `references/databases/oa-tiers.md` — documento canônico com bases por tier
- `scripts/searches/search_orchestrator.py` — orquestrador com disclosure pré-/pós-busca

### Adicionado — Padrão de venues OA-first com alternativas explicadas

Cada modo declara venue padrão $0 + 2-3 alternativas com APC declarado:
- Software Paper: padrão JOSS ($0); alt F1000Research, SoftwareX, IEEE Software
- Position Paper: padrão Zenodo + preprint OA ($0); alt AI&Society, CACM, IEEE Insights
- Technical Report: padrão Zenodo / arXiv ($0); alt NIST Tech Series, OSF, repositório
- White Paper: padrão Zenodo ($0); alt OSF, SciELO Preprints, SSRN — todos $0
- Integrative Review: padrão Zenodo + SciELO Preprints ($0); alt CSP, EP USP (A1 BR $0)
- Realist Review: padrão Zenodo ($0); alt CSP, EP USP, BMC Medicine, Implementation Science

### Adicionado — Documentação

- `references/modes/MODES_OVERVIEW.md` — panorama master dos 10 modos com hierarquia tripla, tabela comparativa em três layers, algoritmo de decisão sequencial
- `references/modes/mode-XX-*.md` — 10 perfis individuais detalhados em três layers
- `references/profiles/_guidelines/` — 6 perfis YAML de guidelines novas (whittemore-knafl, rameses-ii, software-paper-generic, position-paper-generic, ansi-niso-z3918, white-paper-generic) → 13 perfis ao total
- `assets/templates/modes/` — 6 templates HTML de modo novos → 10 templates ao total

### Modificado

- `scripts/assessor/eliminators.py`: constantes novas `VALID_REVIEW_TYPES_V21` (18 valores), `SYSTEMATIC_REVIEW_VALID_VALUES`, `REVIEW_TYPE_TO_LAYER` (mapa para 3 camadas). E16 estendido — bloqueia review_type fora do enum válido v2.1; mensagens de erro mencionam camada hierárquica.
- `references/profiles/_schema/venue_profile.schema.json`: enum `review_types_accepted` agora aceita 18 valores (vs 10 em v2.0); novo campo `recommended_for_layer` (primary | secondary | tertiary | all).
- `SKILL.md`: Decisões 10, 11 e 12 adicionadas. Decisão 1 atualizada. Regra crítica DECLARE atualizada com 18 valores. Description do frontmatter atualizada para mencionar v2.1.

### Decisões editoriais novas

- **Decisão 10**: Dez modos de saída em hierarquia tripla (Primária / Secundária / Terciária).
- **Decisão 11**: Política OA-first com 3 tiers de bases.
- **Decisão 12**: Padrão de venues OA-first com alternativas explicadas.

### Estimativa de tempo de produção

Adicionado campo `time_to_produce_estimate: "user_estimate_15min_unvalidated"` em todos os perfis de modo. Estimativa do usuário: ~15 minutos. Será refinado após casos reais documentados.

### Testes

22/22 passam em 2.61s:
- `tests/test_regression.py` (2/2): cenários canônicos preservados
- `tests/test_v21_modes.py` (20/20): contratos VALID_REVIEW_TYPES_V21, REVIEW_TYPE_TO_LAYER, comportamento E16 estendido, JSON Schema, existência de arquivos

### Gap conhecido a fechar em v2.2

Cobertura OA INT continua pobre — apenas Campbell é Q1 INT fully OA. v2.2 adicionará PLOS ONE, F1000Research, Frontiers como prioridade alta.

### Sequência das próximas releases v2.x

- **v2.2**: ≥3 A2 BR por área + fechar gap OA INT (PLOS ONE, F1000Research, Frontiers)
- **v2.3**: ≥3 A3 BR e ≥3 B1 BR por área + ≥3 Q2 INT por área
- **v2.4**: estabilização — completar coberturas + mitigações Cat B + opcional artigos sobre a ferramenta (apenas se metas batidas E houver bom motivo)

---

## [2.0.0] — 2026-05-02

### Sub-rodadas v2.0.x — fechamento de gaps + Tarefa 3 (mesma data)

**Gap 1 fechado** — Templates de modo:
- `assets/templates/modes/mode-scoping-review.md` (PRISMA-ScR + JBI Manual)
- `assets/templates/modes/mode-rapid-review.md` (PRISMA-RR + Cochrane RR Methods)
- `assets/templates/modes/mode-mapping-study.md` (Petersen 2015 + ACM SIGSOFT ESS-14)
- `assets/templates/modes/mode-systematic-review-strict.md` (PRISMA-2020 + 2 revisores obrigatórios)

**Gap 2 fechado** — Integração assessor v1 ↔ compliance v2:
- `scripts/unified_assessment.py`: produz relatório JSON unificado com Layer 1 (assessor v1: 16 eliminadores + rubric + audit + temperature) e Layer 2 (compliance v2: primary venue + dimensions + gaps + alternatives) + verdict agregado.

**Gap 3 fechado** — Eliminatório E16:
- `scripts/assessor/eliminators.py:check_e16_systematic_review_without_two_reviewers`
- Política: bloqueia manuscritos novos (com `review_type` declarado) que reivindicam "Systematic Review" sem evidência de 2 revisores humanos com kappa documentado. Manuscritos legacy (sem `review_type`) recebem warning, preservando regressão.
- Validado em 5 casos canônicos.

**Tarefa 3 entregue** — Análise de aspectos publicáveis:
- `references/draft/PUBLISHABLE_ASPECTS_ANALYSIS.md` (332 linhas)
- Diagnóstico de 7 aspectos potencialmente publicáveis (A-G), com critérios de inéditeza, validação atual, tipo de paper viável, venues realistas, gaps por aspecto.
- Posicionado como mapa para o futuro, NÃO plano imediato.
- Recomendação primária se houver bom motivo: JOSS (Journal of Open Source Software).
- Posição honesta: caminho mais defensável é publicar DEPOIS de uso real em produção (5-20 RS depositadas).

**Regressão preservada**: pytest tests/test_regression.py: 2/2 passa em 3.6s. Os 4 cenários canônicos (smoke=NÃO-CLASS, corpus18=B1, ghostwriter=SUB-B4, casoH=B3) continuam validando.

---

## [2.0.0] — 2026-05-02 (versão original do dia)


### Adicionado

- **Sistema de avaliação por requisitos formais de venues** — núcleo da v2.0. Engine determinístico que compara o manuscrito contra perfis YAML de 20 venues representativos.
- **20 perfis de venue iniciais** (`references/profiles/`):
  - 9 venues brasileiros (A1/A2/B1): Cadernos de Saúde Pública, Revista de Saúde Pública, Ciência & Saúde Coletiva, Educação e Pesquisa, Revista Brasileira de Educação, Cadernos de Pesquisa, JBCS/SBC, JISTEM, RBIE.
  - 11 venues Q1 internacionais: NEJM, The Lancet, BMJ, Cochrane DSR, IEEE TSE, ACM TOSEM, Empirical Software Engineering, Educational Research Review, Review of Educational Research, Campbell Systematic Reviews, Research Synthesis Methods.
- **JSON Schema draft-2020-12** para perfis de venue (`references/profiles/_schema/venue_profile.schema.json`).
- **6 perfis transversais de reporting guidelines** (`references/profiles/_guidelines/`): PRISMA-2020 (39 itens classificados por automation_level full/partial/none), PRISMA-S, PRISMA-ScR, PRISMA-RR, MECIR, Campbell-Standards, SIGSOFT-EMP-STANDARDS.
- **Engine de compliance em 7 estágios** (`scripts/compliance/`):
  - Stage 1: Parse & Normalize (HTML/TXT/JATS) → ManuscriptDocument
  - Stage 2: Hard Requirements Checking (length, abstract, citation style, declarations, ORCID, registration, language)
  - Stage 3: Reporting Guidelines Mapping (≥50% itens automatizáveis; resto flagged needs_human_review)
  - Stage 4: Scope Matching (TF-IDF cosine + thesaurus + citation overlap + anchor matching)
  - Stage 5: Aggregation (pesos: structural 0.25, reporting 0.30, declarations 0.15, citation 0.10, registration 0.10, scope 0.10)
  - Stage 6: Gap Prioritization (Priority = 0.5×severity + 0.3×venue_weight + 0.2×fix_cost⁻¹)
  - Stage 7: Multi-Venue Ranking
- **Gerador de pacote Zenodo** (`scripts/zenodo/`):
  - `ZenodoPackageBuilder` agrega 8 artefatos obrigatórios (prompt.md, model.txt, databases.txt, dois.csv, selecao_log.json, verificacao_dois.json, ai_disclosure.md, README.md) + opcionais.
  - Gera `reproducibility_manifest.yaml` com SHA-256 de cada arquivo.
  - Verificação automática de DOIs via Crossref REST API + OpenAlex + Retraction Watch (via OpenAlex `is_retracted` flag). Estados: `verified | not_found | retracted | invalid_format | unverified_no_network | error`.
- **Três modos de saída do ghostwriter** (Decisão 1):
  - `AI-Assisted Scoping Review` (default exploratório, segue PRISMA-ScR + JBI Manual)
  - `AI-Assisted Rapid Review` (default decisional, segue PRISMA-RR + Cochrane RR Methods)
  - `AI-Assisted Systematic Mapping Study` (default CS/SE, segue Petersen et al. 2015 + ACM SIGSOFT)
  - `Systematic Review` reservado APENAS a casos com 2 revisores humanos validados.
- **Dois modos de Forma** (Decisão 4): "Preprint/Zenodo" (normas área-padrão) vs "Venue-Specific" (normas do publisher).
- **Recomendação semi-automática de preprint server** (Decisão 3): mapeamento por área para EdArXiv/PsyArXiv/medRxiv/bioRxiv/arXiv/SSRN/SciELO Preprints/Research Square/LawArXiv/Humanities Commons.
- **Monitoramento EQUATOR Network** (`references/equator-monitoring.md`): 7 guidelines implementadas + 8 prioritárias não implementadas + 9 emergentes monitoradas (PRISMA-AI, TRIPOD-AI, CHART, CONSORT-AI, etc.).
- **Prompts estruturados Claude Chat** (`references/claude-chat-tasks/`): C7 (releitura semântica), C8 (originalidade real), C9 (qualidade linguística), C10+T4 (profundidade + agregação). Substituem na v2.0 o que serão modelos linguísticos na v3.0.
- **Documento de orientação ao usuário** (`references/user-guidance/post-deposit-actions.md`): 243 linhas documentando mitigações de Categoria B (vinculação bidirecional Revisão↔Changelog, auditoria periódica, open peer review pós-Zenodo) que não pertencem ao escopo do skill.
- **5 mitigações Categoria A obrigatórias de conflito de interesse** (Decisão 8) integradas ao SKILL.md como mandatórios:
  1. Pré-registro PROSPERO/OSF com timestamp anterior à decisão de design.
  2. Declaração CoI padronizada identificando projeto subjacente, tipo de relação, timing.
  3. Seção "Evidência contrária encontrada" obrigatória.
  4. Categorização `review_purpose` no metadado: `design_foundational | design_validation | design_correction | independent_inquiry`.
  5. Pacote reprodutibilidade Zenodo.

### Mudado

- **SKILL.md** atualizado de 353 para 473 linhas. Description do frontmatter ampliada para mencionar v2.0.
- **5 novas proibições críticas** adicionadas: nunca chamar de "systematic review" sem 2 revisores; nunca chamar de "living review" sem protocolo formal; nunca depositar Zenodo sem pacote completo; nunca omitir mitigações Categoria A.
- **6 novos mandatórios** adicionados: declarar `review_type`, declarar `review_purpose`, gerar pacote Zenodo via `scripts/zenodo/`, aplicar engine de compliance, apresentar recomendação de preprint server com confirmação humana.
- **Sprint Badge** explicitamente rotulado como **experimental/preview**. Calibração definitiva (regressiva SJR+JIF, n=1.600-3.200) é alvo da v3.0 no Cowork.
- **Whitepaper preliminar** (`references/draft/whitepaper-PRELIMINARY.md`) recebeu aviso explícito de rascunho. Substituição definitiva = Artigo 9 (Tools Paper) da série editorial após corpus expandido.

### Mantido

- **Compatibilidade total com cenários canônicos da v1**: pytest tests/test_regression.py passa 2/2 testes (regressão automática preservada). Os 4 cenários canônicos (smoke=NÃO-CLASS, corpus18=B1, ghostwriter=SUB-B4, casoH=B3) continuam produzindo os resultados gravados.
- Todos os componentes consolidados da v1.x (assessor, render_v2, slr_to_package, attest_phase_transition, generate_assessment, prisma_flow, deduplicate, render_manuscript, scripts/searches/*).

### Decisões editoriais incorporadas

| # | Decisão |
|---|---|
| 1 | Três modos de saída (Scoping/Rapid/Mapping/Systematic-com-evidência) |
| 2 | Pacote reprodutibilidade Zenodo obrigatório + verificação de DOIs |
| 3 | Preprint server semi-automático (gera, usuário submete) |
| 4 | Dois modos de Forma (Preprint/Zenodo vs Venue-Specific) |
| 5 | Monitoramento EQUATOR Network |
| 6 | "Living review" só com protocolo formal Cochrane/Campbell |
| 7 | Idiomas v2.0: EN primário + PT + ES; mandarim em v2.x+ |
| 8 | 5 mitigações Categoria A obrigatórias de CoI |
| 9 | Sprint Badge marcado como experimental/preview até v3.0 |

### Não incluído nesta versão (roadmap v3.0/Cowork)

- Classificador regressivo SJR+JIF (precisa corpus expandido n=1.600-3.200 SLRs reais).
- Embeddings semânticos (SPECTER2, SciBERT) para scope matching avançado.
- Integração com OPA/Rego para perfis hierárquicos publisher → família → revista.
- Suporte a mandarim (parsers CJK específicos).
- Series de 9 artigos publicáveis (Dataset Paper, Calibration, Tools Paper, etc.).

### Pesquisas conduzidas para fundamentar a v2.0

- **Pesquisa A** (artifact wf-bcb211b3): IEEE Publication Strategy — caminhos viáveis de publicação.
- **Pesquisa B** (artifact wf-ddbd1e6c): Qualis CAPES 2021-2024 — 49 áreas, 6 sub-grupos metodológicos.
- **Pesquisa C** (artifact wf-53572a5e): Sample Size Foundations — n total alvo 3.200, mínimo 1.600.
- **Pesquisa D1** (artifact wf-9c38fb1b → wf-dc6af54b): Compliance Engine state-of-the-art e especificação técnica completa.

### Pesquisas adiadas

- **Pesquisa D2** (classificador regressivo SJR+JIF para v3.0): adiada para o Cowork onde será efetivamente usada.
- **Pesquisa D3** (aspectos publicáveis honestamente da v2.0): adiada para após a v2.0 implementada e testada com casos reais (não-fixtures).

---

## [1.0.0-alpha26] — 2026-04-29

Versão consolidada anterior. Sprint Badge calibrado com n=187 SLRs (insuficiente para publicação rigorosa). 4 cenários canônicos validados.

(Detalhes em journal.txt e references/calibrations/v1.0-2026-04-29.md.)
