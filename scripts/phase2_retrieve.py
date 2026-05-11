#!/usr/bin/env python3
"""Phase 2 — full-text retrieval via OA resolver cascade.

Reads ``handoff.json`` from a bootstrapped run dir (output of
``phase2_init.py``). For every DOI in ``included_for_fulltext[]``,
walks an open-access resolver cascade to find a free, legitimate
full-text URL. Downloads the file to ``<run_dir>/sources/<doi-slug>.pdf``
(or ``.html``). Items that exhaust the cascade are registered in
``gap_report.md`` so the operator can attempt manual retrieval.

The cascade (in order):

1. **Unpaywall** (``api.unpaywall.org/v2/{doi}``) — the canonical OA
   locator. Required: ``--contact-email`` (or env
   ``IGNORANTIA_CONTACT_EMAIL``) — Unpaywall enforces a polite-pool.
2. **Open Access Button** (``api.openaccessbutton.org/find``) — second
   try; returns OA URL or reports unavailable.
3. **arXiv direct** for DOIs hosted on arXiv — derived from the DOI
   prefix ``10.48550``.

CORE and credential-proxy adapters are stubbed in this version
(``KEY``/``PROXY``) and will be added in a follow-up sub-phase. The
script never burns paywall; absent OA, the item goes to
``gap_report.md`` with attempted methods + status.

Usage::

    python3 scripts/phase2_retrieve.py runs/<run-id>/ \\
        --contact-email researcher@example.org

Exit codes:

* ``0`` — every included DOI was either downloaded or registered as a
  gap. Phase 2 can proceed to extraction.
* ``1`` — input error (run dir missing, handoff missing, no
  ``--contact-email`` provided).
* ``2`` — retrieval encountered an unrecoverable error (network down,
  cache corrupted). Different from "items not found" — that's not an
  error, that's a gap.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


_USER_AGENT = (
    "ignorantia-skill/3.0 (https://github.com/jrocha-io/ignorantia; "
    "mailto:{email})"
)
_DEFAULT_TIMEOUT_S = 15.0


# ── HTTP layer (injectable for tests) ──────────────────────────────────


@dataclass
class HttpResponse:
    status: int
    body: bytes
    content_type: str
    final_url: str


HttpFetcher = Callable[[str, dict[str, str]], HttpResponse]


def default_http_fetch(url: str, headers: dict[str, str]) -> HttpResponse:
    """Real network fetch via ``urllib.request``."""
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT_S) as resp:  # noqa: S310
        body = resp.read()
        return HttpResponse(
            status=resp.status,
            body=body,
            content_type=resp.headers.get("Content-Type", ""),
            final_url=resp.url,
        )


# ── DOI normalisation + filename slug ──────────────────────────────────


def normalise_doi(doi: str) -> str:
    """Strip the ``https://doi.org/`` prefix if present; lowercase."""
    doi = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
    return doi.lower()


def doi_to_filename_slug(doi: str) -> str:
    """Convert a DOI into a safe filename slug.

    ``10.1234/foo.bar`` → ``10-1234-foo-bar``. Reversible mapping isn't
    needed; the slug just has to be unique and filesystem-safe.
    """
    return re.sub(r"[^a-z0-9]+", "-", normalise_doi(doi)).strip("-")


# ── content sniffing ───────────────────────────────────────────────────


def is_pdf_bytes(body: bytes) -> bool:
    """Heuristic: does the byte buffer look like a PDF?"""
    return body[:5] == b"%PDF-"


def is_html_bytes(body: bytes, content_type: str) -> bool:
    lower_ct = content_type.lower()
    if "text/html" in lower_ct or "application/xhtml" in lower_ct:
        return True
    return body[:100].lstrip().lower().startswith((b"<!doctype html", b"<html"))


# ── resolvers ──────────────────────────────────────────────────────────


@dataclass
class ResolvedURL:
    """A single OA candidate URL from one resolver."""

    url: str
    license: str = ""
    host_type: str = ""
    is_best_oa: bool = False


@dataclass
class RetrievalAttempt:
    resolver: str
    success: bool
    url_tried: str = ""
    error: str = ""
    license: str = ""


