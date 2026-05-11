# Tutorial — Ignorantia v3 in 30 minutes

This tutorial walks you from a clean checkout to a rendered
manuscript artefact using only the v3 Click CLI. No prior
familiarity with the Ignorantia v2 surface is assumed. Every step
is copy-pasteable.

**You will learn how to:**

1. Install Ignorantia v3 with the optional `[docx]` extra.
2. Smoke-test the CLI surface (`--help`, `--version`).
3. Author a minimal `manuscript.json` from the wire-format reference.
4. Render the manuscript to HTML, LaTeX, and DOCX with three
   different citation styles.
5. Record an audit entry against the v3 reproducibility manifest.
6. Inspect every subcommand's output JSON against its schema.

**Time:** ~25 minutes if you copy-paste; ~45 minutes if you tweak
the example as you go.

**Prerequisites:** Python ≥ 3.10, a POSIX shell, and a local clone
of the Ignorantia repository.

---

## Step 1 — Install

From the repository root:

```bash
pip install -e '.[dev,docx]'
```

The `[dev]` extra installs `pytest`, `ruff`, `mypy`, etc. — useful
if you plan to run the test suite. The `[docx]` extra brings
`python-docx`, required to render `.docx` artefacts. Drop either if
you don't need it; the rest of the tutorial works with just the base
install.

Verify:

```bash
ignorantia --version
# → cli 2.23.0  (the project version; v3 is in integration)

ignorantia --help
# Lists the four subcommands: audit, finalize, render, search.
```

If `ignorantia` is not on your `$PATH`, the `pip install -e` step
silently failed; rerun it with `-v` to see the error.

---

## Step 2 — Author a manuscript JSON

Create `tutorial/manuscript.json`. The shape mirrors the
`RenderManuscriptCommand` DTO:

```bash
mkdir -p tutorial
cat > tutorial/manuscript.json <<'JSON'
{
    "title": "A Tutorial Systematic Review",
    "abstract": "This worked example demonstrates the v3 render pipeline end-to-end.",
    "language": "en",
    "keywords": ["evidence", "systematic review", "tutorial"],
    "sections": [
        {
            "id": "introduction",
            "title": "Introduction",
            "body_md": "Systematic reviews synthesise the evidence base on a focused question.\n\nThis tutorial walks through a minimal end-to-end render."
        },
        {
            "id": "methods",
            "title": "Methods",
            "body_md": "We followed PRISMA-2020 reporting. Sources were searched in **OpenAlex**, **Crossref**, and **arXiv**."
        },
        {
            "id": "results",
            "title": "Results",
            "body_md": "After deduplication, 71 unique records were screened."
        }
    ],
    "references": [
        {
            "type": "article",
            "title": "Quality of evidence in SLRs",
            "authors": ["Silva, J. P.", "Pereira, A.", "Costa, B."],
            "year": 2024,
            "venue": "Journal of Systematic Reviews",
            "volume": "10",
            "issue": "2",
            "pages": "100-110",
            "doi": "10.1234/jsr.2024.001"
        },
        {
            "type": "book",
            "title": "Systematic Reviews",
            "authors": ["Pereira, Ana", "Costa, Bruno"],
            "year": 2023,
            "publisher": "Academic Press",
            "location": "São Paulo"
        }
    ]
}
JSON
```

The minimum required field is `title`; everything else has a
default. The full set of optional fields per reference type is
documented in
[`src/ignorantia/application/dtos.py`](../src/ignorantia/application/dtos.py).

---

## Step 3 — Render to HTML (APA citations, default)

```bash
ignorantia render \
    --input tutorial/manuscript.json \
    --output tutorial/manuscript.html \
    --format html \
    --citation-style apa
# → {"output_format": "html", "byte_size": 1827, "output_path": "tutorial/manuscript.html"}
```

Open `tutorial/manuscript.html` in a browser. You should see:

- An `<h1>` with the manuscript title.
- An `<section class="abstract">` block with the abstract.
- A `<p class="keywords">` line.
- One `<section id="…">` per section, each with an `<h2>` heading
  and `<p>`-wrapped paragraphs (Markdown bold `**…**` becomes
  `<strong>`).
- A `<section class="references">` listing the references with APA
  formatting: `Silva, J. P., Pereira, A., & Costa, B. (2024). …`.

Inspect the JSON line printed by the CLI — it conforms to
[`render_result.schema.json`](../src/ignorantia/interface/manifests/render_result.schema.json):

```json
{
    "output_format": "html",
    "byte_size": 1827,
    "output_path": "tutorial/manuscript.html"
}
```

---

## Step 4 — Render to LaTeX (ABNT citations)

```bash
ignorantia render \
    --input tutorial/manuscript.json \
    --output tutorial/manuscript.tex \
    --format latex \
    --citation-style abnt
# → {"output_format": "latex", "byte_size": 1456, "output_path": "tutorial/manuscript.tex"}
```

