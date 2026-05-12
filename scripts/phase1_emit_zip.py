#!/usr/bin/env python3
"""Phase 1 — emit deposit ZIP with handoff + external-download artifacts.

The chat session (Phase 1) finishes by producing a single artifact the
operator can hand to Phase 2 (Cowork). Two pieces:

1. The schema-validated ``handoff-v<X.Y.Z>.json``.
2. A **download list** in formats consumable by external download
   managers (JDownloader, Free Download Manager, ``wget -i``, etc.),
   plus a human-readable index and a README.

Phase 1 itself does NOT download PDFs — that's a heavy operation
inappropriate for a chat session. Instead, this script resolves
OA URLs via Unpaywall + arXiv-direct (lightweight HTTP HEAD-style
lookups), packs the URL list, and stops. The operator downloads the
papers externally and dumps them into the Phase 2 run dir.

Output structure (ZIP)::

    ignorantia-phase1-<author>-<topic>-v<X.Y.Z>.zip
    ├── handoff-v<X.Y.Z>.json     # immutable contract for Phase 2
    ├── downloads.crawljob        # JDownloader-compatible JSON array
    ├── downloads.txt             # one URL per line (wget / FDM)
    ├── downloads-index.md        # human-readable table
    └── README.md                 # instructions for Phase 2 handoff

Usage::

    python3 scripts/phase1_emit_zip.py path/to/handoff.json \\
        --contact-email researcher@example.org \\
        --output-dir ./phase1-output/

Exit codes:

* ``0`` — ZIP written; some DOIs may have no resolved URL (those go
  into ``downloads-index.md`` as "manual lookup required" rows).
* ``1`` — input error (handoff missing/malformed, --contact-email
  absent).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))


# ── URL resolution (delegated to phase2_retrieve resolvers) ────────────


@dataclass
class ResolvedDownload:
    doi: str
    title: str
    year: int | None
    expected_tier: str
    resolved_url: str = ""
    resolver: str = ""
    license: str = ""
    error: str = ""


def resolve_download_list(
    items: list[dict[str, Any]],
    *,
    contact_email: str,
    http_fetch: Callable | None = None,
    sleep_between_s: float = 0.3,
) -> list[ResolvedDownload]:
    """For each included item, resolve an OA URL via the cascade.

    Reuses the resolver implementations from phase2_retrieve so Phase 1
    and Phase 2 stay in lockstep. Network-light: only Unpaywall + arXiv
    lookups (one HTTP per resolver per DOI), no PDF download.
    """
    import time as time_mod

    from phase2_retrieve import (
        default_http_fetch,
        lookup_arxiv,
        lookup_oa_button,
        lookup_unpaywall,
        normalise_doi,
    )

    if http_fetch is None:
        http_fetch = default_http_fetch

    resolvers = [lookup_arxiv, lookup_unpaywall, lookup_oa_button]
    out: list[ResolvedDownload] = []
    for item in items:
        doi = normalise_doi(item["doi"])
        result = ResolvedDownload(
            doi=doi,
            title=item.get("title", ""),
            year=item.get("year"),
            expected_tier=item.get("expected_access_tier", "unknown"),
        )
        for resolver in resolvers:
            try:
                url_obj, attempt = resolver(
                    doi, contact_email=contact_email, http=http_fetch
                )
            except Exception as e:  # noqa: BLE001
                continue
            if url_obj and url_obj.url:
                result.resolved_url = url_obj.url
                result.resolver = attempt.resolver
                result.license = url_obj.license
                break
            if sleep_between_s:
                time_mod.sleep(sleep_between_s)
        else:
            # No resolver succeeded
            last_error = (
                "no OA URL found via arXiv/Unpaywall/OAB; needs manual lookup"
                if result.expected_tier != "paywall_no_credential"
                else "paywalled — operator must use institutional credential "
                "or contact the author"
            )
            result.error = last_error
        out.append(result)
    return out


# ── artifact builders ──────────────────────────────────────────────────


def build_downloads_crawljob(resolved: list[ResolvedDownload]) -> str:
    """JDownloader ``.crawljob`` format. JDownloader accepts a JSON
    array of objects with at least ``text`` (URL) and optionally
    ``comment``, ``packageName``, ``filename``.
    """
    entries: list[dict[str, Any]] = []
    for r in resolved:
        if not r.resolved_url:
            continue
        comment = f"DOI: {r.doi}"
        if r.title:
            comment += f" — {r.title[:120]}"
        entries.append(
            {
                "text": r.resolved_url,
                "comment": comment,
                "packageName": "ignorantia-phase1-downloads",
                "autoStart": "TRUE",
                "filename": _suggest_filename(r),
            }
        )
    return json.dumps(entries, indent=2, ensure_ascii=False)


def _suggest_filename(r: ResolvedDownload) -> str:
    """Filename the operator's download manager should save under.

    Format: ``<doi-slug>.pdf``. Matches the slug Phase 2's
    ``phase2_retrieve.doi_to_filename_slug`` produces, so dropping the
    downloaded file into ``<run_dir>/sources/`` makes it auto-matchable.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", r.doi.lower()).strip("-")
    return f"{slug}.pdf"


