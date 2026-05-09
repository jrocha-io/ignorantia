#!/usr/bin/env python3
"""Decisão 19 vocabulary check — Fix 10 of RS-42 dogfood remediation,
expanded by Fix 19 (RS-42 third wave).

Decisão 19 forbids skill-internal meta-discourse from leaking into the
artifact voice. RS-42 Mark 4 (v2.23.2 dogfood) showed two new failure
classes that Fix 10 did not catch:

* **Skill-internal taxonomy** appearing literal in deposited artifacts:
  ``Tier 1 / Tier 2``, ``FALLBACK_MD``, ``KEY → PROXY → FALLBACK_MD``,
  ``DD-6``, ``cascata Tier 0``. These are operational labels the skill
  uses to organise execution — they have no place in a scientific paper
  or pre-registered protocol.
* **Meta-project bleed-through**: ``projeto subjacente``,
  ``as outras 41 revisões``, ``função declaratória / função instrumental``,
  ``design_foundational``. A reviewer reading the artifact blind should
  not learn that the paper is part of a 42-review workflow.

Fix 19 also widens the **scope** of the check: instead of running only
against ``manuscript.tex`` it now scans every depositable artifact
(``.md`` / ``.tex`` / ``.html``) in a deposit directory via ``--all``.
The protocol that ships in the Zenodo zip is just as much a public
artifact as the manuscript — and that is precisely where the worst
leakage was found.

Public surface:

1. ``find_violations(text, *, is_latex=False)`` — pure function for tests
   and other Python callers.
2. ``find_violations_in_directory(root)`` — walk a deposit directory,
   return a mapping of file → violations.
3. CLI ``python3 scripts/check_decision_19_vocabulary.py <path>`` —
   single-file mode, exits 2 on any violation.
4. CLI ``python3 scripts/check_decision_19_vocabulary.py --all <dir>`` —
   directory mode, exits 2 if any file in the deposit has any violation.

The check operates on the **body** of the artifact only — LaTeX preamble
(everything up to ``\\begin{document}``) is stripped so version-bearing
``\\usepackage[...]`` lines don't false-positive.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Sidecar filename — parallel to ``assessment_gate.json`` (Fix 9) and
# ``pipeline_invariants_gate.json`` (Fix 11). All three sidecars live in
# the deposit directory and are inspected by downstream packagers via a
# chained shell ``&&``.
_GATE_SIDECAR_FILENAME = "vocabulary_gate.json"
_GATE_EXIT_CODE = 2

# ---------------------------------------------------------------------------
# Forbidden vocabulary (Decisão 19; expanded in v2.23.1 by Fix 10 and in
# v2.23.3 by Fix 19 — RS-42 Mark 4 regression patterns).
# ---------------------------------------------------------------------------
#
# Each entry is (compiled regex, human-readable label, why-it-matters).
# Patterns are anchored to whole-word boundaries where appropriate to
# minimise false-positives. They are tested against the artifact body
# *after* preamble stripping, so LaTeX package names like
# ``\usepackage[utf8]{inputenc}`` don't trip them.

_FORBIDDEN: tuple[tuple[re.Pattern[str], str, str], ...] = (
    # SemVer rhetoric — academic prose says "future work", not "v1.1.0".
    (
        re.compile(r"\bv\d+\.\d+\.\d+\b"),
        "semver-version-tag",
        "academic prose should say 'future work' / 'subsequent investigation', "
        "not 'v1.0.0' / 'v1.1.0' — that is software-versioning rhetoric.",
    ),
    # Internal procedural references — leaks the protocol-as-checklist mode.
    (
        re.compile(r"\bDecis[ãa]o\s+\d+\b", re.IGNORECASE),
        "decision-number-reference",
        "'Decisão N' references the skill's internal protocol numbering. "
        "Artifact voice attributes methodological choices to the researcher, "
        "not to a numbered checklist item.",
    ),
    # Design Decisions — internal skill numbering distinct from "Decisão N".
    (
        re.compile(r"\bDD-\d+\b"),
        "design-decision-reference",
        "'DD-N' is the skill's internal design-decision numbering. "
        "Translate the rationale into prose instead of citing the label.",
    ),
    # Skill-internal classification taxonomy.
    (
        re.compile(r"\bCategoria\s+[ABC]\b"),
        "category-classification",
        "'Categoria A' / 'Categoria B' is the skill's CoI mitigation taxonomy. "
        "Use prose descriptions of mitigations instead of taxonomic labels.",
    ),
    # Skill-internal database tiering. Fix 19 — RS-42 Mark 4 leaked these
    # straight into the protocol and the manuscript Methods section.
    (
        re.compile(r"\bTier\s*[012]\b"),
        "tier-tiering-label",
        "'Tier 0/1/2' is the skill's internal database-access cascade label. "
        "Scientific prose says 'open access' / 'subscription' / 'paywall'.",
    ),
    # FALLBACK_MD / KEY → PROXY cascade — internal mode labels.
    (
        re.compile(r"\bFALLBACK_MD\b"),
        "fallback-mode-label",
        "'FALLBACK_MD' is an internal mode label for paywall-without-credential "
        "handling. Prose should describe the gap report deliverable, not the mode.",
    ),
    (
        re.compile(r"\bKEY\s*(?:→|->)\s*PROXY\b"),
        "key-proxy-cascade",
        "'KEY → PROXY → FALLBACK_MD' is the skill's internal credential cascade. "
        "Translate to plain language: 'institutional credential, then proxy, then "
        "manual citation list'.",
    ),
    # Literal JSON / metadata field names leaking into prose.
    (
        re.compile(
            r"\b(review_purpose|review_type|purpose_per_stage|"
            r"human_oversight|authors_responsible|execution_method|"
            r"tier1_databases|tier2_paywall)\b"
        ),
        "metadata-field-name",
        "literal JSON/metadata field names belong in the package metadata, "
        "not in academic prose. Translate to natural language.",
    ),
    # review_purpose enum values — leak the skill's classification taxonomy.
    (
        re.compile(r"\bdesign[_-](foundational|validation|decision)\b"),
        "review-purpose-enum",
        "'design_foundational' / 'design_validation' are review_purpose enum "
        "values used internally to classify the review type. Use a prose "
        "description of the review's purpose instead of the literal token.",
    ),
    # Meta-project bleed-through (Fix 19, RS-42 Mark 4) — the artifact
    # narrates the broader 42-review workflow it belongs to.
    (
        re.compile(r"\bprojeto\s+subjacente\b", re.IGNORECASE),
        "meta-project-reference",
        "'projeto subjacente' refers to the broader workflow this artifact "
        "is part of. A reviewer reading the deposit blind should not need to "
        "know about other reviews — declare the specific project of CoI "
        "concern by name (e.g. 'Ler e Escrever / EMAI'), not as 'subjacente'.",
    ),
    (
        re.compile(r"\boutr[ao]s?\s+\d{1,3}\s+(revis[õo]es|estudos)\b", re.IGNORECASE),
        "sibling-reviews-count",
        "phrasings like 'as outras 41 revisões' or 'outros 12 estudos do "
        "autor' narrate the workflow, not the science. Each artifact stands "
        "on its own; cross-references between deposited artifacts go in the "
        "README, not in the manuscript body.",
    ),
    (
        re.compile(
            r"\bfun[çc][ãa]o\s+(declarat[óo]ria|instrumental)\b",
            re.IGNORECASE,
        ),
        "coi-function-split",
        "'função declaratória vs. função instrumental' is the skill's "
        "internal taxonomy for CoI mitigation. Describe the mitigation in "
        "natural language; do not reproduce the taxonomy label.",
    ),
    # Skill brand (kept here for completeness — already covered by v2.8.0
    # test, but consolidated under Decisão 19 for one-stop checking).
    (
        re.compile(r"\bignorantia\b", re.IGNORECASE),
        "skill-brand",
        "the artifact voice is the researcher's, not the skill's. "
        "The skill name must not appear anywhere in the artifact body.",
    ),
)

# ---------------------------------------------------------------------------
# Body extraction (skip LaTeX preamble; HTML kept as-is)
# ---------------------------------------------------------------------------

_LATEX_BEGIN_DOC = re.compile(r"\\begin\{document\}")


def _extract_body(text: str, *, is_latex: bool) -> str:
    """Return the manuscript body for vocabulary checking.

    For LaTeX files, strip everything up to and including
    ``\\begin{document}`` so ``\\usepackage[utf8]{inputenc}`` and similar
    preamble lines don't false-positive on the version-tag pattern.
    For HTML / Markdown / plain text, return as-is.
    """
    if not is_latex:
        return text
    match = _LATEX_BEGIN_DOC.search(text)
    if match is None:
        return text
    return text[match.end() :]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Violation:
    """One occurrence of a forbidden phrase in the manuscript body."""

    label: str
    matched_text: str
    line_number: int
    why: str


def find_violations(text: str, *, is_latex: bool = False) -> list[Violation]:
    """Scan ``text`` and return all Decisão 19 vocabulary violations.

    Args:
        text: Artifact content (.tex, .html, .md, plain).
        is_latex: When ``True``, strip preamble before scanning so
            ``\\usepackage`` lines don't false-positive on version tags.

    Returns:
        List of :class:`Violation` records, in document order. Empty
        list when the text is clean.
    """
    body = _extract_body(text, is_latex=is_latex)
    # Track preamble offset so reported line numbers map back to the
    # original document.
    preamble_offset = text[: len(text) - len(body)].count("\n") if is_latex else 0

    violations: list[Violation] = []
    for pattern, label, why in _FORBIDDEN:
        for match in pattern.finditer(body):
            line_number = body[: match.start()].count("\n") + 1 + preamble_offset
            violations.append(
                Violation(
                    label=label,
                    matched_text=match.group(0),
                    line_number=line_number,
                    why=why,
                )
            )
    violations.sort(key=lambda v: (v.line_number, v.label))
    return violations


# Extensions scanned by ``find_violations_in_directory``. Anything else
# (CSV, JSON, SVG, ZIP, binary) is left out — the gate's job is prose,
# not data.
_SCAN_EXTENSIONS: frozenset[str] = frozenset({".md", ".tex", ".latex", ".html", ".htm"})


def find_violations_in_directory(root: Path) -> dict[Path, list[Violation]]:
    """Walk ``root`` recursively, scanning every prose artifact.

    The deposit artifacts that need checking are the manuscript
    (``.tex`` / ``.html``), the protocol (``.md``), and the auxiliary
    Markdown files that ship with the Zenodo zip — README, compliance
    checklist, AI declaration, venue suggestions, the auto-assessment.
    Data files (CSV, JSON), figures (SVG, PDF) and the package archive
    itself are skipped.

    Args:
        root: Deposit directory (or any subtree containing artifacts).

    Returns:
        Mapping from artifact path to its violations, in stable
        path-sorted order. Files with zero violations are omitted from
        the mapping.
    """
    findings: dict[Path, list[Violation]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _SCAN_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        violations = find_violations(text, is_latex=_is_latex(path))
        if violations:
            findings[path] = violations
    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(path: Path, violations: list[Violation]) -> str:
    """Render a human-readable failure report."""
    lines = [f"Decisão 19 vocabulary check FAILED for {path}", ""]
    for v in violations:
        lines.append(f"  L{v.line_number}  [{v.label}]  '{v.matched_text}'")
        lines.append(f"     why: {v.why}")
    lines.append("")
    lines.append(f"Total: {len(violations)} violation(s)")
    return "\n".join(lines)


def _is_latex(path: Path) -> bool:
    return path.suffix.lower() in {".tex", ".latex"}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code (0 = clean, 2 = violations).

    Two modes:

    * Single-file: ``check_decision_19_vocabulary.py <path>``.
    * Directory: ``check_decision_19_vocabulary.py --all <dir>``.
      Scans every ``.md`` / ``.tex`` / ``.html`` file under the given
      directory and aggregates the report.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Verify a deposited artifact (or a whole deposit directory) "
            "for Decisão 19 vocabulary leakage."
        )
    )
    parser.add_argument(
        "path",
        type=Path,
        help=(
            "Path to a single artifact (manuscript.tex, protocol.md, etc.) "
            "or to a deposit directory when --all is set."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Treat <path> as a deposit directory and scan every prose "
            "artifact (.md/.tex/.html) recursively."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-violation report; print only the summary.",
    )
    parser.add_argument(
        "--gate-sidecar",
        action="store_true",
        help=(
            "Emit ``vocabulary_gate.json`` into the deposit directory, "
            "parallel to ``assessment_gate.json`` (Fix 9) and "
            "``pipeline_invariants_gate.json`` (Fix 11). Requires --all."
        ),
    )
    parser.add_argument(
        "--no-gate",
        action="store_true",
        help=(
            "Compute and (with --gate-sidecar) write the report, but do "
            "not exit non-zero on violations. Triage / debug only — "
            "must never be set in production packaging flows."
        ),
    )
    args = parser.parse_args(argv)

    if args.gate_sidecar and not args.all:
        print("ERROR: --gate-sidecar requires --all", file=sys.stderr)
        return 1

    if args.all:
        return _main_all(
            args.path,
            quiet=args.quiet,
            gate_sidecar=args.gate_sidecar,
            no_gate=args.no_gate,
        )
    return _main_single(args.path, quiet=args.quiet)


def _main_single(path: Path, *, quiet: bool) -> int:
    if not path.is_file():
        print(f"ERROR: {path} does not exist", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8", errors="replace")
    violations = find_violations(text, is_latex=_is_latex(path))

    if not violations:
        print(f"Decisão 19 vocabulary check PASSED for {path} (0 violations)")
        return 0

    if quiet:
        print(
            f"Decisão 19 vocabulary check FAILED for {path}: "
            f"{len(violations)} violation(s)",
            file=sys.stderr,
        )
    else:
        print(_format_report(path, violations), file=sys.stderr)
    return 2


def _main_all(
    root: Path,
    *,
    quiet: bool,
    gate_sidecar: bool = False,
    no_gate: bool = False,
) -> int:
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 1

    findings = find_violations_in_directory(root)
    total = sum(len(v) for v in findings.values())
    files_scanned = sum(
        1
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in _SCAN_EXTENSIONS
    )
    passed = not findings

    if gate_sidecar:
        sidecar_path = root / _GATE_SIDECAR_FILENAME
        sidecar_path.write_text(
            json.dumps(
                {
                    "passed": passed,
                    "total_violations": total,
                    "files_scanned": files_scanned,
                    "files_with_violations": [
                        str(p.relative_to(root)) for p in findings
                    ],
                    "violations_by_label": _aggregate_by_label(findings),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            f"Wrote {sidecar_path}  "
            f"(gate: {'PASS' if passed else 'FAIL'})"
        )

    if passed:
        print(
            f"Decisão 19 vocabulary check PASSED for deposit {root} "
            f"(0 violations across {files_scanned} file(s))"
        )
        return 0

    if quiet:
        print(
            f"Decisão 19 vocabulary check FAILED for deposit {root}: "
            f"{total} violation(s) across {len(findings)} file(s)",
            file=sys.stderr,
        )
    else:
        for path, violations in findings.items():
            print(_format_report(path, violations), file=sys.stderr)
        print(
            f"\nDeposit total: {total} violation(s) across "
            f"{len(findings)} file(s)",
            file=sys.stderr,
        )

    if no_gate:
        # Triage mode: report but do not enforce.
        print(
            "GATE NOT ENFORCED (--no-gate): proceeding despite violations. "
            "Production packaging must NEVER set this flag.",
            file=sys.stderr,
        )
        return 0
    return _GATE_EXIT_CODE


def _aggregate_by_label(
    findings: dict[Path, list[Violation]],
) -> dict[str, int]:
    """Count violations grouped by label, for the sidecar summary."""
    counts: dict[str, int] = {}
    for vlist in findings.values():
        for v in vlist:
            counts[v.label] = counts.get(v.label, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    sys.exit(main())
