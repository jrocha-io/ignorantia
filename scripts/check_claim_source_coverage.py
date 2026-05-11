#!/usr/bin/env python3
"""Gate 5 — claim-to-source coverage.

Every substantive claim in the manuscript must be traceable to a
page/section of a real source paper. The mapping lives in
``<dir>/claim_to_source.json``; this gate verifies that **every
in-prose citation in ``manuscript.tex`` resolves to a row with a
non-empty ``source_anchor``**.

This is the structural fix for abstract-based hallucinated synthesis.
A claim like *"S08 reports 58× speedup"* only passes if
``claim_to_source.json`` contains an entry like::

    {
        "claim_id": "C-S08-001",
        "claim_text": "Reporta speed-up de 58× em screening assistido por IA.",
        "source_doi": "10.1234/example",
        "source_anchor": "p.7 §3.2 ¶2",
        "extracted_at": "2026-05-11T..."
    }

The anchor is captured during Phase 2 extraction; missing anchors
block the Zenodo deposit.

Exit codes:

* ``0`` — all substantive claims have a complete source mapping.
* ``1`` — input missing or malformed (manuscript or mapping file
  absent / unreadable).
* ``2`` — coverage gap; one or more claims lack a ``source_anchor``.

Sidecar: ``claim_source_gate.json`` with::

    {
        "passed": bool,
        "total_claims": int,
        "covered_claims": int,
        "uncovered_claim_ids": [str, ...],
        "missing_anchor_claim_ids": [str, ...]
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_GATE_SIDECAR_FILENAME = "claim_source_gate.json"
_GATE_EXIT_CODE = 2

# Inline citation key patterns. Two forms supported in Phase 2 output:
#   - ``\cite{key1,key2}`` (LaTeX biblatex/natbib)
#   - ``\citep{key}`` / ``\citet{key}`` (natbib)
# Numeric markers ``[N]`` are resolved through bibliography indirection;
# this gate operates on the LaTeX source where keys are explicit.
_CITE_PATTERN = re.compile(r"\\(?:cite[pt]?|parencite|textcite)\{([^}]+)\}")

# Substantive-claim heuristic: a claim is the sentence that contains a
# citation. We split the body on sentence terminators (.!?) and check
# each fragment for at least one cite. This is conservative — fragments
# without citations are not claims by definition, so they don't need a
# source mapping.


@dataclass(frozen=True, slots=True)
class Claim:
    """One in-prose citation occurrence (a sentence + the keys it cites)."""

    sentence_text: str
    line_number: int
    cited_keys: tuple[str, ...]


def _extract_body(text: str) -> tuple[str, int]:
    """Return ``(body, preamble_line_count)``. LaTeX preamble (before
    ``\\begin{document}``) is stripped so line numbers reported by the
    gate map back to the original file."""
    match = re.search(r"\\begin\{document\}", text)
    if not match:
        return text, 0
    body = text[match.end() :]
    preamble_lines = text[: match.end()].count("\n")
    return body, preamble_lines


def find_claims(manuscript_tex: str) -> list[Claim]:
    """Return the list of substantive claims (citation-bearing sentences)
    found in the manuscript body.

    Each claim's ``cited_keys`` is the union of keys appearing in any
    ``\\cite[pt]?`` command inside the sentence. Sentences without any
    citation are not claims by this definition.
    """
    body, preamble_offset = _extract_body(manuscript_tex)
    claims: list[Claim] = []
    # Split body into sentences. The regex keeps the terminator so
    # line offsets stay aligned.
    sentence_starts = [0]
    for m in re.finditer(r"[.!?]\s+", body):
        sentence_starts.append(m.end())
    for i, start in enumerate(sentence_starts):
        end = sentence_starts[i + 1] if i + 1 < len(sentence_starts) else len(body)
        sentence = body[start:end]
        cite_matches = _CITE_PATTERN.findall(sentence)
        if not cite_matches:
            continue
        keys: list[str] = []
        for match_text in cite_matches:
            keys.extend(k.strip() for k in match_text.split(",") if k.strip())
        line_number = body[:start].count("\n") + 1 + preamble_offset
        claims.append(
            Claim(
                sentence_text=sentence.strip()[:200],
                line_number=line_number,
                cited_keys=tuple(keys),
            )
        )
    return claims


def load_claim_to_source(path: Path) -> dict[str, dict]:
    """Read ``claim_to_source.json`` and return a ``{claim_id: row}`` index.

    Accepts both flat-list and indexed forms::

        [{"claim_id": "C-...", "source_doi": "10.x", "source_anchor": "p.7"}]

        {"C-...": {"source_doi": "10.x", "source_anchor": "p.7"}}
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {row["claim_id"]: row for row in raw if "claim_id" in row}
    if isinstance(raw, dict):
        return raw
    raise ValueError(
        f"claim_to_source.json must be a list of rows or an indexed dict; got {type(raw).__name__}"
    )


