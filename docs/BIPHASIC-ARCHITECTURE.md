# Biphasic architecture (v3.0.0)

> **Goal of the skill.** Produce a Zenodo-ready scientific manuscript
> from a topic and a researcher profile, *with zero post-generation
> human review required* before deposit. The architecture below is the
> set of constraints under which that goal is mechanically verifiable.

This document is the contract between Phase 1 (Claude Desktop chat
session, operator interacts via `/ignorantia`) and Phase 2 (Anthropic
Cowork, batch retrieval + extraction + writing + packaging). It also
specifies the seven final gates that gate the Zenodo zip: if all seven
pass, the deposit is, by construction, fit to upload without further
review.

## Why biphasic

The monolithic skill (v2.23.x) ran the entire pipeline inside one chat
session. Three structural failures recurred:

1. **Token budget exhaustion.** Large reviews (≥ 5 sections, ≥ 20
   references, ≥ 3 web searches) hit the "esta conversa não pode ser
   compactada ainda mais" wall before any artifact reached disk.
2. **Ad-hoc fallback under pressure.** When the orchestrator scripts
   could not run, the chat session defaulted to `web_search` and
   produced `searches.json.metadata.execution_method:
   single_session_ad_hoc_web_search` — RS-42 v1.0.0 shipped this way.
3. **Abstract-based extraction.** The chat session lacked the
   throughput to download and read full-text for each elegible study,
   so the extraction was abstract-only. Claims in the synthesis could
   not be verified against the actual source paragraph.

Splitting the pipeline at the natural PRISMA inflection point —
*after* title/abstract screening, *before* full-text retrieval —
isolates the cognitive work (Phase 1) from the throughput work
(Phase 2), aligns the architecture with PRISMA's own pre-registration
discipline, and makes claim-to-source verification (the largest
hallucination risk) tractable.

## Phase boundaries

### Phase 1 — Claude Desktop chat (`/ignorantia`)

**Environment.** Chat session in claude.ai, single token budget.
Tools: `web_search`, `web_fetch`, `ask_user_input_v0`, basic file I/O
through tool harness.

**Responsibilities.**

1. **Interview** the operator (10 dimensions per current SKILL.md).
2. **Pre-registered protocol** — PCC, IC/EC, base list, search
   strings, AI disclosure block.
3. **Metadata-only search** in OA bases (arXiv, OpenAlex, Crossref,
   Semantic Scholar, PubMed, EuropePMC, DOAJ, ERIC, dblp, SciELO,
   LA Referencia, Redalyc, BDTD, Catálogo CAPES). Paywall bases →
   gap_report.md with citation-list-for-manual-retrieval.
4. **Deduplication** by DOI > arXiv ID > title-author-year.
5. **Title/abstract screening** (the 3-pass cascade documented in the
   skill, refined as needed).
6. **Handoff package** — `handoff-v1.0.0.json` matching
   `schemas/handoff-v1.schema.json`, with SHA-256 self-attestation
   in `handoff_hash` field.

**Exit criteria.** Phase 1 succeeds when the handoff JSON validates
against the schema **and** the operator has confirmed the included
list in chat (single confirmation prompt — not a multi-question
review).

**What Phase 1 does NOT do.**

