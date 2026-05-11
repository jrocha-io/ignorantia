#!/usr/bin/env python3
"""Phase 2 entry point — validate handoff and bootstrap output directory.

This is the **single command** Phase 2 (Cowork) runs to start a
biphasic execution. It validates the handoff produced by Phase 1
(chat session) against the schema, recomputes the integrity hash, and
sets up the output directory layout that downstream scripts
(phase2_retrieve, phase2_extract, etc.) consume.

Usage::

    python3 scripts/phase2_init.py path/to/handoff-v1.0.0.json \\
        --output-dir runs/

After a successful run, the layout is::

    runs/<author-slug>-<area>-<topic>-v<X.Y.Z>/
        handoff.json              # immutable copy of input
        sources/                  # PDFs/HTMLs land here in Phase E2
        gates/                    # sidecar JSONs land here in Phase 2 final
        logs/                     # compile.log, retrieval.log, etc.
        extraction.csv            # initialised with header
        claim_to_source.json      # initialised as empty list
        gap_report.md             # initialised with header
        phase2_state.json         # progress tracker for orchestrator

Exit codes:

* ``0`` — handoff is valid, output dir created and bootstrapped.
* ``1`` — input error (handoff missing or unreadable).
* ``2`` — handoff schema-invalid or hash mismatch (Phase 2 must abort;
  operator should re-run Phase 1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "handoff-v1.schema.json"


def canonical_hash(handoff: dict[str, Any]) -> str:
    """SHA-256 of the handoff with the ``handoff_hash`` field removed.

    Matches the algorithm Phase 1 uses to seal the handoff. Sorted keys
    and tight separators canonicalise the JSON so the hash is stable.
    """
    copy = {k: v for k, v in handoff.items() if k != "handoff_hash"}
    raw = json.dumps(copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_handoff(
    handoff: dict[str, Any], schema_path: Path
) -> list[str]:
    """Return a list of human-readable validation error strings.

    Empty list = valid. The function tries ``jsonschema`` for full
    validation; if not installed, falls back to a minimal required-
    field check so Phase 2 still aborts on grossly malformed input.
    """
    errors: list[str] = []
    try:
        import jsonschema
    except ImportError:
        # Minimal fallback: check required top-level fields.
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        for field in schema.get("required", []):
            if field not in handoff:
                errors.append(f"missing required field: {field}")
        return errors

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for err in validator.iter_errors(handoff):
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return errors


def cross_check_included_against_screening(handoff: dict[str, Any]) -> list[str]:
    """Verify every DOI in ``included_for_fulltext[]`` has a positive
    final decision in ``screening.trace_per_doi``. The schema alone
    can't enforce this cross-reference; the gate must."""
    errors: list[str] = []
    included = {item["doi"] for item in handoff["included_for_fulltext"]}
    trace = handoff["screening"]["trace_per_doi"]
    for doi in sorted(included):
        if doi not in trace:
            errors.append(f"included DOI {doi!r} has no screening trace")
            continue
        decisions = trace[doi]
        if not decisions:
            errors.append(f"included DOI {doi!r} has empty screening trace")
            continue
        final = decisions[-1].get("decision")
        if final not in {"include", "borderline"}:
            errors.append(
                f"included DOI {doi!r} has final screening decision {final!r}; "
                f"expected 'include' or 'borderline'"
            )
    return errors


