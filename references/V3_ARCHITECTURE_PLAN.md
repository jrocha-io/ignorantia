# Plano v3.0.0 — Refactoring arquitetural

**Status:** planejado, não iniciado · **Início estimado:** após v2.23.0 estabilizar · **Escopo:** semanas, não horas

## Mandato

Usuário (2026-05-04 pós-v2.23.0): *"Use todas as boas práticas POSSÍVEIS: Clean code, SOLID, princípios de design essenciais (DRY, YAGNI, KISS etc.), DDD, Modularidade e Acoplamento Baixo, Design Patterns, TDD, Testes Automatizados, Refatoração Constante, Code Reviews rigorosas, Git flow, Documentação Clara, Security by Design etc. Nem que pra isso seja necessário refazer tudo criando uma versão 3 que não é bem a planejada, adiando a versão cowork para a versão 4."*

## Princípio guia

**v2.x foi orgânica** — adapters foram crescendo um a um, cada um com seu próprio padrão. Resultado: 5 rodadas de auditoria detectando categorias diferentes de inconsistência (USER_AGENT em 9 versões, source_tier int vs str, schemas heterogêneos, mock ≠ real). v2.23.0 fechou DRY/Liskov mais críticos via fixes pontuais.

**v3.0.0 será arquitetada** — bounded contexts claros, ports & adapters, classe base canônica (`FetchedItem` migrado para todos), validação de schema em runtime, TDD desde o primeiro commit. Cowork (originalmente planejado para v3) **adiado para v4** porque dignifica trabalhar primeiro a base.

## Bounded Contexts (DDD)

```
ignorantia/
├── domain/                      # camada de domínio pura (sem I/O)
│   ├── __init__.py
│   ├── slr/                     # bounded context: Systematic Literature Review
│   │   ├── entities.py          # Study, Manuscript, Review (entities)
│   │   ├── value_objects.py     # DOI, ISSN, Tier, Language (VOs)
│   │   ├── repositories.py      # ABC: StudyRepository, ManuscriptRepository
│   │   └── services.py          # DeduplicationService, ScreeningService
│   ├── search/                  # bounded context: Search across databases
│   │   ├── entities.py          # SearchQuery, SearchResult, FetchedItem
│   │   ├── value_objects.py     # Tier ('tier0'..'tier3'), Method enum
│   │   ├── ports/
│   │   │   ├── adapter_port.py  # interface AdapterPort: fetch, validate
│   │   │   └── orchestrator_port.py
│   │   └── services.py          # SearchOrchestrator, DeduplicatorService
│   ├── render/                  # bounded context: Manuscript rendering
│   │   ├── entities.py          # ManuscriptDoc, RenderTarget
│   │   ├── value_objects.py     # CitationStyle (ABNT, APA, IEEE, Vancouver)
│   │   ├── ports/
│   │   │   └── renderer_port.py # interface RendererPort
│   │   └── services.py          # PipelineFinalize (registry-based, E10)
│   ├── compliance/              # bounded context: Editorial compliance
│   │   ├── entities.py          # VenueProfile, ComplianceReport
│   │   ├── value_objects.py     # Decision, DesignDecision
│   │   └── services.py          # ComplianceEngine
│   └── audit/                   # bounded context: Audit log + reproducibility
│       ├── entities.py          # AuditEntry, ReproducibilityManifest
│       └── services.py          # ManifestService
│
├── infrastructure/              # adapters externos
│   ├── search/
│   │   ├── http/
│   │   │   ├── arxiv.py         # implementa AdapterPort
│   │   │   ├── crossref.py
│   │   │   ├── ...              # 60+ adapters, cada um implementando port
│   │   ├── paywall/             # subclasses específicas com cascata
│   │   └── _adapter_base.py     # classe abstrata + helpers
│   ├── render/
│   │   ├── chunks_renderer.py   # implementa RendererPort para HTML
│   │   ├── docx_renderer.py
│   │   ├── latex_renderer.py
│   ├── persistence/             # I/O de arquivos
│   │   ├── yaml_repository.py   # carrega profiles YAML
│   │   ├── json_writer.py       # escreve JSONs com schema validation
│   └── http_client.py           # cliente HTTP centralizado (timeout, retry, UA)
│
├── application/                 # casos de uso (use cases)
│   ├── use_cases/
│   │   ├── search_for_studies.py     # SearchForStudiesUseCase
│   │   ├── render_manuscript.py      # RenderManuscriptUseCase
│   │   ├── finalize_pipeline.py      # FinalizePipelineUseCase
│   │   ├── run_audit.py              # RunAuditUseCase
│   └── dtos.py                       # DTOs entre camadas
│
├── interface/                   # camada de apresentação (CLI)
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── commands.py          # Click/argparse — todos os entry points
│   │   ├── main.py
│   └── manifests/               # JSON schemas para validação
│       ├── search_result.schema.json
│       ├── orchestration_summary.schema.json
│       └── pipeline_summary.schema.json
│
├── tests/
│   ├── unit/                    # 1 teste por classe/função; isolado
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/             # 2+ classes interagindo
│   ├── e2e/                     # subprocess + filesystem real
│   └── contract/                # property-based + schema validation
└── pyproject.toml               # dependências, build, configs (ruff, mypy, pytest)
```

