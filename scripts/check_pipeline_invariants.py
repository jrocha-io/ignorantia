#!/usr/bin/env python3
"""Pipeline invariants check — Fix 11 of RS-42 dogfood remediation.

Validates that the pipeline produced an artefact suitable for Zenodo
deposit. The dogfood RS-42 v1.0.0 (2026-05-08) shipped a package whose
``searches.json`` declared::

    "execution_method": "single_session_ad_hoc_web_search"

— meaning Claude executed five Google-SERP queries inside the chat
session instead of invoking ``search_orchestrator.py`` against the 14+
Tier-1/Tier-2 databases the SKILL.md prescribes. The package was
finalised anyway because nothing programmatic enforced that the pipeline
actually ran.

Fix 11 closes that loop with a small validator that inspects the
``searches.json`` and ``pipeline_summary.json`` (when present) and
rejects packages that admit ad-hoc execution without explicit operator
opt-in via ``--accept-ad-hoc-search``.

Invariants enforced:

I1. ``searches.json.execution_method`` is **not**
    ``single_session_ad_hoc_web_search`` — unless ``--accept-ad-hoc-search``
    is passed.
I2. ``searches.json`` references at least 3 distinct database identifiers
    (per ``searches.json.metadata.tier1_databases_actually_queried`` or,
    failing that, the legacy ``per_database`` array).
I3. When ``pipeline_summary.json`` exists, no step has ``status: ERROR``.

CLI: ``python3 scripts/check_pipeline_invariants.py <output_dir>``
exits 0 (clean), 2 (invariant violation), 1 (input not found / parse
error). Same exit-code contract as Fix 9 and Fix 10 so all three can
chain via ``&&``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AD_HOC_METHOD = "single_session_ad_hoc_web_search"
_MIN_DATABASES = 3
_INVARIANT_EXIT_CODE = 2
_INPUT_ERROR_EXIT_CODE = 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InvariantViolation:
    """A single failed invariant."""

    invariant_id: str
    message: str


def check(output_dir: Path, *, accept_ad_hoc: bool = False) -> list[InvariantViolation]:
    """Inspect ``output_dir`` and return all invariant violations.

    Args:
        output_dir: Directory containing ``searches.json`` (required) and
            optionally ``pipeline_summary.json``.
        accept_ad_hoc: When ``True``, suppress I1 (ad-hoc execution).
            Use only when the operator has reviewed the gap-report and
            consciously accepts a partial-coverage release.

    Returns:
        List of :class:`InvariantViolation`. Empty list = pass.
    """
    violations: list[InvariantViolation] = []

    searches_path = output_dir / "searches.json"
    if not searches_path.is_file():
        return [
            InvariantViolation(
                invariant_id="I0",
                message=(
                    f"{searches_path} does not exist; pipeline did not "
                    f"produce the search artefact."
                ),
            )
        ]

    try:
        searches = json.loads(searches_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [
            InvariantViolation(
                invariant_id="I0",
                message=f"{searches_path} is not valid JSON: {exc}",
            )
        ]

    # I1 — execution_method not ad-hoc unless explicitly accepted.
    metadata = searches.get("metadata", {}) if isinstance(searches, dict) else {}
    method = metadata.get("execution_method")
    if method == _AD_HOC_METHOD and not accept_ad_hoc:
        violations.append(
            InvariantViolation(
                invariant_id="I1",
                message=(
                    f"searches.json.metadata.execution_method == "
                    f"{_AD_HOC_METHOD!r}; this admits a single-session "
                    f"chat-bound execution that bypasses the orchestrator. "
                    f"Pass --accept-ad-hoc-search if you have reviewed the "
                    f"gap-report and consciously accept partial coverage; "
                    f"otherwise rerun the orchestrator before packaging."
                ),
            )
        )

    # I2 — at least N distinct databases queried.
    n_bases = _count_databases(searches)
    if n_bases < _MIN_DATABASES:
        violations.append(
            InvariantViolation(
                invariant_id="I2",
                message=(
                    f"only {n_bases} database(s) referenced in searches.json; "
                    f"PRISMA-2020 expects ≥{_MIN_DATABASES}. Add more bases "
                    f"or document the limitation explicitly."
                ),
            )
        )

    # I3 — no ERROR steps in pipeline_summary.json (when present).
    summary_path = output_dir / "pipeline_summary.json"
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            violations.append(
                InvariantViolation(
                    invariant_id="I3",
                    message=f"{summary_path} is not valid JSON: {exc}",
                )
            )
        else:
            errored = _failed_steps(summary)
            if errored:
                violations.append(
                    InvariantViolation(
                        invariant_id="I3",
                        message=(
                            f"pipeline_summary.json reports {len(errored)} "
                            f"ERROR step(s): {', '.join(errored)}. Resolve "
                            f"before packaging."
                        ),
                    )
                )

    return violations


def _count_databases(searches: object) -> int:
    """Return the number of distinct databases referenced in ``searches``.

    Accepts both the v3 layout (``metadata.tier1_databases_actually_queried``)
    and the legacy v2 layout (``per_database`` array of objects with a
    ``database`` field). Falls back to ``0`` if neither shape applies.
    """
    if not isinstance(searches, dict):
        return 0
    metadata = searches.get("metadata")
    if isinstance(metadata, dict):
        bases = metadata.get("tier1_databases_actually_queried")
        if isinstance(bases, list):
            return len({b for b in bases if isinstance(b, str)})
    per_db = searches.get("per_database")
    if isinstance(per_db, list):
        return len(
            {
                entry.get("database")
                for entry in per_db
                if isinstance(entry, dict) and entry.get("database")
            }
        )
    return 0


def _failed_steps(summary: object) -> list[str]:
    """Return the names of steps with ``status: ERROR`` in the summary."""
    if not isinstance(summary, dict):
        return []
    steps = summary.get("steps", [])
    if not isinstance(steps, list):
        return []
    return [
        entry.get("name", "<unnamed>")
        for entry in steps
        if isinstance(entry, dict) and entry.get("status") == "ERROR"
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(violations: list[InvariantViolation]) -> str:
    lines = ["Pipeline invariants check FAILED", ""]
    for v in violations:
        lines.append(f"  [{v.invariant_id}] {v.message}")
    lines.append("")
    lines.append(f"Total: {len(violations)} violation(s)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Verify a pipeline output_dir for finalisation invariants."
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Path to the SLR output directory (must contain searches.json).",
    )
    parser.add_argument(
        "--accept-ad-hoc-search",
        action="store_true",
        help=(
            "Suppress invariant I1 (ad-hoc execution_method). Use only when "
            "you have reviewed the gap-report and consciously accept a "
            "partial-coverage preview release. Never set in production runs."
        ),
    )
    args = parser.parse_args(argv)

    if not args.output_dir.is_dir():
        print(f"ERROR: {args.output_dir} is not a directory", file=sys.stderr)
        return _INPUT_ERROR_EXIT_CODE

    violations = check(args.output_dir, accept_ad_hoc=args.accept_ad_hoc_search)

    if not violations:
        print(f"Pipeline invariants check PASSED for {args.output_dir}")
        return 0

    # I0 (input parse failure) is reported but uses the input-error exit code
    # so callers can distinguish "your inputs are broken" from "your pipeline
    # didn't run correctly."
    if any(v.invariant_id == "I0" for v in violations):
        print(_format_report(violations), file=sys.stderr)
        return _INPUT_ERROR_EXIT_CODE

    print(_format_report(violations), file=sys.stderr)
    return _INVARIANT_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