def lookup_unpaywall(
    doi: str, *, contact_email: str, http: HttpFetcher
) -> tuple[ResolvedURL | None, RetrievalAttempt]:
    """Query Unpaywall's REST API for the best OA URL.

    Returns ``(url, attempt)``. ``url`` is None when the API said
    "no OA available" or returned an error.
    """
    encoded_doi = urllib.parse.quote(doi, safe="/")
    url = (
        f"https://api.unpaywall.org/v2/{encoded_doi}"
        f"?email={urllib.parse.quote(contact_email)}"
    )
    headers = {"User-Agent": _USER_AGENT.format(email=contact_email)}
    try:
        resp = http(url, headers)
    except urllib.error.HTTPError as e:
        return None, RetrievalAttempt(
            resolver="unpaywall", success=False, url_tried=url,
            error=f"HTTP {e.code}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, RetrievalAttempt(
            resolver="unpaywall", success=False, url_tried=url,
            error=str(e),
        )

    try:
        payload = json.loads(resp.body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None, RetrievalAttempt(
            resolver="unpaywall", success=False, url_tried=url,
            error="invalid JSON response",
        )

    best = payload.get("best_oa_location")
    if not best or not best.get("url_for_pdf"):
        return None, RetrievalAttempt(
            resolver="unpaywall", success=False, url_tried=url,
            error="no OA location",
        )
    resolved = ResolvedURL(
        url=best["url_for_pdf"],
        license=best.get("license", "") or "",
        host_type=best.get("host_type", "") or "",
        is_best_oa=True,
    )
    return resolved, RetrievalAttempt(
        resolver="unpaywall", success=True, url_tried=url,
        license=resolved.license,
    )


def lookup_oa_button(
    doi: str, *, contact_email: str, http: HttpFetcher
) -> tuple[ResolvedURL | None, RetrievalAttempt]:
    """Query Open Access Button for a free copy of the paper."""
    url = (
        f"https://api.openaccessbutton.org/find"
        f"?id={urllib.parse.quote(doi)}"
    )
    headers = {"User-Agent": _USER_AGENT.format(email=contact_email)}
    try:
        resp = http(url, headers)
    except urllib.error.HTTPError as e:
        return None, RetrievalAttempt(
            resolver="oa_button", success=False, url_tried=url,
            error=f"HTTP {e.code}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, RetrievalAttempt(
            resolver="oa_button", success=False, url_tried=url,
            error=str(e),
        )
    try:
        payload = json.loads(resp.body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None, RetrievalAttempt(
            resolver="oa_button", success=False, url_tried=url,
            error="invalid JSON response",
        )
    url_field = payload.get("url") or payload.get("data", {}).get("url")
    if not url_field:
        return None, RetrievalAttempt(
            resolver="oa_button", success=False, url_tried=url,
            error="no URL in response",
        )
    return (
        ResolvedURL(url=url_field, host_type="oa_button"),
        RetrievalAttempt(resolver="oa_button", success=True, url_tried=url),
    )


def lookup_arxiv(
    doi: str, *, contact_email: str, http: HttpFetcher
) -> tuple[ResolvedURL | None, RetrievalAttempt]:
    """If the DOI is hosted on arXiv (prefix ``10.48550/arxiv.``),
    derive the direct PDF URL without a lookup.
    """
    norm = normalise_doi(doi)
    match = re.match(r"^10\.48550/arxiv\.([\w./-]+)$", norm)
    if not match:
        return None, RetrievalAttempt(
            resolver="arxiv", success=False, url_tried="",
            error="not an arXiv DOI",
        )
    arxiv_id = match.group(1)
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return (
        ResolvedURL(url=pdf_url, host_type="repository", license="arxiv-nonexclusive"),
        RetrievalAttempt(resolver="arxiv", success=True, url_tried=pdf_url),
    )


# ── per-DOI retrieval ──────────────────────────────────────────────────


@dataclass
class RetrievalResult:
    doi: str
    status: str  # "downloaded" | "gap" | "error"
    file_path: Path | None = None
    file_kind: str = ""  # "pdf" | "html" | ""
    attempts: list[RetrievalAttempt] = field(default_factory=list)
    resolved_url: str = ""


def retrieve_one(
    doi: str,
    *,
    dest_dir: Path,
    contact_email: str,
    http: HttpFetcher,
    resolver_chain: list[Callable] | None = None,
    sleep_between_s: float = 0.0,
) -> RetrievalResult:
    """Walk the resolver cascade for one DOI. Returns the final outcome."""
    if resolver_chain is None:
        resolver_chain = [lookup_arxiv, lookup_unpaywall, lookup_oa_button]

    result = RetrievalResult(doi=doi, status="gap")
    norm = normalise_doi(doi)

    for resolver_fn in resolver_chain:
        resolved, attempt = resolver_fn(norm, contact_email=contact_email, http=http)
        result.attempts.append(attempt)
        if resolved is None:
            if sleep_between_s:
                time.sleep(sleep_between_s)
            continue
        # Try to fetch the resolved URL.
        try:
            resp = http(resolved.url, {"User-Agent": _USER_AGENT.format(email=contact_email)})
        except urllib.error.HTTPError as e:
            attempt.error = f"HTTP {e.code} on download"
            attempt.success = False
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            attempt.error = f"download failed: {e}"
            attempt.success = False
            continue
        # Validate content
        body = resp.body
        if is_pdf_bytes(body):
            slug = doi_to_filename_slug(doi)
            out_path = dest_dir / f"{slug}.pdf"
            out_path.write_bytes(body)
            result.status = "downloaded"
            result.file_path = out_path
            result.file_kind = "pdf"
            result.resolved_url = resolved.url
            return result
        if is_html_bytes(body, resp.content_type):
            slug = doi_to_filename_slug(doi)
            out_path = dest_dir / f"{slug}.html"
            out_path.write_bytes(body)
            result.status = "downloaded"
            result.file_path = out_path
            result.file_kind = "html"
            result.resolved_url = resolved.url
            return result
        attempt.error = (
            f"content sniff failed: {len(body)} bytes, "
            f"content-type {resp.content_type!r}"
        )
        attempt.success = False
        if sleep_between_s:
            time.sleep(sleep_between_s)

    return result


# ── gap_report assembly ────────────────────────────────────────────────


def append_gap_report(
    gap_report_path: Path, result: RetrievalResult, item: dict[str, Any]
) -> None:
    """Append one row to gap_report.md for an unrecovered DOI."""
    if not gap_report_path.is_file():
        gap_report_path.write_text(
            "# Gap Report\n\n"
            "Itens da lista de retrieval que não puderam ser obtidos.\n\n"
            "| DOI | Title | Expected Tier | Attempted Methods | Status |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    methods = ", ".join(a.resolver for a in result.attempts) or "—"
    last_err = result.attempts[-1].error if result.attempts else ""
    row = (
        f"| {item['doi']} "
        f"| {item.get('title', '')[:80]} "
        f"| {item.get('expected_access_tier', '')} "
        f"| {methods} "
        f"| {last_err or 'no OA found'} |\n"
    )
    with gap_report_path.open("a", encoding="utf-8") as f:
        f.write(row)


# ── retrieval log ──────────────────────────────────────────────────────


def append_retrieval_log(
    log_path: Path, doi: str, result: RetrievalResult
) -> None:
    """Append one JSON-lines record per DOI to retrieval.log."""
    record = {
        "doi": doi,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": result.status,
        "file_path": str(result.file_path) if result.file_path else None,
        "file_kind": result.file_kind,
        "resolved_url": result.resolved_url,
        "attempts": [
            {
                "resolver": a.resolver,
                "success": a.success,
                "url_tried": a.url_tried,
                "error": a.error,
                "license": a.license,
            }
            for a in result.attempts
        ],
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


# ── main pipeline ──────────────────────────────────────────────────────


def retrieve_all(
    run_dir: Path,
    *,
    contact_email: str,
    http: HttpFetcher | None = None,
    sleep_between_s: float = 0.5,
) -> dict[str, Any]:
    """Walk the included_for_fulltext list and retrieve each item.

    Returns a summary dict suitable for the orchestrator's state.json.
    """
    if http is None:
        http = default_http_fetch

    handoff_path = run_dir / "handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    sources_dir = run_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    gap_report_path = run_dir / "gap_report.md"
    log_path = run_dir / "logs" / "retrieval.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    n_downloaded = 0
    n_gap = 0
    n_total = len(handoff["included_for_fulltext"])

    for item in handoff["included_for_fulltext"]:
        doi = item["doi"]
        result = retrieve_one(
            doi,
            dest_dir=sources_dir,
            contact_email=contact_email,
            http=http,
            sleep_between_s=sleep_between_s,
        )
        append_retrieval_log(log_path, doi, result)
        if result.status == "downloaded":
            n_downloaded += 1
        else:
            n_gap += 1
            append_gap_report(gap_report_path, result, item)

    return {
        "total_included": n_total,
        "downloaded": n_downloaded,
        "gap": n_gap,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2 — full-text retrieval via OA resolver cascade. "
            "Walks the included_for_fulltext list and downloads each "
            "free, legitimate copy. Paywall items go to gap_report.md."
        )
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Path to the run dir bootstrapped by phase2_init.py.",
    )
    parser.add_argument(
        "--contact-email",
        default=os.environ.get("IGNORANTIA_CONTACT_EMAIL", ""),
        help="Contact email for Unpaywall's polite pool (env "
        "IGNORANTIA_CONTACT_EMAIL if not given).",
    )
    parser.add_argument(
        "--sleep-between-s",
        type=float,
        default=0.5,
        help="Delay between resolver / download calls (be polite to APIs).",
    )
    args = parser.parse_args(argv)

    if not args.run_dir.is_dir():
        print(f"ERROR: run dir not found: {args.run_dir}", file=sys.stderr)
        return 1
    if not (args.run_dir / "handoff.json").is_file():
        print(
            f"ERROR: {args.run_dir}/handoff.json not found. "
            f"Did you run phase2_init.py first?",
            file=sys.stderr,
        )
        return 1
    if not args.contact_email:
        print(
            "ERROR: --contact-email (or env IGNORANTIA_CONTACT_EMAIL) is "
            "required. Unpaywall enforces a polite-pool policy.",
            file=sys.stderr,
        )
        return 1

    try:
        summary = retrieve_all(
            args.run_dir,
            contact_email=args.contact_email,
            sleep_between_s=args.sleep_between_s,
        )
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: retrieval pipeline crashed: {e}", file=sys.stderr)
        return 2

    # Update phase2_state.json
    state_path = args.run_dir / "phase2_state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("completed_steps", []).append("retrieve")
        state["retrieval"] = summary
        state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(
        f"Retrieval complete: {summary['downloaded']} of "
        f"{summary['total_included']} items downloaded "
        f"({summary['gap']} in gap_report.md)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