## Princípios aplicados

### Clean Code
- Funções **<20 linhas**.
- Nomes claros: `Study` em vez de `dict`, `DOI` em vez de `str`.
- **Sem comentários óbvios** — código auto-explicativo.

### SOLID

**S** — Single Responsibility:
- `SearchOrchestrator` apenas orquestra; não escreve arquivos (delega a `JsonWriter`).
- `PipelineFinalize` apenas executa registry; não conhece detalhes de cada step.
- Cada `AdapterPort` implementa apenas `fetch(query) -> SearchResult`.

**O** — Open/Closed:
- Novo adapter → adicionar classe que implementa `AdapterPort`. Zero edits no orquestrador.
- Nova etapa de pipeline → adicionar `PipelineStep` no registry. Zero edits em `run_pipeline`.
- Novo citation style → implementar `CitationFormatterPort`. Zero edits em renderers.

**L** — Liskov:
- Todos os adapters retornam **`SearchResult`** com schema fixo. v2.23.0 já corrigiu `source_tier`.
- Todos os renderers aceitam **`ManuscriptDoc`** + `RenderTarget`.

**I** — Interface Segregation:
- `AdapterPort.fetch()` separado de `AdapterPort.validate_query()`. Adapters que não suportam validate retornam `NotImplemented` claro.
- Renderers HTML/docx/latex compartilham `RendererPort` mas têm portas específicas (`InteractiveRendererPort` para HTML).

**D** — Dependency Inversion:
- `domain/` não importa de `infrastructure/`.
- Injeção de dependências: `SearchOrchestrator.__init__(adapter_factory: AdapterFactoryPort)`.

### DRY
- `FetchedItem` (já existe em v2 só para paywall) **migrado para todos os 62 adapters**.
- `cli_exit_with_error_message` (v2.23.0) — único lugar com lógica de stderr.
- HTTP client único: `infrastructure/http_client.py` com USER_AGENT, throttle, retry, timeout. Zero `urllib.request.urlopen` em adapters.
- Schemas JSON **validados em runtime** via `jsonschema`.

### KISS / YAGNI
- Não inventar abstrações sem uso real (ex: factory abstrata sem 2+ implementações).
- Não premature optimization (lazy-loading, async etc.) — adicionar quando profiling mostrar necessidade.
- Citation styles: **ABNT, APA, IEEE, Vancouver** — não adicionar Chicago/Harvard sem demanda.