Inspect `tutorial/manuscript.tex`. You'll see `\documentclass{article}`,
the abstract environment, sectioning commands, and a `thebibliography`
block whose entries follow ABNT NBR 6023:2018 (uppercase surnames,
`p. 100-110`, etc.).

To compile to PDF (optional):

```bash
pdflatex -output-directory=tutorial tutorial/manuscript.tex
```

---

## Step 5 — Render to DOCX (IEEE numeric citations)

Requires the `[docx]` extra installed in step 1.

```bash
ignorantia render \
    --input tutorial/manuscript.json \
    --output tutorial/manuscript.docx \
    --format docx \
    --citation-style ieee
# → {"output_format": "docx", "byte_size": 36412, "output_path": "tutorial/manuscript.docx"}
```

Open the `.docx` in Word, LibreOffice, or Pages. Sections become
Heading 2 styled blocks; references appear as numbered list entries
with IEEE inline brackets `[N]`.

---

## Step 6 — Record an audit entry

The reproducibility manifest tracks every event in the SLR
lifecycle (search runs, screening decisions, package builds, …).
Append one entry:

```bash
ignorantia audit \
    --action tutorial.complete \
    --actor cli \
    --payload '{"steps_completed": 6, "artefacts": ["html","latex","docx"]}'
# → {"timestamp_iso8601": "2026-05-07T22:35:00Z", "action": "tutorial.complete", "manifest_size": 1}
```

The output conforms to
[`audit_result.schema.json`](../src/ignorantia/interface/manifests/audit_result.schema.json).

> **Note.** Each CLI invocation starts fresh — the in-process
> manifest is not yet persisted to disk in v3.0.0-alpha. Persistence
> arrives with infrastructure-layer wiring in a follow-up release.
> For now, audit is useful as a smoke check and inside scripts that
> compose `RunAuditUseCase` programmatically across calls.

---

## Step 7 — Run the pipeline (smoke)

```bash
ignorantia finalize --actor cli
# → {"started_at_iso8601": …, "finished_at_iso8601": …,
#    "n_ok": 0, "n_skipped": 0, "n_errors": 0,
#    "final_artifacts": [], "is_successful": true, "steps": []}
```

The pipeline runs an empty step registry in v3.0.0-alpha. Concrete
steps (cross-tab, render, screening) migrate from
`scripts/pipeline_finalize.py` into `infrastructure/pipeline/` over
the upcoming maintenance releases. Run
`ignorantia finalize --help` to see the option surface as it grows.

---

## Step 8 — Search the literature (network-dependent)

Skip this step if you're working offline.

```bash
ignorantia search \
    --text "evidence synthesis methodology" \
    --source openalex --source crossref --source arxiv \
    --year-start 2020 --year-end 2025 \
    --output tutorial/search_results.json
# → {"n_sources_ok": 3, "n_sources_errored": 0,
#    "n_items_total": 87, "n_items_deduplicated": 71,
#    "per_source_status": [
#        {"source": "openalex", "method": "real", "n_items": 45, "total_results": 1234},
#        {"source": "crossref", "method": "real", "n_items": 30, "total_results": 567},
#        {"source": "arxiv",    "method": "real", "n_items": 12, "total_results": 89}
#    ]}
```

`tutorial/search_results.json` will hold the full per-source +
deduplicated DTOs. Resilience semantics: any single adapter
returning a `URLError` lands as `Method.REAL_ERROR` in
`per_source_status`; the rest of the search still completes.

---

## Step 9 — What you built

You should now have a `tutorial/` directory with:

```
tutorial/
├── manuscript.json           # source-of-truth wire format
├── manuscript.html           # rendered HTML (APA)
├── manuscript.tex            # rendered LaTeX (ABNT)
├── manuscript.docx           # rendered DOCX (IEEE)
└── search_results.json       # only if you ran step 8
```

Every `.html` / `.tex` / `.docx` artefact was produced by the same
`RenderManuscriptUseCase` running over the same domain
`ManuscriptDoc` — only the renderer + citation formatter pair
changed. Same domain logic, three different output formats. That is
the Strategy + Hexagonal Architecture combination that makes v3
worth the migration.

---

## Where to go next

* **Programmatic API.** `docs/MIGRATION_v2_TO_v3.md` shows how to
  compose use cases directly without the CLI — useful for test
  harnesses and notebook explorations.
* **Custom citation styles.** Implement `CitationFormatterPort` and
  register the new formatter in
  `infrastructure/render/citation/factory.py`. The four shipped
  styles (ABNT, APA, IEEE, Vancouver) are the reference
  implementations.
* **Custom pipeline steps.** Implement a callable returning
  `StepResult` and append it to the registry in
  `interface/cli/main.build_pipeline_steps()`. The Open/Closed
  invariant means no edits to `PipelineExecutor` itself.
* **JSON schemas.** Every CLI manifest has a published schema in
  `src/ignorantia/interface/manifests/`. Downstream tooling can
  `$ref` them directly.
* **Architecture deep-dive.** `dev-docs/V3_ARCHITECTURE_PLAN.xml`
  documents the design rationale and the bounded-context map.
