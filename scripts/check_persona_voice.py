#!/usr/bin/env python3
"""Persona-voice heuristic check — Fix 12 of RS-42 dogfood remediation.

Decisão 20 prescribes an academic impersonal voice that describes the
*method applied to the problem*, not the *execution of the pipeline*.
The dogfood RS-42 disasters (2026-05-08) showed that Claude treats
Decisão 20 as advisory and writes pipeline-execution narration anyway —
``Phase 3 invocou search_orchestrator.py``, ``cascata KEY → PROXY →
FALLBACK_MD``, ``Decisão 23 obrigatória``, etc.

The Decisão 19 vocabulary checker (Fix 10) catches the brand-leakage
class — ``v1.0.0``, ``Decisão N``, ``Categoria A``, JSON field names.
This module catches the *complementary* class: tooling-narration
vocabulary that isn't a single banned word but a phrasing pattern.

Because voice quality is qualitative, this checker is **advisory by
default**: it emits warnings to stdout and exits 0 unless ``--strict``
is passed (then exit 2 on any warning). The advisory mode is meant to
be consulted during the Fase 7 writing loop; the strict mode is meant
to be chained before final packaging.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Heuristic patterns
# ---------------------------------------------------------------------------
#
# Each entry catches a tooling-narration pattern that the dogfood
# transcripts showed leaking into manuscript prose. Patterns are
# deliberately tuned for high precision (low false positives) at the
# cost of some recall — false negatives can be added by extending this
# tuple.

_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    # "Phase N" / "Fase N" — pipeline-stage references in prose.
    (
        re.compile(r"\b(Phase|Fase)\s+\d+\b"),
        "pipeline-stage-reference",
        "academic prose describes the method, not the pipeline stage. "
        "Replace 'Phase 3' / 'Fase 3' with 'a busca' / 'a triagem' / etc.",
    ),
    # Script names ending in .py inside prose.
    (
        re.compile(r"\b\w+\.py\b"),
        "script-name-in-prose",
        "script names belong in the README, not in the manuscript body. "
        "Describe what the method did, not which tool ran it.",
    ),
    # CLI flag-style tokens (``--flag``).
    (
        re.compile(r"\B--[a-z][a-z\-]+\b"),
        "cli-flag-in-prose",
        "CLI flags are tooling artefacts. Translate '--skip-tier0' into "
        "natural language about which databases were not consulted.",
    ),
    # File path placeholders like ``<output_dir>`` or ``<base>``.
    (
        re.compile(r"<[a-z_]+>"),
        "path-placeholder-in-prose",
        "file paths and placeholder tokens are tooling artefacts. "
        "Describe what is in the file, not where it is on disk.",
    ),
    # Pipeline-cascade rhetoric ``X → Y → Z`` with caps tokens.
    # Requires a real arrow (→ or ->) — em-dash between acronyms is
    # ordinary punctuation and would false-positive.
    (
        re.compile(r"\b[A-Z]{2,}\s*(?:→|->)\s*[A-Z]{2,}"),
        "cascade-arrow-rhetoric",
        "tier/cascade arrows like 'KEY → PROXY → FALLBACK_MD' are "
        "internal vocabulary. Describe the fallback strategy in prose.",
    ),
    # ``Tier N`` references.
    (
        re.compile(r"\bTier\s+\d+\b"),
        "tier-reference",
        "'Tier 1 / Tier 2' is the skill's internal classification. "
        "Use 'bases de acesso aberto' / 'bases comerciais' instead.",
    ),
    # ``DD-N`` design-decision references.
    (
        re.compile(r"\bDD-\d+\b"),
        "dd-reference",
        "'DD-N' is the skill's pre-Decisão registry. Manuscript voice "
        "doesn't cite design decisions by number.",
    ),
    # First-person execution narration ("invoquei", "rodei", "gerei").
    (
        re.compile(
            r"\b(invoquei|invoquei o|rodei|rodei o|executei|gerei|gerei o)\b",
            re.IGNORECASE,
        ),
        "first-person-execution",
        "first-person action verbs ('invoquei', 'rodei') describe "
        "pipeline execution, not the academic method. Use passive voice "
        "('foi conduzido', 'foi gerado').",
    ),
    # ``executável`` / ``orchestrator`` / ``pipeline executável`` etc.
    (
        re.compile(
            r"\b(orchestrator|search_orchestrator|pipeline\s+execut[áa]vel|"
            r"subprocess\s+long-running)\b",
            re.IGNORECASE,
        ),
        "infrastructure-vocabulary",
        "'orchestrator' / 'pipeline executável' / 'subprocess' name "
        "infrastructure components. Describe the methodological action "
        "they perform, not the components themselves.",
    ),
)

# ---------------------------------------------------------------------------
# Body extraction (skip LaTeX preamble; HTML kept as-is)
# ---------------------------------------------------------------------------

_LATEX_BEGIN_DOC = re.compile(r"\\begin\{document\}")


def _extract_body(text: str, *, is_latex: bool) -> tuple[str, int]:
    """Return (body, preamble_line_offset) for line-number reporting."""
    if not is_latex:
        return text, 0
    match = _LATEX_BEGIN_DOC.search(text)
    if match is None:
        return text, 0
    body = text[match.end() :]
    offset = text[: match.end()].count("\n")
    return body, offset


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Warning_:  # noqa: N801 — `Warning` shadows builtins.Warning
    """Heuristic warning record for a tooling-narration pattern."""

    label: str
    matched_text: str
    line_number: int
    why: str


def find_warnings(text: str, *, is_latex: bool = False) -> list[Warning_]:
    """Scan ``text`` and return all persona-voice heuristic warnings.

    Args:
        text: Manuscript content.
        is_latex: When ``True``, strip LaTeX preamble before scanning.

    Returns:
        List of :class:`Warning_` records in document order.
    """
    body, preamble_offset = _extract_body(text, is_latex=is_latex)
    warnings: list[Warning_] = []
    for pattern, label, why in _PATTERNS:
        for match in pattern.finditer(body):
            line_number = body[: match.start()].count("\n") + 1 + preamble_offset
            warnings.append(
                Warning_(
                    label=label,
                    matched_text=match.group(0),
                    line_number=line_number,
                    why=why,
                )
            )
    warnings.sort(key=lambda w: (w.line_number, w.label))
    return warnings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(path: Path, warnings: list[Warning_]) -> str:
    lines = [f"Persona-voice heuristic check: {len(warnings)} warning(s) in {path}", ""]
    for w in warnings:
        lines.append(f"  L{w.line_number}  [{w.label}]  '{w.matched_text}'")
        lines.append(f"     why: {w.why}")
    lines.append("")
    lines.append(
        "These are *heuristic* warnings. Voice quality is qualitative — "
        "review each match in context. Strict mode (--strict) treats "
        "any warning as a gate failure."
    )
    return "\n".join(lines)


def _is_latex(path: Path) -> bool:
    return path.suffix.lower() in {".tex", ".latex"}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Heuristic persona-voice check (Decisão 20). Advisory by default; "
            "use --strict to fail with exit 2 on any warning."
        )
    )
    parser.add_argument("path", type=Path, help="Path to a manuscript file.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 2 when any warning is emitted.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-warning output; print only the summary.",
    )
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"ERROR: {args.path} does not exist", file=sys.stderr)
        return 1

    text = args.path.read_text(encoding="utf-8", errors="replace")
    warnings = find_warnings(text, is_latex=_is_latex(args.path))

    if not warnings:
        print(f"Persona-voice check PASSED for {args.path} (0 warnings)")
        return 0

    out = sys.stderr if args.strict else sys.stdout
    if args.quiet:
        print(
            f"Persona-voice heuristic: {len(warnings)} warning(s) in {args.path}",
            file=out,
        )
    else:
        print(_format_report(args.path, warnings), file=out)

    return 2 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
