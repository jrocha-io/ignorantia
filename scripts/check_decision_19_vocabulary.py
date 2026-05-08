#!/usr/bin/env python3
"""Decisão 19 vocabulary check — Fix 10 of RS-42 dogfood remediation.

Decisão 19 forbids skill-internal meta-discourse from leaking into the
manuscript voice. The pre-existing test (``test_v28_eliminations.py``)
covers only the literal brand string ``ignorantia``. RS-42 v1.0.0
slipped through that test while still producing a manuscript that read
as engineering documentation, because the leakage was in a *family* of
terms — not the single brand string:

* SemVer rhetoric (``v1.0.0``, ``v1.1.0``, ``será corrigido em v1.1.0``)
* Internal procedural references (``Decisão 8 do protocolo``, ``Decisão 22``)
* Skill-internal classifications (``Categoria A``, ``Categoria B``)
* Literal JSON / metadata field names (``review_purpose``,
  ``purpose_per_stage``, ``execution_method``)

This module enumerates the forbidden phrases as a single allowlist-of-bans
and provides:

1. A pure function ``find_violations(text)`` that returns a list of
   ``Violation`` records — used by tests and other Python callers.
2. A CLI ``python3 scripts/check_decision_19_vocabulary.py <path>``
   that exits with code 2 when the file contains any violation,
   so it can be chained via shell ``&&`` like the Fix 9 gate.

The check operates on the **body** of the manuscript only — it
deliberately ignores LaTeX preamble (``\\begin{document}`` upward) so
package versions in ``\\usepackage[...]`` lines don't false-positive.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Forbidden vocabulary (Decisão 19, expanded in v2.23.1)
# ---------------------------------------------------------------------------
#
# Each entry is (compiled regex, human-readable label, why-it-matters).
# Patterns are anchored to whole-word boundaries where appropriate to
# minimise false-positives. They are tested against the manuscript body
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
        "Manuscript voice attributes methodological choices to the researcher, "
        "not to a numbered checklist item.",
    ),
    # Skill-internal classification taxonomy.
    (
        re.compile(r"\bCategoria\s+[ABC]\b"),
        "category-classification",
        "'Categoria A' / 'Categoria B' is the skill's CoI mitigation taxonomy. "
        "Use prose descriptions of mitigations instead of taxonomic labels.",
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
    # Skill brand (kept here for completeness — already covered by v2.8.0
    # test, but consolidated under Decisão 19 for one-stop checking).
    (
        re.compile(r"\bignorantia\b", re.IGNORECASE),
        "skill-brand",
        "the manuscript voice is the researcher's, not the skill's. "
        "The skill name must not appear anywhere in the manuscript body.",
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
        text: Manuscript content (.tex, .html, .md, plain).
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
    """CLI entry point. Returns the process exit code (0 = clean, 2 = violations)."""
    parser = argparse.ArgumentParser(
        description="Verify a manuscript file for Decisão 19 vocabulary leakage."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to manuscript.tex / manuscript.html / manuscript.md.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-violation report; print only the summary.",
    )
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"ERROR: {args.path} does not exist", file=sys.stderr)
        return 1

    text = args.path.read_text(encoding="utf-8", errors="replace")
    violations = find_violations(text, is_latex=_is_latex(args.path))

    if not violations:
        print(f"Decisão 19 vocabulary check PASSED for {args.path} (0 violations)")
        return 0

    if args.quiet:
        print(
            f"Decisão 19 vocabulary check FAILED for {args.path}: "
            f"{len(violations)} violation(s)",
            file=sys.stderr,
        )
    else:
        print(_format_report(args.path, violations), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