def slugify(text: str, *, max_len: int = 40) -> str:
    """Filename-safe slug. Used to derive output-dir name from handoff."""
    text = text.lower().strip()
    text = re.sub(r"[áàâãä]", "a", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[íìîï]", "i", text)
    text = re.sub(r"[óòôõö]", "o", text)
    text = re.sub(r"[úùûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len].rstrip("-") or "untitled"


def derive_run_id(handoff: dict[str, Any]) -> str:
    """Compute the output-dir name from handoff metadata.

    Format: ``<author-slug>-<title-slug>-v<version>``. **No skill brand
    in the filename** (Decisão 41 / Phase H invariant).
    """
    authors = handoff["protocol"].get("authors", [])
    author = authors[0]["name"] if authors else "anon"
    author_slug = slugify(author.split()[-1] if " " in author else author, max_len=20)
    title_slug = slugify(handoff["protocol"]["title"], max_len=40)
    version = handoff["metadata"]["skill_version"]
    return f"{author_slug}-{title_slug}-v{version}"


def bootstrap_output_dir(run_dir: Path, handoff: dict[str, Any]) -> None:
    """Create the subdirectory layout and initial empty artifacts."""
    for sub in ("sources", "gates", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    # Immutable handoff copy
    handoff_copy = run_dir / "handoff.json"
    handoff_copy.write_text(
        json.dumps(handoff, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # extraction.csv with header
    extraction_csv = run_dir / "extraction.csv"
    if not extraction_csv.exists():
        extraction_csv.write_text(
            "study_id,doi,title,year,venue,study_type,area,intervention,"
            "methods,findings,limitations,coi_declared,"
            "repro_package_available,claim_ids\n",
            encoding="utf-8",
        )

    # claim_to_source.json — empty list of mappings
    claim_to_source = run_dir / "claim_to_source.json"
    if not claim_to_source.exists():
        claim_to_source.write_text("[]\n", encoding="utf-8")

    # gap_report.md — header
    gap_report = run_dir / "gap_report.md"
    if not gap_report.exists():
        gap_report.write_text(
            "# Gap Report\n\n"
            "Itens da lista de retrieval que não puderam ser obtidos.\n\n"
            "| DOI | Title | Expected Tier | Attempted Methods | Status |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )

    # phase2_state.json — progress tracker
    state = run_dir / "phase2_state.json"
    state.write_text(
        json.dumps(
            {
                "phase": 2,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "handoff_hash": handoff["handoff_hash"],
                "n_included": len(handoff["included_for_fulltext"]),
                "completed_steps": ["init"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2 entry point. Validates a Phase 1 handoff and "
            "bootstraps the output directory for downstream scripts."
        )
    )
    parser.add_argument(
        "handoff_path",
        type=Path,
        help="Path to the handoff JSON produced by Phase 1.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs"),
        help="Parent directory under which the run dir will be created "
        "(default: ./runs/).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Override the handoff schema path (advanced).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing run directory. By default, "
        "phase2_init aborts if the target directory already exists "
        "(protects against accidental re-bootstrap).",
    )
    args = parser.parse_args(argv)

    if not args.handoff_path.is_file():
        print(f"ERROR: handoff not found: {args.handoff_path}", file=sys.stderr)
        return 1
    if not args.schema.is_file():
        print(f"ERROR: schema not found: {args.schema}", file=sys.stderr)
        return 1

    try:
        handoff = json.loads(args.handoff_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: handoff is not valid JSON: {e}", file=sys.stderr)
        return 1

    # Schema validation
    errors = validate_handoff(handoff, args.schema)
    if errors:
        print("ERROR: handoff fails schema validation:", file=sys.stderr)
        for e in errors[:20]:
            print(f"  - {e}", file=sys.stderr)
        print(
            "Phase 2 must abort. Re-run Phase 1 to produce a clean handoff.",
            file=sys.stderr,
        )
        return 2

    # Hash check (only if the field is present and schema validation passed)
    expected_hash = handoff.get("handoff_hash", "")
    actual_hash = canonical_hash(handoff)
    if expected_hash != actual_hash:
        print(
            f"ERROR: handoff_hash mismatch.\n"
            f"  declared: {expected_hash}\n"
            f"  recomputed: {actual_hash}\n"
            f"The handoff was modified after Phase 1 sealed it. Phase 2 "
            f"must abort.",
            file=sys.stderr,
        )
        return 2

    # Cross-check: included DOIs all have positive screening decisions.
    cross_errors = cross_check_included_against_screening(handoff)
    if cross_errors:
        print("ERROR: handoff cross-reference inconsistencies:", file=sys.stderr)
        for e in cross_errors[:20]:
            print(f"  - {e}", file=sys.stderr)
        return 2

    # All checks passed; bootstrap the run dir.
    run_id = derive_run_id(handoff)
    run_dir = args.output_dir / run_id
    if run_dir.exists() and not args.force:
        print(
            f"ERROR: run directory already exists: {run_dir}\n"
            f"Pass --force to overwrite, or use a different --output-dir.",
            file=sys.stderr,
        )
        return 1
    if run_dir.exists() and args.force:
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)

    bootstrap_output_dir(run_dir, handoff)

    n_included = len(handoff["included_for_fulltext"])
    n_bases = len(handoff["protocol"]["bases"])
    print(
        f"Phase 2 bootstrap OK\n"
        f"  run dir:       {run_dir}\n"
        f"  handoff hash:  {actual_hash[:16]}…\n"
        f"  included:      {n_included} DOI(s) for full-text retrieval\n"
        f"  bases:         {n_bases} declared\n"
        f"\n"
        f"Next: run `python3 scripts/phase2_retrieve.py {run_dir}` "
        f"to retrieve full-texts."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
