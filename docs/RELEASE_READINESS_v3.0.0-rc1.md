# Release readiness — v3.0.0-rc1

This document is the mechanical verification of the v3.0.0-rc1
acceptance criteria from issue #10. Every check below is a
copy-pasteable shell command; the result column captures the
result at the date of this report.

**Report date:** 2026-05-07
**Branch:** `develop` after PR #77 merge.

## Summary

| # | Criterion | Result |
|---|---|---|
| 1 | All search adapters implement `AdapterPort` | ⚠️ 58 / 62 (4 carried to v3.0.0 stable) |
| 2 | `mypy --strict` green on `domain/` + `application/` | ✅ pass |
| 3 | Coverage ≥ 90% on `domain/` + `application/` | ✅ 98.72% / 100.00% |
| 4 | Zero `urllib.request` outside `infrastructure/http_client.py` | ✅ pass |
| 5 | Zero `argparse` outside `interface/cli/` | ✅ pass |
| 6 | Zero `datetime.now()` in `domain/` | ✅ pass |
| 7 | CHANGELOG with migration guide v2 → v3 | ✅ `docs/MIGRATION_v2_TO_v3.md` |
| 8 | Tutorial: SLR from scratch in <30 min | ✅ `docs/TUTORIAL.md` |
| 9 | Cowork mentioned as v4 roadmap, not implemented | ✅ documented (not implemented) |
| 10 | RS-42 dogfooding | ⚠️ deferred — see notes |

**Architecture invariants** from `references/audits/AUDIT_PROCEDURE.md`
(v3 appendix, V1–V8) are checked separately at the bottom.

## Per-criterion verification

### 1. AdapterPort coverage

```bash
PYTHONPATH=src python3 -c "
from ignorantia.infrastructure.search.adapter_factory import AdapterFactory
print(len(AdapterFactory.known_sources()))
"
# → 58
```

The 4-adapter gap vs the historical v2 count of 62 is the same gap
recorded in the project journal on 2026-05-06: `dimensions`,
`oa_button` (Tier-0 OAB), `embase_full`, and `latindex` are
referenced by `scripts/searches/` but are not yet wired into the
v3 `AdapterFactory` registry. They migrate as a follow-up batch in
v3.0.0 stable; the RC ships with the 58 already migrated. Every
registered adapter implements `AdapterPort` (the registry function
type `Callable[[HttpClient], AdapterPort]` enforces this at
factory construction).

### 2. `mypy --strict` on `domain/` + `application/`

```bash
mypy --strict src/ignorantia/domain src/ignorantia/application
# → No issues found
```

Plus the whole `src/ignorantia/`:

```bash
mypy --strict src/ignorantia
# → No issues found
```

### 3. Coverage thresholds

```bash
pytest tests/unit/domain/ --cov=ignorantia.domain      # → 98.72%
pytest tests/unit/application/ --cov=ignorantia.application  # → 100.00%
```

The threshold is ≥ 90%; both layers exceed it.

### 4. `urllib.request` outside `http_client.py`

```bash
grep -rn "urllib.request.urlopen" src/ignorantia/ \
    --include="*.py" | grep -v http_client
# → src/ignorantia/infrastructure/search/http/arxiv.py:4: (docstring)
```

The single match is the **module docstring** of `arxiv.py`
mentioning v2 history. No code calls `urllib.request.urlopen`
outside `http_client.py`.

### 5. `argparse` outside `interface/cli/`

```bash
grep -rn "import argparse\|from argparse" src/ignorantia/
# → (empty)
```

The v3 CLI uses Click; argparse is fully retired from the v3
package. The `scripts/` directory (v2) still uses argparse but is
out of scope.

### 6. `datetime.now()` in `domain/`

AST-level check (regex would catch docstring mentions):

```python
# Same script as in AUDIT_PROCEDURE.md V4
# → V4 strict (AST): PASS — zero datetime.now() calls in domain+application
```

