"""Fix 20 / Phase F — operator-surface clean meta-gate.

After the audience-separation refactor (Fix 20), the operator-facing
surface (SKILL.md + references/*.xml shipped in the production zip +
assets/templates/*) must contain **zero developer-facing markers**.

Developer markers are:
- ``Fix \\d+`` (fix-history breadcrumbs)
- ``registrado em v\\d+\\.\\d+`` (versioning provenance)
- ``tests/integration/`` (test pointers — operator doesn't run tests)
- ``RS-42 dogfood`` (specific incident reference)
- ``Para quem mantém`` (maintainer-addressed blocks)
- ``Verificação mecânica`` (test-coverage pointer)
- ``Adendo de manutenção`` (maintenance notes)
- ``\\bv\\d+\\.\\d+\\.\\d+ falharia\\b`` (incident-replay annotations)

The meta-gate is **stricter than the deposit-wide vocabulary gate** in
some ways (catches `Fix N`, `tests/integration/`) and **less strict in
others** (allows pedagogical anti-pattern teachings — quotes like *"não
usar 'projeto subjacente'"* are legitimate operator instruction).

Why this gate exists: Fix 20 phase D rewrote SKILL.md to remove these
markers. Without a regression test, a maintainer can paste back a
`(registrado em v2.23.5, Fix 22)` annotation next sprint and re-create
the audience-mixing structural bug. The test pins the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


# ── pattern set ────────────────────────────────────────────────────────


DEVELOPER_MARKER_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bFix\s+\d+(?:\.\d+)?\b"), "fix-history-reference"),
    (re.compile(r"registrado em v\d+\.\d+"), "versioning-provenance"),
    (re.compile(r"tests/integration/"), "test-pointer"),
    (re.compile(r"RS-42 dogfood|RS-42 v\d|RS-42 Mark"), "incident-reference"),
    (re.compile(r"Para quem mantém"), "maintainer-block"),
    (re.compile(r"Verificação mecânica"), "test-coverage-pointer"),
    (re.compile(r"Adendo de manutenção"), "maintenance-aside"),
    (re.compile(r"\bv\d+\.\d+\.\d+ falharia\b"), "incident-replay"),
    # New patterns surfaced by the second-pass audit:
    (re.compile(r"^##\s+Hist[óo]rico\b", re.MULTILINE), "version-history-section"),
    (re.compile(r"\bCHANGELOG\.md\b"), "changelog-pointer"),
    (re.compile(r"\bdev-docs/"), "devdocs-pointer-in-operator-surface"),
    (re.compile(r"^>\s*\*\*Nota\s+v\d+\.\d+\.\d+:?\*\*", re.MULTILINE), "inline-version-note"),
    (re.compile(r"\bauditoria iterativa\b", re.IGNORECASE), "developer-audit-iteration"),
)


# ── files scanned ──────────────────────────────────────────────────────


def _operator_surface_files() -> list[Path]:
    """Files Claude-using-skill reads at runtime.

    Source of truth: the exact set the production packager ships, via
    ``scripts.build_production_package.resolve_allowlist``. This couples
    the meta-gate directly to whatever ends up in the zip — adding a
    new prose extension to the allowlist automatically widens the gate;
    removing one narrows it. No risk of audit-allowlist drift.
    """
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_production_package import resolve_allowlist

    # Limit to prose extensions. ``.toml`` (config) and ``.yaml``
    # (structured venue profile data) ship in the zip but are not read
    # as prose by the operator — they're consumed by build tooling or
    # data-loaders. Scanning them would flag false positives in
    # comments and structured fields.
    prose_exts = {".md", ".xml", ".html"}
    return [
        p
        for p in resolve_allowlist(ROOT)
        if p.suffix in prose_exts
    ]


# ── per-pattern scan ───────────────────────────────────────────────────


def _scan(text: str) -> dict[str, list[tuple[int, str]]]:
    """Return {label: [(line_no, matched_text), ...]} for any hits."""
    findings: dict[str, list[tuple[int, str]]] = {}
    for pattern, label in DEVELOPER_MARKER_PATTERNS:
        for m in pattern.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            findings.setdefault(label, []).append((line_no, m.group(0)))
    return findings


@pytest.fixture(scope="module")
def operator_files() -> list[Path]:
    files = _operator_surface_files()
    assert files, "no operator-surface files found — repo layout invalid?"
    return files


# ── contract per pattern (one test per pattern for diagnostic clarity) ─


def _assert_pattern_absent(
    files: list[Path], pattern: re.Pattern[str], label: str
) -> None:
    """Fail with the file paths + line numbers + matched text if any hit."""
    hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in pattern.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            rel = path.relative_to(ROOT)
            hits.append(f"  {rel}:{line_no}: {m.group(0)!r}")
    assert not hits, (
        f"Operator surface contains {len(hits)} developer marker(s) "
        f"of class '{label}' — Fix 20 phase F requires zero. "
        f"Move the developer detail to dev-docs/SKILL-HISTORY.md or "
        f"dev-docs/DECISIONS-REGISTRY.md and reword the operator-facing "
        f"prose to describe the rule without the marker.\n" + "\n".join(hits)
    )


def test_no_fix_history_references(operator_files: list[Path]) -> None:
    """Operator never reads about Fix N — that's developer history."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[0]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_versioning_provenance(operator_files: list[Path]) -> None:
    """Operator never reads ``registrado em v2.X.Y`` — version-provenance
    is developer-facing change-log metadata."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[1]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_test_pointers(operator_files: list[Path]) -> None:
    """Operator never reads ``tests/integration/`` — that's QA-facing."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[2]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_incident_references(operator_files: list[Path]) -> None:
    """Operator never reads about a specific dogfood incident."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[3]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_maintainer_blocks(operator_files: list[Path]) -> None:
    """Operator never reads ``**Para quem mantém esta skill:**`` blocks."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[4]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_test_coverage_pointers(operator_files: list[Path]) -> None:
    """Operator never reads ``**Verificação mecânica:**`` pointers."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[5]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_maintenance_asides(operator_files: list[Path]) -> None:
    """Operator never reads ``**Adendo de manutenção:**`` asides."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[6]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_incident_replay(operator_files: list[Path]) -> None:
    """Operator never reads ``v1.0.0 falharia com X violações``."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[7]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_version_history_section(operator_files: list[Path]) -> None:
    """Operator never reads ``## Histórico`` — version-trajectory tables
    are developer changelog material."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[8]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_changelog_pointer(operator_files: list[Path]) -> None:
    """Operator never reads ``CHANGELOG.md`` — it doesn't ship in the
    production zip and pointing at it from operator prose is dev-leak."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[9]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_devdocs_pointer(operator_files: list[Path]) -> None:
    """Operator surface should never point at ``dev-docs/`` — that's the
    developer-only tree, invisible to the operator at runtime."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[10]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_inline_version_note(operator_files: list[Path]) -> None:
    """Operator never reads ``> **Nota v2.X.Y:**`` blockquotes — these
    are version-trajectory annotations in rubric/spec files."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[11]
    _assert_pattern_absent(operator_files, pat, lbl)


def test_no_developer_audit_iteration(operator_files: list[Path]) -> None:
    """Operator never reads ``auditoria iterativa #N`` — that is dev
    sprint vocabulary. The scientific term "auditoria" (peer audit) by
    itself is allowed."""
    pat, lbl = DEVELOPER_MARKER_PATTERNS[12]
    _assert_pattern_absent(operator_files, pat, lbl)


# ── brand-leak gate: skill name in operator surface ────────────────────


# The skill brand is allowed in a tiny allowlist of files where the
# brand legitimately appears: SKILL.md frontmatter declares the skill
# name; artifact-vocabulary-policy.xml and persona-voice.xml teach
# Claude NOT to write the brand and must mention it as anti-pattern
# exemplar. Anywhere else in the operator surface, the brand must not
# appear — including templates the operator copies (e.g. an HTML
# manuscript template with ``ignorantia`` in the footer teaches the
# operator to brand-leak the deposited HTML).
_BRAND_ALLOWED_PATHS: frozenset[str] = frozenset({
    "SKILL.md",
    "SKILL-PHASE-2.md",                              # v3.0.0 biphasic — Cowork manifest
    "references/artifact-vocabulary-policy.xml",
    "assets/templates/persona-voice.xml",
    "docs/BIPHASIC-ARCHITECTURE.md",                 # v3.0.0 — CLI command references (/ignorantia, /ignorantia-execute)
})


def test_no_branded_deposit_filename_pattern(
    operator_files: list[Path],
) -> None:
    """The deposit filename pattern must not embed the skill brand.

    ``ignorantia-<area>-<topic>-v<X.Y.Z>.zip`` instructs the operator
    to embed the brand into the deposited Zenodo zip filename. A blind
    reviewer reading the deposit metadata would see the brand in the
    filename — that's a brand leak in deposit metadata, distinct from
    a brand leak in deposit prose, but with the same effect.

    The brand-strict gate (next test) allowlists SKILL.md as a whole
    because the frontmatter declares ``name: ignorantia`` (required by
    the Claude skill manifest convention) and the body teaches the
    brand as anti-pattern. But the ``ignorantia-<...>.zip`` filename
    pattern is *instructional* — it tells the operator to brand the
    deposit. That's not anti-pattern teaching; it's the leak.
    """
    pattern = re.compile(r"ignorantia-<[^>]+>", re.IGNORECASE)
    hits: list[str] = []
    for path in operator_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in pattern.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            rel = str(path.relative_to(ROOT))
            hits.append(f"  {rel}:{line_no}: {m.group(0)!r}")
    assert not hits, (
        f"The deposit filename convention embeds the skill brand. "
        f"The operator deposit must not be branded — Decisão 41 applies "
        f"to filenames as well as prose. Hits:\n" + "\n".join(hits)
    )


def test_skill_brand_only_in_allowlisted_files(
    operator_files: list[Path],
) -> None:
    """The skill brand ``ignorantia`` (case-insensitive) must not appear
    in operator-surface files except for the explicit allowlist that
    legitimately uses the brand (frontmatter declaration + anti-pattern
    teachings).

    A template that says ``<strong>ignorantia</strong>`` in an HTML footer
    teaches the operator to ship the brand in the deposited HTML — the
    very leak the deposit gate then catches downstream. Catch it at the
    source instead.
    """
    pattern = re.compile(r"\bignorantia\b", re.IGNORECASE)
    hits: list[str] = []
    for path in operator_files:
        rel = str(path.relative_to(ROOT))
        if rel in _BRAND_ALLOWED_PATHS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in pattern.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            hits.append(f"  {rel}:{line_no}: {m.group(0)!r}")
    assert not hits, (
        f"Skill brand 'ignorantia' appears in {len(hits)} operator-surface "
        f"location(s) outside the allowlist. The brand never appears in "
        f"deposited artifacts; any operator-surface mention is at risk of "
        f"being copied into output. Allowed: {sorted(_BRAND_ALLOWED_PATHS)}. "
        f"Hits:\n" + "\n".join(hits)
    )


# ── aggregate (so CI sees one summary if multiple classes fail) ────────


def test_full_operator_surface_clean(operator_files: list[Path]) -> None:
    """Aggregate report: every operator-surface file has zero developer
    markers across all 8 pattern classes. Equivalent to chaining the
    per-pattern tests above; kept separate to surface one summary line
    in CI rather than 8 individual failures."""
    total_hits = 0
    by_file: dict[str, dict[str, list[tuple[int, str]]]] = {}
    for path in operator_files:
        findings = _scan(path.read_text(encoding="utf-8", errors="replace"))
        if findings:
            rel = str(path.relative_to(ROOT))
            by_file[rel] = findings
            total_hits += sum(len(v) for v in findings.values())
    assert total_hits == 0, (
        f"Operator surface contains {total_hits} developer marker(s) "
        f"across {len(by_file)} file(s). Fix 20 phase F requires zero. "
        f"By file: {by_file}"
    )


# ── dev-docs preservation invariant ────────────────────────────────────


def test_dev_docs_history_preserves_developer_content() -> None:
    """The content cut from SKILL.md must still exist in dev-docs/.

    Phase D was destructive on the operator surface but lossless overall:
    every developer-facing section was copied to dev-docs/SKILL-HISTORY.md
    before being cut. This test pins that preservation invariant. If a
    future change removes dev-docs/SKILL-HISTORY.md or guts its content,
    this test trips."""
    history = ROOT / "dev-docs" / "SKILL-HISTORY.md"
    assert history.is_file(), (
        "Phase D preservation broken — dev-docs/SKILL-HISTORY.md missing"
    )
    body = history.read_text(encoding="utf-8")
    # Markers that MUST exist in history (one per developer-facing section
    # that was cut from SKILL.md).
    expected_markers = [
        "## Auditoria sistemática",
        "## Estado quantitativo da skill",
        "## Arquitetura v2.15-v2.18",
        "Verificação mecânica",
        "registrado em v",
        "Fix",
    ]
    missing = [m for m in expected_markers if m not in body]
    assert not missing, (
        f"dev-docs/SKILL-HISTORY.md is missing preserved markers: {missing}. "
        f"Phase D was supposed to copy SKILL.md to history before cutting."
    )


def test_dev_docs_decisions_registry_preserves_numbering() -> None:
    """The numbered Decisão registry must remain in dev-docs/ with all 39
    entries. Operator surface has no numbering by design; developer
    workflow (commits, PRs, issues) cites Decisão N via the registry."""
    registry = ROOT / "dev-docs" / "DECISIONS-REGISTRY.md"
    assert registry.is_file(), "dev-docs/DECISIONS-REGISTRY.md missing"
    body = registry.read_text(encoding="utf-8")
    # Spot-check: must register at least 30 numbered Decisões (39 expected
    # at time of phase C extraction; floor at 30 to allow for future
    # withdrawal/consolidation).
    n_decisoes = body.count("### Decisão ")
    assert n_decisoes >= 30, (
        f"dev-docs/DECISIONS-REGISTRY.md has only {n_decisoes} numbered "
        f"Decisão entries; expected ≥30 (preserved from pre-F20 SKILL.md)"
    )