### DDD (Domain-Driven Design)
- **Ubiquitous language**: termos do domínio (Study, Manuscript, Tier, Method) definidos em `domain/<context>/value_objects.py` e usados consistentemente.
- **Bounded contexts** isolados: `search/` não importa de `render/` diretamente — comunicam via DTOs em `application/`.
- **Aggregates**: `Review` é aggregate root que contém `[Study, ...]`.
- **Domain events** (futuro): `SearchCompleted`, `ScreeningDecisionMade` — para auditoria/extensão.

### TDD (estrito)
- **Vermelho**: escrever teste que falha primeiro.
- **Verde**: implementação mínima para passar.
- **Refatorar**: limpar mantendo verde.
- Cobertura mínima: **90%** em `domain/` e `application/`. **70%** em `infrastructure/`.
- **Testes de contrato** com `hypothesis` para schema validation (property-based).

### Modularidade + Acoplamento Baixo
- Cada bounded context = 1 pacote Python independente. Importa apenas de `domain/<próprio_contexto>` e `application/dtos`.
- Dependência circular? Erro de design — refatorar.
- `mypy --strict` em CI.

### Design Patterns aplicados

| Padrão | Onde | Por quê |
|---|---|---|
| **Adapter** | `infrastructure/search/http/*.py` | Cada adapter de busca é literal Adapter pattern |
| **Strategy** | Citation formatters, Renderers | ABNT/APA/IEEE/Vancouver são estratégias; HTML/docx/latex idem |
| **Registry** | `PIPELINE_STEPS` (v2.23.0 já tem) | Open/Closed |
| **Factory** | `AdapterFactory.create(name) -> AdapterPort` | Construção centralizada |
| **Repository** | `StudyRepository`, `ProfileRepository` | Persistência abstraída |
| **Use Case** | `SearchForStudiesUseCase` | Aplicação como objetos |
| **DTO** | Entre camadas | Sem leak de domínio para CLI |
| **Builder** | `ManuscriptDoc.builder()` | Construção fluente de docs complexos |
| **Observer** (futuro) | `DomainEventBus` | Auditoria, hooks |

### Testes Automatizados

```
tests/
├── unit/              # ~ 200+ testes; pytest -m unit; <5s total
├── integration/       # ~ 50 testes; pytest -m integration; <30s
├── e2e/               # ~ 20 testes subprocess; pytest -m e2e; <2min
└── contract/          # ~ 30 testes property-based; pytest -m contract
```

CI: pytest + ruff + mypy + bandit + pip-audit + coverage. Quebra build se cobertura cair abaixo do limite.

### Refatoração Constante
- **Boy Scout Rule** — toque em código, deixa-o melhor.
- Refactor antes de feature: se feature não cabe limpa em estrutura atual, refatora primeiro.
- Sem feature flags morta: remove código que não tem uso há 2+ versões.

### Code Reviews rigorosas
- Cada PR: ≥1 review humano + checklist:
  - [ ] SOLID violado?
  - [ ] DRY violado? (busca lateral por código semelhante)
  - [ ] Cobertura ≥ limite?
  - [ ] Documentação atualizada?
  - [ ] CHANGELOG atualizado?
  - [ ] AUDIT_PROCEDURE.md cobre dimensão nova encontrada?

### Git Flow
- `main` — releases estáveis (v2.23.0, v3.0.0).
- `develop` — integração contínua de features.
- `feature/<descrição>` — PRs para develop.
- `hotfix/<descrição>` — PRs diretos para main + backport.
- **SemVer estrito**: breaking change = major (v3.0.0); feature = minor; bugfix = patch.
- **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.

### Documentação Clara
- **README** — quickstart 5min.
- **Tutorial** — 1 SLR completa do zero (didático).
- **Arquitetura** — diagrama C4 (Context, Container, Component, Code).
- **API reference** — gerada de docstrings via Sphinx ou mkdocs.
- **AUDIT_PROCEDURE.md** — manual de auditoria (já existe em v2.22.0, atualizar para refletir v3 architecture).
- **DECISIONS.md** — manter ADRs (Architecture Decision Records).