The single authorised call site is
`src/ignorantia/interface/cli/main._real_clock()`. Every domain
service (`ManifestService`, `ComplianceEngine`, `PipelineExecutor`)
takes a `clock: Callable[[], str]` constructor parameter (issue
#13).

### 7. CHANGELOG + migration guide

* `docs/MIGRATION_v2_TO_v3.md` — full v2→v3 mapping, CLI command
  examples, deprecation timeline.
* `CHANGELOG.md` — v3.0.0-rc1 entry added in this PR.

### 8. End-to-end tutorial in <30 min

`docs/TUTORIAL.md` walks from clean checkout to rendered HTML +
LaTeX + DOCX artefacts in ~25 minutes (copy-paste). Every step is
exercised by the CI test suite (the underlying use cases / CLI
commands are unit-tested) so the tutorial cannot silently rot.

### 9. Cowork as v4 roadmap

Cowork (multi-author collaborative editing of an SLR package) is
referenced in the architecture plan only as future scope — there
is no implementation in v3 and no API surface that would imply
its presence. See:

* `references/V3_ARCHITECTURE_PLAN.md` (Domain events: future)
* No `cowork` / `collaboration` / `multi_author` modules in
  `src/ignorantia/`.

### 10. RS-42 dogfooding

The acceptance criterion "RS-42 dogfooding: todos os 62 adapters
executados; pipeline completo gera manuscrito" requires running
the full pipeline against live external APIs — not something the
RC build can verify in CI without network credentials and
controlled fixtures. The RC therefore ships with:

* **Validated**: every domain + application unit test (2146 green),
  every CLI subcommand exercised end-to-end against stub services
  in `tests/unit/interface/`, every JSON manifest schema-validated.
* **Deferred to dogfooding sprint** between rc1 and v3.0.0 stable:
  a real-network run of `ignorantia search` against the 58 wired
  adapters + a complete `render` → `finalize` cycle on a real SLR
  topic. Issues raised in dogfooding land as v3.0.0 release blockers.

## V1–V8 architecture invariants

| Dim | Invariant | Result |
|---|---|---|
| V1 | No cross-context imports under `domain/<ctx>/` | ✅ pass |
| V2 | No `urllib`/`requests`/`httpx` in `domain/`+`application/` | ✅ pass |
| V3 | `interface/cli/` consumes DTOs only (+ enum exception) | ✅ pass |
| V4 | No `datetime.now()` in `domain/`+`application/` (AST-checked) | ✅ pass |
| V5 | Every CLI manifest goes through `validate_manifest()` | ✅ pass |
| V6 | `ignorantia.legacy` import emits `DeprecationWarning` | ✅ pass |
| V7 | Per-layer coverage (domain ≥90%, app ≥90%, interface ≥70%, infra ≥70%) | ✅ pass |
| V8 | `mypy --strict` clean; `# type: ignore` only with documented reason | ✅ pass |

## Test surface

* `pytest -q` — **2146 passed, 1 skipped** (the skipped test is the
  `DocxRenderer` integration test gated on the optional `[docx]`
  extra; CI installs the extra and runs it).
* `ruff check src tests` — clean.
* `ruff format --check src tests` — clean.
* `bandit -r src -c pyproject.toml` — clean.

## Outstanding work for v3.0.0 stable

* Migrate the remaining 4 search adapters into the v3 factory
  (`dimensions`, `oa_button`, `embase_full`, `latindex`).
* Complete the dogfooding sprint described in §10.
* Migrate concrete pipeline steps from `scripts/pipeline_finalize.py`
  into `infrastructure/pipeline/` (the v3 `finalize` subcommand
  currently runs an empty step registry).
* Bump `version` in `pyproject.toml` from `2.23.0` to `3.0.0` once
  the dogfooding sprint signs off.

## Ship signal

The 8 architecture invariants pass mechanically. 8 of 10 issue-#10
acceptance criteria pass mechanically; the remaining 2 (62 adapters
+ RS-42 dogfooding) are explicit deferrals to v3.0.0 stable, both
documented above. The RC is ready to tag.