def check_coverage(
    claims: list[Claim], mapping: dict[str, dict]
) -> dict:
    """Compute the coverage report.

    A claim is *covered* iff every key it cites resolves to a mapping
    row AND that row has a non-empty ``source_anchor``.

    Returns the sidecar payload (without the ``passed`` field — caller
    decides exit code).
    """
    uncovered: list[str] = []
    missing_anchor: list[str] = []
    covered = 0
    for claim in claims:
        claim_covered = True
        for key in claim.cited_keys:
            row = mapping.get(key)
            if row is None:
                uncovered.append(key)
                claim_covered = False
                continue
            if not row.get("source_anchor"):
                missing_anchor.append(key)
                claim_covered = False
        if claim_covered:
            covered += 1
    return {
        "total_claims": len(claims),
        "covered_claims": covered,
        "uncovered_claim_ids": sorted(set(uncovered)),
        "missing_anchor_claim_ids": sorted(set(missing_anchor)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gate 5 — verify every in-prose citation in manuscript.tex "
            "resolves to a complete claim_to_source.json row."
        )
    )
    parser.add_argument(
        "deposit_dir",
        type=Path,
        help="Path to the deposit directory containing manuscript.tex "
        "and claim_to_source.json.",
    )
    parser.add_argument(
        "--manuscript-name",
        default="manuscript.tex",
        help="Filename of the manuscript LaTeX source (default: manuscript.tex).",
    )
    parser.add_argument(
        "--mapping-name",
        default="claim_to_source.json",
        help="Filename of the claim-to-source mapping (default: claim_to_source.json).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-claim diagnostics; emit only the summary line.",
    )
    args = parser.parse_args(argv)

    if not args.deposit_dir.is_dir():
        print(f"ERROR: {args.deposit_dir} is not a directory", file=sys.stderr)
        return 1

    manuscript = args.deposit_dir / args.manuscript_name
    mapping_file = args.deposit_dir / args.mapping_name
    if not manuscript.is_file():
        print(f"ERROR: {manuscript} not found", file=sys.stderr)
        return 1
    if not mapping_file.is_file():
        print(f"ERROR: {mapping_file} not found", file=sys.stderr)
        return 1

    try:
        text = manuscript.read_text(encoding="utf-8")
        mapping = load_claim_to_source(mapping_file)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"ERROR parsing inputs: {e}", file=sys.stderr)
        return 1

    claims = find_claims(text)
    report = check_coverage(claims, mapping)
    passed = (
        report["total_claims"] > 0
        and report["covered_claims"] == report["total_claims"]
    )
    report["passed"] = passed

    sidecar_path = args.deposit_dir / _GATE_SIDECAR_FILENAME
    sidecar_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if passed:
        print(
            f"Claim-to-source coverage check PASSED for {args.deposit_dir} "
            f"({report['covered_claims']}/{report['total_claims']} claims covered)"
        )
        return 0

    if not args.quiet:
        print(
            f"Claim-to-source coverage check FAILED for {args.deposit_dir}",
            file=sys.stderr,
        )
        if report["total_claims"] == 0:
            print(
                "  No substantive claims found in manuscript — the manuscript "
                "appears to have zero citations. Either the synthesis is "
                "missing or the citation format isn't recognised.",
                file=sys.stderr,
            )
        if report["uncovered_claim_ids"]:
            print(
                f"  {len(report['uncovered_claim_ids'])} cite key(s) missing "
                f"from claim_to_source.json:",
                file=sys.stderr,
            )
            for k in report["uncovered_claim_ids"][:20]:
                print(f"    - {k}", file=sys.stderr)
        if report["missing_anchor_claim_ids"]:
            print(
                f"  {len(report['missing_anchor_claim_ids'])} cite key(s) "
                f"in mapping but with empty source_anchor:",
                file=sys.stderr,
            )
            for k in report["missing_anchor_claim_ids"][:20]:
                print(f"    - {k}", file=sys.stderr)
    print(
        f"Wrote {sidecar_path}  (gate: {'PASS' if passed else 'FAIL'})",
        file=sys.stderr if not passed else sys.stdout,
    )
    return _GATE_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
