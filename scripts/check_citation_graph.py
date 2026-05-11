#!/usr/bin/env python3
"""Gate 6 — citation graph integrity.

Verifies three properties of the citation graph between
``manuscript.tex`` and ``bibliography.bib``:

* **Check A — completeness**: every ``\\cite{key}`` in the manuscript
  resolves to a ``.bib`` entry with the same key.
* **Check B — no padding**: every ``.bib`` entry is cited at least
  once in the manuscript body. Unused entries indicate reference-list
  padding.
* **Check C — DOI liveness** (opt-in via ``--verify-dois``): each
  ``.bib`` entry with a ``doi = {…}`` field is resolved via Crossref
  (``api.crossref.org/works/{doi}``) with a short timeout. Results
  are cached in ``doi_verification_cache.json``. Items returning
  HTTP 404 (DOI not found) or flagged as retracted are blocked.

Exit codes:

* ``0`` — graph is complete, no padding, all DOIs live (when verified).
* ``1`` — input missing or malformed.
* ``2`` — graph has missing keys, unused keys, or dead/retracted DOIs.

Sidecar: ``citation_graph_gate.json`` with::

    {
        "passed": bool,
        "missing_keys": [...],
        "unused_keys": [...],
        "retracted_dois": [...],
        "unreachable_dois": [...]
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_GATE_SIDECAR_FILENAME = "citation_graph_gate.json"
_GATE_EXIT_CODE = 2

_CITE_PATTERN = re.compile(r"\\(?:cite[pt]?|parencite|textcite)\{([^}]+)\}")
_BIB_ENTRY_PATTERN = re.compile(
    r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,\s]+)\s*,",
    re.MULTILINE,
)
_BIB_DOI_FIELD = re.compile(
    r"^\s*doi\s*=\s*[{\"]([^}\"\n]+)[}\"]",
    re.IGNORECASE | re.MULTILINE,
)

_CROSSREF_API = "https://api.crossref.org/works/{doi}"
_USER_AGENT = (
    "ignorantia-gate/1.0 (https://github.com/jrocha-io/ignorantia; "
    "mailto:noreply@example.org)"
)


def extract_cited_keys(manuscript_tex: str) -> set[str]:
    """Return the set of cite-keys appearing anywhere in the manuscript."""
    body_start = manuscript_tex.find(r"\begin{document}")
    body = manuscript_tex[body_start:] if body_start != -1 else manuscript_tex
    keys: set[str] = set()
    for match in _CITE_PATTERN.findall(body):
        for k in match.split(","):
            k = k.strip()
            if k:
                keys.add(k)
    return keys


def parse_bib_entries(bibtex: str) -> dict[str, dict[str, str]]:
    """Return ``{key: {field_name: field_value}}`` for every ``@type{key,…}``
    entry in the ``.bib`` file.

    The parser is intentionally simple: it captures the type and key,
    plus any ``doi = {…}`` field needed for Check C. It doesn't try to
    fully parse BibTeX — that's overkill for the gate.
    """
    entries: dict[str, dict[str, str]] = {}
    matches = list(_BIB_ENTRY_PATTERN.finditer(bibtex))
    for i, m in enumerate(matches):
        key = m.group("key")
        entry_type = m.group("type").lower()
        # Locate this entry's body: from end of header to start of next
        # entry (or end of file).
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(bibtex)
        body = bibtex[body_start:body_end]
        fields: dict[str, str] = {"_type": entry_type}
        doi_match = _BIB_DOI_FIELD.search(body)
        if doi_match:
            fields["doi"] = doi_match.group(1).strip()
        entries[key] = fields
    return entries


def verify_doi(
    doi: str, *, cache: dict[str, dict], timeout: float = 5.0
) -> dict:
    """Resolve ``doi`` via Crossref. Returns ``{status, retracted, http_code, error}``.

    Cached results are returned without a network call. Cache survives
    process restarts via ``doi_verification_cache.json``.
    """
    if doi in cache:
        return cache[doi]
    url = _CROSSREF_API.format(doi=doi)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        message = payload.get("message", {})
        # Crossref flags retractions in ``update-to[*]/type == "retraction"``.
        retracted = any(
            u.get("type") == "retraction" for u in message.get("update-to", []) or []
        )
        result = {
            "status": "ok" if not retracted else "retracted",
            "retracted": retracted,
            "http_code": 200,
            "error": None,
        }
    except urllib.error.HTTPError as e:
        result = {
            "status": "not_found" if e.code == 404 else "http_error",
            "retracted": False,
            "http_code": e.code,
            "error": f"HTTP {e.code}",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        result = {
            "status": "unreachable",
            "retracted": False,
            "http_code": None,
            "error": str(e),
        }
    cache[doi] = result
    return result


def check_graph(
    manuscript_tex: str,
    bibtex: str,
    *,
    verify_dois: bool = False,
    cache: dict[str, dict] | None = None,
    sleep_between: float = 0.1,
) -> dict:
    """Compute the citation-graph report.

    Returns the sidecar payload (without ``passed`` — caller decides).
    """
    cited = extract_cited_keys(manuscript_tex)
    entries = parse_bib_entries(bibtex)
    bib_keys = set(entries)
    missing = sorted(cited - bib_keys)
    unused = sorted(bib_keys - cited)
    retracted: list[str] = []
    unreachable: list[str] = []
    if verify_dois:
        if cache is None:
            cache = {}
        for key, fields in sorted(entries.items()):
            doi = fields.get("doi")
            if not doi:
                continue
            result = verify_doi(doi, cache=cache)
            if result["retracted"]:
                retracted.append(doi)
            elif result["status"] in {"not_found", "unreachable", "http_error"}:
                unreachable.append(doi)
            if sleep_between:
                time.sleep(sleep_between)
    return {
        "missing_keys": missing,
        "unused_keys": unused,
        "retracted_dois": retracted,
        "unreachable_dois": unreachable,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gate 6 — verify the citation graph between manuscript.tex "
            "and bibliography.bib. Optionally pings Crossref for DOI liveness."
        )
    )
    parser.add_argument(
        "deposit_dir",
        type=Path,
        help="Path to the deposit directory containing manuscript.tex "
        "and bibliography.bib.",
    )
    parser.add_argument(
        "--manuscript-name",
        default="manuscript.tex",
        help="Filename of the manuscript LaTeX source.",
    )
    parser.add_argument(
        "--bibliography-name",
        default="bibliography.bib",
        help="Filename of the bibliography (BibTeX).",
    )
    parser.add_argument(
        "--verify-dois",
        action="store_true",
        help="Ping Crossref for each DOI in the bibliography. Slow; "
        "results cached in doi_verification_cache.json.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-item diagnostics; emit only the summary.",
    )
    args = parser.parse_args(argv)

    if not args.deposit_dir.is_dir():
        print(f"ERROR: {args.deposit_dir} is not a directory", file=sys.stderr)
        return 1

    manuscript = args.deposit_dir / args.manuscript_name
    bib = args.deposit_dir / args.bibliography_name
    if not manuscript.is_file():
        print(f"ERROR: {manuscript} not found", file=sys.stderr)
        return 1
    if not bib.is_file():
        print(f"ERROR: {bib} not found", file=sys.stderr)
        return 1

    cache_path = args.deposit_dir / "doi_verification_cache.json"
    cache: dict[str, dict] = {}
    if args.verify_dois and cache_path.is_file():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}

    report = check_graph(
        manuscript.read_text(encoding="utf-8"),
        bib.read_text(encoding="utf-8"),
        verify_dois=args.verify_dois,
        cache=cache,
    )

    if args.verify_dois:
        cache_path.write_text(
            json.dumps(cache, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    passed = (
        not report["missing_keys"]
        and not report["unused_keys"]
        and not report["retracted_dois"]
        and not report["unreachable_dois"]
    )
    report["passed"] = passed

    sidecar_path = args.deposit_dir / _GATE_SIDECAR_FILENAME
    sidecar_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if passed:
        print(
            f"Citation graph check PASSED for {args.deposit_dir}"
            + (" (with DOI verification)" if args.verify_dois else "")
        )
        return 0

    if not args.quiet:
        print(
            f"Citation graph check FAILED for {args.deposit_dir}",
            file=sys.stderr,
        )
        if report["missing_keys"]:
            print(
                f"  {len(report['missing_keys'])} cite key(s) not in bibliography:",
                file=sys.stderr,
            )
            for k in report["missing_keys"][:10]:
                print(f"    - {k}", file=sys.stderr)
        if report["unused_keys"]:
            print(
                f"  {len(report['unused_keys'])} bib entry/entries never cited "
                f"(reference padding):",
                file=sys.stderr,
            )
            for k in report["unused_keys"][:10]:
                print(f"    - {k}", file=sys.stderr)
        if report["retracted_dois"]:
            print(
                f"  {len(report['retracted_dois'])} retracted DOI(s):",
                file=sys.stderr,
            )
            for d in report["retracted_dois"]:
                print(f"    - {d}", file=sys.stderr)
        if report["unreachable_dois"]:
            print(
                f"  {len(report['unreachable_dois'])} DOI(s) unreachable / not found:",
                file=sys.stderr,
            )
            for d in report["unreachable_dois"]:
                print(f"    - {d}", file=sys.stderr)
    return _GATE_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