- Does not retrieve full-text. (No paper downloads in chat.)
- Does not write any manuscript prose. (Phase 2's job.)
- Does not run the four production gates (persona, assessment,
  invariants, vocabulary). Those are Phase 2 final gates.

### Phase 2 — Cowork (`/ignorantia-execute <handoff.json>`)

**Environment.** Anthropic Cowork — batch, persistent state, large
token budget, tool access (filesystem, network, subprocess).

**Responsibilities.**

1. **Validate handoff** against schema; abort with diagnostic if
   invalid. Verify `handoff_hash` matches contents.
2. **Full-text retrieval** for every DOI in
   `included_for_fulltext[]`. Tier cascade: open-access locator
   (Unpaywall + OAB + CORE) → operator-provided credentials → manual
   citation list for irretrievable items. Items with no recoverable
   full-text are dropped from the included set and registered in
   `gap_report.md`.
3. **Read full-text.** Each retrieved PDF/HTML is parsed; extraction
   targets specific paragraphs/sections, not abstracts.
4. **Extraction with source mapping.** Every substantive claim in the
   extraction CSV is paired with a `(source_doi, source_anchor)` tuple
   in `claim_to_source.json`. The anchor is page-number for PDFs or
   section-id for HTML.
5. **Quality appraisal** (CASP/DARE; Kitchenham if SE/CS).
6. **Snowballing backward** from seed papers (3-10 most central
   to the topic). New DOIs go through a mini-loop: retrieve →
   abstract-screen → full-text-screen → add to corpus.
7. **Synthesis** narrative-thematic per RQ, with cross-tabulation
   (Decisão 29). Every claim in the manuscript cites a `claim_id`
   that maps back to `claim_to_source.json`.
8. **Compilation** — LaTeX → PDF via `pdflatex + bibtex + pdflatex x2`.
   DOCX via pandoc from the same `.tex`.
9. **Seven final gates** (next section). All seven must pass before
   the Zenodo zip is sealed.
10. **Final ZIP** — `<author-slug>-<area>-<topic>-v<X.Y.Z>.zip`,
    SHA-256 of every artifact in README. **No prompt to operator
    asks for review.** The zip is, by construction, fit to upload.

**What Phase 2 does NOT do.**

- Does not modify the protocol. Protocol amendments are recorded as
  `gap_report.md` entries; the operator decides whether to re-run
  Phase 1.
- Does not invoke Zenodo upload or any external service. The skill
  produces the artifact; deposit is the operator's manual step.
- Does not send email, post to Slack/social, contact authors. The
  skill stops at the artifact.

## Handoff contract

`schemas/handoff-v1.schema.json` is the source of truth. Summary:

| Field | Type | Purpose |
|---|---|---|
| `phase` | const `1` | Identifies the handoff origin phase. |
| `schema_version` | string | `1.0` (semver). Phase 2 checks compatibility. |
| `created_at` | ISO-8601 | Timestamp of Phase 1 completion. |
| `protocol` | object | PCC + IC/EC + base list + search strings + AI disclosure. |
| `searches` | array | One entry per (base, query). Includes date, raw hit count, status. |
| `dedup` | object | Stats: n_in, n_out, hierarchy used. |
| `screening` | object | Per-pass stats + per-DOI decision trace. |
| `included_for_fulltext` | array | One entry per DOI to retrieve in Phase 2. Includes title, year, abstract, expected access tier. |
| `metadata` | object | Skill version, model used, ISO timestamps. |
| `handoff_hash` | hex string | SHA-256 of all of the above (excluding `handoff_hash` itself). |

Phase 2 validates by:

1. Schema-conformance against `handoff-v1.schema.json`.
2. Recomputing the hash and verifying it matches `handoff_hash`.
3. Ensuring every DOI in `included_for_fulltext[]` is also in
   `screening.trace_per_doi` with a positive final decision.

If any check fails, Phase 2 aborts before any retrieval.

## Final gates (seven sequential)

Phase 2 runs these gates after compilation. The ZIP is sealed if and
only if **all seven pass**. Each gate emits a JSON sidecar in the
output directory; the seven sidecars form an auditable trail.

### Gate 1 — persona-voice (strict)

Existing. `scripts/check_persona_voice.py --strict`. Catches the
"pipeline execution narration" failure mode (Decisão 20). Emits
`persona_voice_gate.json` with `{passed, warnings[]}`.

### Gate 2 — quality assessment

Existing. `scripts/generate_assessment.py`. Exit 2 on any eliminator
or score < 7.0. Emits `assessment_gate.json` with
`{passed, score, eliminatory_count}`.

### Gate 3 — pipeline invariants

Existing. `scripts/check_pipeline_invariants.py`. I1 (no ad-hoc
search), I2 (≥3 bases), I3 (no ERROR steps). Emits
`pipeline_invariants_gate.json`.

### Gate 4 — vocabulary (deposit-wide)

Existing. `scripts/check_decision_19_vocabulary.py --all <dir> --gate-sidecar`.
Twelve forbidden-pattern classes. Emits `vocabulary_gate.json`.

### Gate 5 — claim-to-source coverage (new)

New. `scripts/check_claim_source_coverage.py <dir>`.

**Input.** `extraction.csv`, `claim_to_source.json`, the manuscript
prose (`manuscript.tex` plus its sections).

**Algorithm.**

1. Walk the manuscript body. Identify each substantive claim — i.e.,
   each sentence that contains at least one inline citation marker
   (`[N]`, `(AUTHOR, year)`, `\cite{key}`).
2. For each claim, extract the cited keys.
3. For each cited key, require a row in `claim_to_source.json` with
   the same key and a non-empty `source_anchor` field.
4. Coverage = (number of substantive claims with full
   `claim_to_source` row) / (total substantive claims).
5. Exit 2 if coverage < 100%.

**Why it matters.** This is the gate that catches "abstract-based
hallucinated synthesis". A claim like "S08 reports 58× speedup" only
passes if `claim_to_source.json` says `{claim_id: ..., source_doi:
10.x/y, source_anchor: "p.7 §3.2"}`. The anchor is captured during
extraction in Phase 2; missing anchors block the deposit.

**Sidecar.** `claim_source_gate.json` with `{passed, total_claims,
covered_claims, uncovered_claim_ids[]}`.

### Gate 6 — citation graph integrity (new)

New. `scripts/check_citation_graph.py <dir>`.

**Input.** `manuscript.tex`, `bibliography.bib`.

**Algorithm.**

1. Parse the manuscript for inline citations (`\cite{key}`).
2. Parse the `.bib` for entries.
3. **Check A**: every inline `\cite{key}` resolves to a `.bib` entry.
4. **Check B**: every `.bib` entry is cited at least once in the body
   (prevents reference padding).
5. **Check C** (live DOI check, opt-in via `--verify-dois`): for
   each `.bib` entry with a `doi = {…}` field, ping
   `https://api.crossref.org/works/{doi}` with a 5-second timeout.
   Cache results in `doi_verification_cache.json`. Items returning
   HTTP 404 or "is retracted" via Retraction Watch API are flagged.

Exit 2 if any of A, B, or C fails (when verification opted in for C).

**Sidecar.** `citation_graph_gate.json` with `{passed, missing_keys[],
unused_keys[], retracted_dois[], unreachable_dois[]}`.

### Gate 7 — manuscript-substantial (new)

New. `scripts/check_manuscript_substantial.py <dir>`.

**Input.** `manuscript.pdf`, `manuscript.tex`.

**Algorithm.**

1. Verify `manuscript.pdf` exists and was produced by the actual
   compile (pdfinfo metadata sanity).
2. Page count ≥ `--min-pages` (default 12 for full SLR; 8 for rapid).
3. Word count of body ≥ `--min-words` (default 5000; 3000 for rapid).
4. Every required section heading is present: §00 Propósito, §01 CoI,
   §02 Introdução, §03 RQ, §04 Métodos, §05 Resultados, §06 Discussão,
   §07 Conclusões, §08 Evidência contrária, §09 Limitações.

Exit 2 if any check fails.

**Sidecar.** `manuscript_substantial_gate.json` with `{passed,
page_count, word_count, missing_sections[]}`.

## "Zenodo-ready" definition

The deposit is fit to upload without human review iff all seven
sidecars exist in the output dir with `passed: true`. Any other state
indicates the skill did not complete its job; the operator must not
deposit.

The user's acceptance test: *"O que faria seguindo as instruções
estaria pronto para que eu publicasse no Zenodo sem nem conferir?"*

The seven gates encode that acceptance test mechanically. If they
pass, the deposit is, by construction, fit. If they fail, the skill
itself blocks the deposit.

## Migration from monolithic v2.23.4

v3.0.0 is a breaking change. The monolithic flow is removed. The
biphasic flow replaces it.

Migration path for in-progress reviews:

1. Reviews started under v2.23.4 finish on v2.23.4 (the zip already
   compiled is final).
2. New reviews start with Phase 1 (Claude Desktop `/ignorantia`)
   producing a handoff, then Phase 2 (Cowork
   `/ignorantia-execute`).
3. Operators with an in-progress v2.23.4 session that has not yet
   reached the manuscript stage can interrupt, export the partial
   state to a handoff JSON manually, and resume in Phase 2.

## What this design explicitly removes

The earlier proposal carried several knobs and loops that are
intentionally omitted here:

- **No amendment loop.** If Phase 2 finds the protocol inadequate, it
  registers the gap and continues. The operator's option is to redo
  Phase 1 from scratch; no implicit "amend" path that would
  invalidate pre-registration discipline.
- **No optional inter-phase Zenodo deposit.** Pre-registration of the
  handoff is the operator's responsibility outside the skill, if they
  want it.
- **No coexistence with monolithic.** v3.0.0 replaces v2.23.x; no
  `--biphasic` opt-in flag, no fallback.
- **No operator review prompt in Phase 2.** Phase 2 produces the
  artifact and stops. The gates encode the review.

These removals are the user's explicit course-correction:
*"CHEGA DE COMPLICAR! É só gerar o artigo pronto para publicar no
Zenodo."*

## Build order (F21 phases)

| Phase | Deliverable |
|---|---|
| **A (this)** | This design doc + `schemas/handoff-v1.schema.json` + the three new gate specs above |
| B | Phase 1 skill manifest (SKILL.md scoped to Phase 1) |
| C | Phase 2 skill manifest + entry point |
| D | Implementation of the three new gates |
| E | Implementation of Phase 2 retrieval + extraction-with-source-mapping pipeline |
| F | Migration of `search_orchestrator.py`, `screening_pipeline.py`, `generate_assessment.py` to fit the two phases |
| G | Tests + dogfood + v3.0.0 release |
