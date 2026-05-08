# Migration guide — Ignorantia v2 → v3

This guide is for callers of Ignorantia v2.x who want to upgrade to
v3.x. The v3 surface area was reorganised under Clean Architecture
(domain / application / infrastructure / interface) and exposes a
new Click-based CLI. The v2 scripts under `scripts/` continue to
work unchanged in this transition release; the deprecation timeline
is documented at the end of this guide.

## TL;DR

* **You used `python3 scripts/<name>.py …`** — switch to
  `ignorantia <subcommand> --…`. The four subcommands are `audit`,
  `finalize`, `render`, `search`.
* **You imported anything from `scripts/`** — replace with imports
  from `ignorantia.application.use_cases` (orchestration) or
  `ignorantia.infrastructure.*` (concrete adapters / renderers /
  formatters). The `ignorantia.legacy` package emits a
  `DeprecationWarning` and offers a `migration_guide()` lookup
  function for tooling.
* **You parsed JSON output of v2 scripts** — the v3 CLI emits
  schema-validated JSON manifests under
  `ignorantia.interface.manifests.*`. Each subcommand's output
  shape is locked down in a published schema so downstream tooling
  can `$ref` it.

## What changed at the architectural level

| v2 (2.x) | v3 (3.x) |
|---|---|
| Standalone scripts in `scripts/` calling each other via `subprocess` | Bounded contexts under `src/ignorantia/{domain,application,infrastructure,interface}/` |
| `argparse` per script | Single `click` group with four subcommands |
| `urllib.request.urlopen` scattered across adapters | One `infrastructure/http_client.py` with throttle + retries |
| `datetime.now()` called inline | Clock callable injected at the composition root (issue #13) |
| Loose dict-based check results | Frozen `Decision` value object + `Severity` / `DecisionStatus` enums |
| Loose dict-based YAML profile load | `VenueProfile` aggregate with structured requirement value objects |
| `PIPELINE_STEPS` registry list (E10, v2.23.0) | `domain/pipeline/PipelineExecutor` + `PipelineStep` value object — same registry pattern, typed |
| `format_abnt.Reference` | `domain/render/Reference` + `CitationFormatterPort` Strategy |
| `render_v2.py` (1042-LOC, 4-tab layout) | `HtmlRenderer` (clean academic skeleton) + `LatexRenderer` + `DocxRenderer` |
| Output validated only by tests | Output validated at runtime against JSON-schemas in `interface/manifests/` |

## CLI command mapping

The v3 CLI is `ignorantia <subcommand> --…`. The four subcommands
cover every v2 entry point.

### `audit` — append to the reproducibility manifest

The closest v2 equivalent is the manifest record helpers in
`scripts/manifest_helpers.py` (Decisions 21 + 22). The v3 form is a
proper command:

```bash
# v3
ignorantia audit \
    --action search.run \
    --actor cli \
    --payload '{"query_hash": "abc123", "n_results": 42}'
# → {"timestamp_iso8601": "2026-05-07T12:00:00Z", "action": "search.run", "manifest_size": 1}
```

### `finalize` — run the Phase-7 pipeline

```bash
# v2
python3 scripts/pipeline_finalize.py --output-dir out --title "My SLR" …

# v3
ignorantia finalize --actor cli
# → {"started_at_iso8601": …, "n_ok": …, "is_successful": true, "steps": […]}
```

The concrete steps that v2's `pipeline_finalize.py` registered
(`cross_tab`, `format_abnt`, `render_html_chunks`, `render_docx_abnt`,
`render_latex`, `screening_pipeline`) are being migrated into
`infrastructure/pipeline/` incrementally. Until they land, the v3
`finalize` command runs an empty registry and emits a successful
empty pipeline summary — useful as a smoke check, not yet as a
drop-in replacement.

### `render` — render a manuscript

```bash
# v2
python3 scripts/render_manuscript.py --content content.json --out manuscript.html

# v3
ignorantia render \
    --input manuscript.json \
    --output manuscript.html \
    --format html \
    --citation-style abnt
# → {"output_format": "html", "byte_size": 12345, "output_path": "manuscript.html"}
```

The `--input` JSON is the wire form of `RenderManuscriptCommand`:

```json
{
    "title": "A Systematic Review of Evidence Synthesis",
    "abstract": "This study evaluates …",
    "language": "en",
    "keywords": ["evidence", "review"],
    "sections": [
        {"id": "intro", "title": "Introduction", "body_md": "Body text."},
        {"id": "methods", "title": "Methods", "body_md": "Methods text."}
    ],
    "references": [
        {
            "type": "article",
            "title": "Quality of evidence in SLRs",
            "authors": ["Silva, J. P."],
            "year": 2024,
            "venue": "Journal of SLR",
            "doi": "10.1234/jsl.2024.001"
        }
    ]
}
```

`--format` accepts `html` (default), `latex`, or `docx`. DOCX
requires the optional `[docx]` extra: `pip install
'ignorantia[docx]'`. `--citation-style` accepts `abnt`, `apa`
(default), `ieee`, or `vancouver`.

### `search` — multi-source bibliographic search

```bash
# v2 — one script per database, glued by orchestrator subprocess calls

# v3
ignorantia search \
    --text "evidence synthesis methodology" \
    --source openalex --source crossref --source arxiv \
    --year-start 2020 --year-end 2025 \
    --language en --language pt \
    --output results.json
# → on stdout: {"n_sources_ok": 3, "n_sources_errored": 0, "n_items_total": 87,
#               "n_items_deduplicated": 71, "per_source_status": [...]}
# → in results.json: full per_source + deduplicated_items DTOs
```

`--source` is repeatable; the orchestrator captures network errors
per-adapter as `Method.REAL_ERROR` rather than aborting the run, so
a single flaky source does not invalidate the whole search.

## v2 entry-point → v3 import mapping

The following Python paths still work in v2-style imports for one
release, but emit a `DeprecationWarning`:

| v2 path | v3 target |
|---|---|
| `scripts/render_v2.py` | `ignorantia render --format html` (HtmlRenderer) |
| `scripts/render_chunks.py` | `HtmlRenderer.render_section` + `InteractiveRendererPort` |
| `scripts/render_manuscript.py` | `ignorantia render` (with `--format` and `--citation-style`) |
| `scripts/format_abnt.py` | `ignorantia.infrastructure.render.citation.abnt_formatter` |
| `scripts/pipeline_finalize.py` | `ignorantia finalize` + `ignorantia.domain.pipeline.PipelineExecutor` |

Programmatic lookup via the compatibility layer:

```python
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from ignorantia import legacy

entry = legacy.lookup("scripts/render_v2.py")
print(entry.v3_target)  # → "`ignorantia render --format html` (HtmlRenderer)"
print(entry.notes)
# → "v3 produces a clean academic skeleton with no themes / no JS. …"

# Or iterate the full table:
for row in legacy.migration_guide():
    print(row.v2_entry, "→", row.v3_target)
```

## JSON manifest schemas

Every CLI subcommand's output is validated at runtime against a
Draft 2020-12 JSON-schema before it is echoed. The schemas live in
`src/ignorantia/interface/manifests/*.schema.json` and can be
referenced (`$ref`) by downstream tooling that wants to type-check
ingested manifests:

* `audit_result.schema.json`
* `finalize_pipeline_result.schema.json`
* `render_result.schema.json`
* `search_result.schema.json`

The schemas pin enum vocabularies (`output_format`, `method`,
`status`) so a v3 enum addition without a schema update fails the
build. `additionalProperties: false` on every schema means
accidental new fields surface immediately.

## Programmatic API: composing use cases directly

CLI is not the only entry point — the use cases under
`ignorantia.application.use_cases` can be composed by other Python
code (test harnesses, alternative interfaces, notebook explorations):

```python
from datetime import datetime, timezone

from ignorantia.application.dtos import RunAuditCommand
from ignorantia.application.use_cases.run_audit import RunAuditUseCase
from ignorantia.domain.audit.services import ManifestService


def real_clock() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


service = ManifestService(clock=real_clock)
use_case = RunAuditUseCase(service=service)

result = use_case.execute(RunAuditCommand(action="search.run", actor="me"))
print(result.timestamp_iso8601, result.manifest_size)
```

The same shape applies for `FinalizePipelineUseCase`,
`RenderManuscriptUseCase`, and `SearchForStudiesUseCase`. Each takes
its dependencies via constructor injection (DIP) — production
wiring lives in `ignorantia.interface.cli.main.build_*_use_case`,
which you can reuse or mirror.

## Deprecation timeline

* **v3.0.0** (this release line): v2 scripts under `scripts/` work
  unchanged; `ignorantia.legacy` emits `DeprecationWarning` on
  import.
* **v3.x.y maintenance**: bug fixes only on the legacy surface;
  new features land only on v3 paths.
* **v4.0.0** (no committed date yet): `scripts/` directory removed;
  `ignorantia.legacy` removed. Anything still importing from those
  paths breaks at install time.

If you need help upgrading, the [`ignorantia.legacy.migration_guide()`](#v2-entry-point--v3-import-mapping)
function is the canonical machine-readable source for the v2 → v3
mapping.