def build_downloads_txt(resolved: list[ResolvedDownload]) -> str:
    """Plain URL list (one per line) for ``wget -i`` / FDM / curl loops.

    Lines starting with ``#`` are comments; they show the DOI of the
    URL on the line below, so a human inspecting the file can match
    URL → paper.
    """
    out: list[str] = []
    for r in resolved:
        if not r.resolved_url:
            continue
        out.append(f"# {r.doi} — {r.title[:80]}")
        out.append(r.resolved_url)
    return "\n".join(out) + "\n"


def build_downloads_index(resolved: list[ResolvedDownload]) -> str:
    """Human-readable Markdown table mapping DOI → URL or "needs manual"."""
    lines = [
        "# Download list — Phase 1 → operator → Phase 2",
        "",
        "Resolve each item below (descending order of automation):",
        "",
        "1. **Drop the file into `<run_dir>/sources/`** when you obtain it.",
        "2. The filename should follow the suggested slug so Phase 2 auto-matches.",
        "3. Items with no resolved URL need manual lookup via institutional "
        "credential, contact-author, or alternative repository.",
        "",
        "| # | DOI | Title | Year | Resolver | URL | Suggested filename |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(resolved, start=1):
        url_cell = r.resolved_url or f"_manual: {r.error}_"
        title_cell = (r.title or "")[:60].replace("|", "·")
        lines.append(
            f"| {i} "
            f"| `{r.doi}` "
            f"| {title_cell} "
            f"| {r.year or ''} "
            f"| {r.resolver or '—'} "
            f"| {url_cell} "
            f"| `{_suggest_filename(r)}` |"
        )
    n_resolved = sum(1 for r in resolved if r.resolved_url)
    lines.extend(
        [
            "",
            f"**Resolved**: {n_resolved} of {len(resolved)} items "
            f"({n_resolved * 100 // max(len(resolved), 1)}%).",
            "",
            "**Manual lookups remaining**: see rows marked _manual_.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_readme(
    resolved: list[ResolvedDownload], *, handoff_filename: str
) -> str:
    """Operator-facing instructions: how to get from Phase 1 ZIP to
    Phase 2 invocation."""
    n_total = len(resolved)
    n_resolved = sum(1 for r in resolved if r.resolved_url)
    n_manual = n_total - n_resolved
    return (
        "# Phase 1 deposit — instructions for Phase 2 handoff\n"
        "\n"
        "This ZIP is the output of the chat session (Phase 1). It "
        "contains the schema-validated handoff JSON plus three "
        "download lists so you can fetch the full-text papers using "
        "any tool of your choice.\n"
        "\n"
        "## What's inside\n"
        "\n"
        f"- `{handoff_filename}` — the Phase-1 → Phase-2 contract.\n"
        "- `downloads.crawljob` — JDownloader-compatible list "
        f"({n_resolved} items).\n"
        "- `downloads.txt` — plain URL list, one per line "
        "(use with `wget -i downloads.txt`, Free Download Manager, "
        "curl loop, etc.).\n"
        "- `downloads-index.md` — human-readable table mapping DOI → "
        "URL or *manual lookup*.\n"
        "\n"
        "## How to proceed to Phase 2\n"
        "\n"
        "1. **Create the run directory** on your local machine, e.g.:\n"
        "\n"
        "       mkdir -p ~/ignorantia-runs/<author-slug>-<topic>-v1.0.0/sources\n"
        "\n"
        "2. **Extract this ZIP** into the run directory:\n"
        "\n"
        "       unzip ignorantia-phase1-*.zip -d ~/ignorantia-runs/<run-id>/\n"
        "\n"
        "3. **Download the papers** using any of the three lists:\n"
        "\n"
        "       # JDownloader\n"
        "       cp downloads.crawljob ~/.jd/folderwatch/\n"
        "\n"
        "       # Free Download Manager: File → Import → downloads.txt\n"
        "\n"
        "       # wget loop\n"
        "       wget -i downloads.txt -P ~/ignorantia-runs/<run-id>/sources/\n"
        "\n"
        "    Save each PDF into `sources/` using the **suggested "
        "filename** from `downloads-index.md` so Phase 2 auto-matches.\n"
        "\n"
        f"4. **Resolve the manual items** ({n_manual} entries marked "
        "*manual* in `downloads-index.md`): institutional credential, "
        "library, contact-author, etc. Drop the PDFs into `sources/` "
        "with the suggested filename.\n"
        "\n"
        "5. **Invoke Phase 2** (Anthropic Cowork) on the populated "
        "run directory:\n"
        "\n"
        "       python3 scripts/phase2_orchestrator.py prepare \\\n"
        f"           ~/ignorantia-runs/<run-id>/{handoff_filename} \\\n"
        "           --output-dir ~/ignorantia-runs/ \\\n"
        "           --contact-email <your-email>\n"
        "\n"
        "       # cowork-Claude writes manuscript.tex etc.\n"
        "\n"
        "       python3 scripts/phase2_orchestrator.py finalize \\\n"
        "           ~/ignorantia-runs/<run-id>/\n"
        "\n"
        "Phase 2 will:\n"
        "\n"
        "- Use the PDFs you already dumped into `sources/` (local-first).\n"
        "- Fall back to HTTP retrieval for any missing items.\n"
        "- Read every paper, build claim-to-source mappings, "
        "compile manuscript, run 7 gates, and emit the Zenodo ZIP.\n"
        "\n"
        "## Phase 1 stats\n"
        "\n"
        f"- Total included for full-text: **{n_total}**\n"
        f"- URLs resolved automatically: **{n_resolved}**\n"
        f"- Manual lookups needed: **{n_manual}**\n"
    )


# ── ZIP assembly ───────────────────────────────────────────────────────


def derive_zip_name(handoff: dict[str, Any]) -> str:
    """Brand-free filename: ``<author-slug>-<title-slug>-v<X.Y.Z>.zip``.

    Imports phase2_init.derive_run_id to keep the slug logic in one place.
    """
    from phase2_init import derive_run_id

    return f"{derive_run_id(handoff)}-phase1.zip"


def emit_zip(
    handoff_path: Path,
    *,
    output_dir: Path,
    contact_email: str,
    http_fetch: Callable | None = None,
    sleep_between_s: float = 0.3,
) -> tuple[Path, list[ResolvedDownload]]:
    """Build the Phase-1 ZIP. Returns (zip_path, resolved_items)."""
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    resolved = resolve_download_list(
        handoff["included_for_fulltext"],
        contact_email=contact_email,
        http_fetch=http_fetch,
        sleep_between_s=sleep_between_s,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_name = derive_zip_name(handoff)
    zip_path = output_dir / zip_name
    if zip_path.exists():
        zip_path.unlink()

    crawljob = build_downloads_crawljob(resolved)
    plain = build_downloads_txt(resolved)
    index = build_downloads_index(resolved)
    readme = build_readme(resolved, handoff_filename=handoff_path.name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(handoff_path, arcname=handoff_path.name)
        zf.writestr("downloads.crawljob", crawljob)
        zf.writestr("downloads.txt", plain)
        zf.writestr("downloads-index.md", index)
        zf.writestr("README.md", readme)
    return zip_path, resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 1 — emit deposit ZIP with handoff + external-download "
            "artifacts (JDownloader / FDM / wget formats)."
        )
    )
    parser.add_argument("handoff", type=Path, help="Path to Phase 1 handoff JSON.")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("phase1-output"),
        help="Where to write the ZIP (default ./phase1-output/).",
    )
    parser.add_argument(
        "--contact-email",
        default=os.environ.get("IGNORANTIA_CONTACT_EMAIL", ""),
        help="Contact email for Unpaywall polite-pool (env "
        "IGNORANTIA_CONTACT_EMAIL fallback).",
    )
    parser.add_argument(
        "--sleep-between-s", type=float, default=0.3,
        help="Delay between Unpaywall lookups.",
    )
    args = parser.parse_args(argv)

    if not args.handoff.is_file():
        print(f"ERROR: handoff not found: {args.handoff}", file=sys.stderr)
        return 1
    if not args.contact_email:
        print(
            "ERROR: --contact-email (or env IGNORANTIA_CONTACT_EMAIL) is "
            "required. Unpaywall enforces a polite-pool policy.",
            file=sys.stderr,
        )
        return 1

    try:
        zip_path, resolved = emit_zip(
            args.handoff,
            output_dir=args.output_dir,
            contact_email=args.contact_email,
            sleep_between_s=args.sleep_between_s,
        )
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: failed to emit ZIP: {e}", file=sys.stderr)
        return 1

    n_total = len(resolved)
    n_resolved = sum(1 for r in resolved if r.resolved_url)
    print(
        f"Phase 1 ZIP written:\n"
        f"  path:     {zip_path}\n"
        f"  size:     {zip_path.stat().st_size:,} bytes\n"
        f"  items:    {n_total} included for full-text\n"
        f"  resolved: {n_resolved} URLs ({n_resolved * 100 // max(n_total, 1)}%)\n"
        f"  manual:   {n_total - n_resolved} entries need manual lookup\n"
        f"\n"
        f"Deliver this ZIP to the operator. See README.md inside the "
        f"ZIP for Phase 2 invocation."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