### Security by Design
- **Input validation** em entry points (CLI args, profile YAML, content.json).
- **`bandit`** em CI.
- **`pip-audit`** para vulns em dependências.
- **Secrets**: `.env` via `python-dotenv` (gitignored). Nunca em código.
- **Rate limiting**: `infrastructure/http_client.py` impede abuso de APIs.
- **Logs**: nunca logar PII ou secrets.
- **Sandboxing** em smoke tests (não tocar filesystem fora de `tmp_path`).

## Roadmap por fases

| Fase | Conteúdo | Estimativa |
|---|---|---|
| **F0** | Repo split: criar `pyproject.toml`, configurar ruff/mypy/pytest, importar AUDIT_PROCEDURE.md, mover testes para `tests/unit/integration/e2e/contract/`. | 1-2 dias |
| **F1** | Domain layer: Study, Manuscript, FetchedItem, Tier, Method, DOI, ISSN value objects. Testes unitários completos para domain. | 2-3 dias |
| **F2** | Search bounded context: AdapterPort, SearchOrchestrator, DeduplicatorService. Migrar 1 adapter representativo (arxiv) como prova. | 3-4 dias |
| **F3** | Migração dos 61 adapters restantes. Cada um vira classe que implementa AdapterPort. | 1-2 semanas |
| **F4** | Render bounded context: RendererPort, MarkdownToLatex, ABNT/APA/IEEE/Vancouver formatters. | 1 semana |
| **F5** | Pipeline + Compliance + Audit contexts. | 1 semana |
| **F6** | Application layer (use cases) + DTOs. | 3-4 dias |
| **F7** | CLI nova com Click; deprecar entry points antigos. | 2-3 dias |
| **F8** | Documentação completa (Sphinx/mkdocs), tutorial, C4 diagrams. | 3-4 dias |
| **F9** | RC release; smoke + dogfood RS-42 com cobertura premium completa. | 1 semana |

**Total**: 6-10 semanas de trabalho focado.

## Critérios de aceitação v3.0.0

- [ ] Todos os 62 adapters implementam `AdapterPort` retornam `FetchedItem` com schema validado.
- [ ] `mypy --strict` verde em `domain/` e `application/`.
- [ ] Cobertura ≥90% em domain + application.
- [ ] Zero `urllib.request` fora de `infrastructure/http_client.py`.
- [ ] Zero `argparse` fora de `interface/cli/`.
- [ ] Zero `datetime.now()` em domain/ (apenas em infrastructure).
- [ ] CHANGELOG completo com migration guide v2 → v3.
- [ ] Tutorial: SLR do zero compila em <30 minutos.
- [ ] Cowork **mencionado como roadmap v4**, não implementado.

## Migration guide v2 → v3 (rascunho)

```python
# v2 (orgânico)
import sys; sys.path.insert(0, "scripts/searches")
import search_arxiv
result = search_arxiv.search("query", year_start=2023, year_end=2024)

# v3 (Clean Architecture)
from ignorantia.application.use_cases import SearchForStudiesUseCase
from ignorantia.domain.search import SearchQuery, Tier

use_case = SearchForStudiesUseCase()  # injeta dependencies via factory
query = SearchQuery(text="query", year_range=(2023, 2024), tier=Tier.TIER1)
result = use_case.execute(query, source="arxiv")  # retorna SearchResult tipado
```

Compatibility layer durante transição: pacote `ignorantia.legacy` expõe APIs v2 sob deprecação.

## O que NÃO faz parte da v3.0.0

- **Cowork**: adiado para v4.
- **Web UI**: nunca foi planejado.
- **Cloud deployment**: skill é offline-first.
- **Integração com Mendeley/Zotero**: futuro v5+ se demanda.
- **Multi-language UI**: pt-BR + en são suficientes.
