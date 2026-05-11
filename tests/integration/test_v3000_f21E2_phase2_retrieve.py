"""Fix 21 / Phase E2 — phase2_retrieve: OA-resolver cascade for full-text.

phase2_retrieve walks the ``included_for_fulltext[]`` list from the
handoff, queries each OA resolver in order, downloads the first
successful hit, and writes either the PDF/HTML to ``sources/`` or a
row to ``gap_report.md``.

These tests pin the contract using an in-memory ``HttpFetcher`` stub
so no network is touched. We verify:

- Each resolver (Unpaywall, OA Button, arXiv) extracts the expected
  URL from its response shape.
- The cascade short-circuits on the first success.
- Content sniffing routes PDFs to ``.pdf`` and HTML to ``.html``.
- Items that exhaust the cascade are written to ``gap_report.md``
  with attempted methods and last error.
- Network errors (HTTPError, URLError, timeout) don't crash the
  pipeline — they're recorded in the attempt log and the cascade
  moves on.
- The retrieval log captures one JSON-line record per DOI.
- Polite-pool email is mandatory and propagates into User-Agent and
  Unpaywall query.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


# ── http stub ──────────────────────────────────────────────────────────


def make_stub_http(responses: dict[str, tuple[int, bytes, str]]):
    """Build an HttpFetcher that returns canned responses for URL prefixes.

    Keys are URL prefixes. The first prefix that matches the requested
    URL wins. Each value is (status, body_bytes, content_type).
    """
    from phase2_retrieve import HttpResponse

    def fetch(url: str, headers: dict[str, str]):
        for prefix, (status, body, ct) in responses.items():
            if url.startswith(prefix):
                if status >= 400:
                    raise urllib.error.HTTPError(url, status, "stub", {}, None)
                return HttpResponse(status=status, body=body, content_type=ct, final_url=url)
        raise urllib.error.URLError(f"stub: no mock for {url}")

    return fetch


# ── DOI utils ──────────────────────────────────────────────────────────


def test_normalise_doi_strips_url_prefixes():
    from phase2_retrieve import normalise_doi

    assert normalise_doi("https://doi.org/10.1234/abc") == "10.1234/abc"
    assert normalise_doi("http://doi.org/10.1234/abc") == "10.1234/abc"
    assert normalise_doi("DOI:10.1234/abc") == "10.1234/abc"
    assert normalise_doi("  10.1234/ABC  ") == "10.1234/abc"


def test_doi_filename_slug_is_safe():
    from phase2_retrieve import doi_to_filename_slug

    assert doi_to_filename_slug("10.1234/foo.bar") == "10-1234-foo-bar"
    assert doi_to_filename_slug("10.48550/arxiv.2024.12345") == "10-48550-arxiv-2024-12345"


# ── content sniffing ───────────────────────────────────────────────────


def test_pdf_sniff_matches_pdf_magic_bytes():
    from phase2_retrieve import is_pdf_bytes

    assert is_pdf_bytes(b"%PDF-1.4\n...")
    assert not is_pdf_bytes(b"<html>...")
    assert not is_pdf_bytes(b"")


def test_html_sniff_matches_content_type_or_doctype():
    from phase2_retrieve import is_html_bytes

    assert is_html_bytes(b"", "text/html; charset=utf-8")
    assert is_html_bytes(b"<!DOCTYPE html><html>", "")
    assert is_html_bytes(b"<html><body>", "application/octet-stream")
    assert not is_html_bytes(b"%PDF-", "")


# ── Unpaywall resolver ─────────────────────────────────────────────────


_UNPAYWALL_HIT = json.dumps(
    {
        "doi": "10.1234/abc",
        "best_oa_location": {
            "url_for_pdf": "https://example.org/free.pdf",
            "license": "cc-by",
            "host_type": "repository",
        },
    }
).encode("utf-8")


_UNPAYWALL_NO_OA = json.dumps(
    {"doi": "10.1234/paywalled", "best_oa_location": None}
).encode("utf-8")


def test_unpaywall_returns_pdf_url_on_hit():
    from phase2_retrieve import lookup_unpaywall

    http = make_stub_http({"https://api.unpaywall.org/v2/": (200, _UNPAYWALL_HIT, "application/json")})
    resolved, attempt = lookup_unpaywall("10.1234/abc", contact_email="x@y.org", http=http)
    assert resolved is not None
    assert resolved.url == "https://example.org/free.pdf"
    assert resolved.license == "cc-by"
    assert attempt.success is True


def test_unpaywall_returns_none_when_no_oa():
    from phase2_retrieve import lookup_unpaywall

    http = make_stub_http({"https://api.unpaywall.org/v2/": (200, _UNPAYWALL_NO_OA, "application/json")})
    resolved, attempt = lookup_unpaywall("10.1234/paywalled", contact_email="x@y.org", http=http)
    assert resolved is None
    assert attempt.success is False
    assert "no oa" in attempt.error.lower()


def test_unpaywall_handles_404():
    from phase2_retrieve import lookup_unpaywall

    http = make_stub_http({"https://api.unpaywall.org/v2/": (404, b"", "")})
    resolved, attempt = lookup_unpaywall("10.1234/notexist", contact_email="x@y.org", http=http)
    assert resolved is None
    assert attempt.success is False
    assert "404" in attempt.error


def test_unpaywall_encodes_contact_email_into_query():
    from phase2_retrieve import lookup_unpaywall

    captured = {}

    def http(url, headers):
        from phase2_retrieve import HttpResponse
        captured["url"] = url
        captured["headers"] = headers
        return HttpResponse(200, _UNPAYWALL_HIT, "application/json", url)

    lookup_unpaywall("10.1234/abc", contact_email="me@there.edu", http=http)
    assert "email=me%40there.edu" in captured["url"]
    assert "me@there.edu" in captured["headers"]["User-Agent"]


# ── OA Button resolver ─────────────────────────────────────────────────


_OAB_HIT = json.dumps({"url": "https://example.org/oab.pdf"}).encode("utf-8")
_OAB_HIT_NESTED = json.dumps({"data": {"url": "https://example.org/oab2.pdf"}}).encode("utf-8")
_OAB_NO_URL = json.dumps({"status": "no copy"}).encode("utf-8")


def test_oa_button_extracts_flat_url():
    from phase2_retrieve import lookup_oa_button

    http = make_stub_http({"https://api.openaccessbutton.org/": (200, _OAB_HIT, "application/json")})
    resolved, attempt = lookup_oa_button("10.1234/abc", contact_email="x@y.org", http=http)
    assert resolved is not None
    assert resolved.url == "https://example.org/oab.pdf"
    assert attempt.success is True


def test_oa_button_extracts_nested_url():
    from phase2_retrieve import lookup_oa_button

    http = make_stub_http({"https://api.openaccessbutton.org/": (200, _OAB_HIT_NESTED, "application/json")})
    resolved, attempt = lookup_oa_button("10.1234/abc", contact_email="x@y.org", http=http)
    assert resolved is not None
    assert resolved.url == "https://example.org/oab2.pdf"


def test_oa_button_returns_none_when_no_url():
    from phase2_retrieve import lookup_oa_button

    http = make_stub_http({"https://api.openaccessbutton.org/": (200, _OAB_NO_URL, "application/json")})
    resolved, _ = lookup_oa_button("10.1234/abc", contact_email="x@y.org", http=http)
    assert resolved is None


# ── arXiv direct resolver ──────────────────────────────────────────────


def test_arxiv_resolver_handles_arxiv_doi():
    from phase2_retrieve import lookup_arxiv

    http = make_stub_http({})  # not called
    resolved, attempt = lookup_arxiv(
        "10.48550/arxiv.2403.12345", contact_email="x@y.org", http=http,
    )
    assert resolved is not None
    assert resolved.url == "https://arxiv.org/pdf/2403.12345.pdf"
    assert attempt.success is True


def test_arxiv_resolver_returns_none_for_non_arxiv():
    from phase2_retrieve import lookup_arxiv

    http = make_stub_http({})
    resolved, attempt = lookup_arxiv(
        "10.1590/abc-001", contact_email="x@y.org", http=http,
    )
    assert resolved is None
    assert "not an arXiv" in attempt.error


# ── retrieve_one cascade ───────────────────────────────────────────────


_FAKE_PDF = b"%PDF-1.4\nfake content\n%%EOF"


def test_retrieve_one_downloads_pdf_via_unpaywall(tmp_path):
    from phase2_retrieve import retrieve_one

    http = make_stub_http({
        "https://api.unpaywall.org/v2/": (200, _UNPAYWALL_HIT, "application/json"),
        "https://example.org/free.pdf": (200, _FAKE_PDF, "application/pdf"),
    })
    result = retrieve_one(
        "10.1234/abc",
        dest_dir=tmp_path,
        contact_email="x@y.org",
        http=http,
    )
    assert result.status == "downloaded"
    assert result.file_kind == "pdf"
    assert result.file_path.exists()
    assert result.file_path.read_bytes() == _FAKE_PDF


def test_retrieve_one_returns_gap_when_no_resolver_succeeds(tmp_path):
    from phase2_retrieve import retrieve_one

    http = make_stub_http({
        "https://api.unpaywall.org/v2/": (200, _UNPAYWALL_NO_OA, "application/json"),
        "https://api.openaccessbutton.org/": (200, _OAB_NO_URL, "application/json"),
    })
    result = retrieve_one(
        "10.1234/paywalled",
        dest_dir=tmp_path,
        contact_email="x@y.org",
        http=http,
    )
    assert result.status == "gap"
    assert result.file_path is None
    # Both resolvers tried; arXiv shortcut also tried (and failed)
    resolvers_tried = {a.resolver for a in result.attempts}
    assert "unpaywall" in resolvers_tried
    assert "oa_button" in resolvers_tried


def test_retrieve_one_short_circuits_on_first_success(tmp_path):
    """If arXiv resolver fires first (because DOI is an arXiv DOI), the
    cascade must not fall through to Unpaywall."""
    from phase2_retrieve import retrieve_one

    http = make_stub_http({
        "https://arxiv.org/pdf/": (200, _FAKE_PDF, "application/pdf"),
        # Unpaywall would error if called — but it shouldn't be
        "https://api.unpaywall.org/v2/": (500, b"", ""),
    })
    result = retrieve_one(
        "10.48550/arxiv.2403.12345",
        dest_dir=tmp_path,
        contact_email="x@y.org",
        http=http,
    )
    assert result.status == "downloaded"
    # The cascade stopped after arXiv
    assert result.attempts[0].resolver == "arxiv"


def test_retrieve_one_writes_html_when_response_is_html(tmp_path):
    from phase2_retrieve import retrieve_one

    html_body = b"<!DOCTYPE html><html><body>Article content</body></html>"
    http = make_stub_http({
        "https://api.unpaywall.org/v2/": (200, _UNPAYWALL_HIT, "application/json"),
        "https://example.org/free.pdf": (200, html_body, "text/html"),
    })
    result = retrieve_one(
        "10.1234/abc",
        dest_dir=tmp_path,
        contact_email="x@y.org",
        http=http,
    )
    assert result.status == "downloaded"
    assert result.file_kind == "html"
    assert result.file_path.suffix == ".html"


def test_retrieve_one_continues_when_download_404(tmp_path):
    """If Unpaywall gives a URL but the download fails 404, cascade
    falls through to the next resolver."""
    from phase2_retrieve import retrieve_one

    http = make_stub_http({
        "https://api.unpaywall.org/v2/": (200, _UNPAYWALL_HIT, "application/json"),
        "https://example.org/free.pdf": (404, b"", ""),
        "https://api.openaccessbutton.org/": (200, _OAB_HIT, "application/json"),
        "https://example.org/oab.pdf": (200, _FAKE_PDF, "application/pdf"),
    })
    result = retrieve_one(
        "10.1234/abc",
        dest_dir=tmp_path,
        contact_email="x@y.org",
        http=http,
    )
    assert result.status == "downloaded"
    assert result.resolved_url == "https://example.org/oab.pdf"


# ── retrieve_all + gap report ──────────────────────────────────────────


def _build_run_dir(tmp_path: Path) -> Path:
    """Mimic phase2_init's output minimally."""
    run = tmp_path / "run"
    (run / "sources").mkdir(parents=True)
    (run / "logs").mkdir(parents=True)
    handoff = {
        "phase": 1,
        "schema_version": "1.0",
        "handoff_hash": "x" * 64,
        "included_for_fulltext": [
            {
                "doi": "10.1234/found",
                "title": "Found paper",
                "year": 2024,
                "expected_access_tier": "open_access",
            },
            {
                "doi": "10.1234/lost",
                "title": "Lost paper",
                "year": 2024,
                "expected_access_tier": "paywall_no_credential",
            },
        ],
    }
    (run / "handoff.json").write_text(json.dumps(handoff), encoding="utf-8")
    return run


def test_retrieve_all_writes_pdfs_for_found_and_gap_report_for_lost(tmp_path):
    from phase2_retrieve import retrieve_all

    def stub_for_doi(doi: str):
        if "found" in doi:
            return _UNPAYWALL_HIT
        return _UNPAYWALL_NO_OA

    def http(url, headers):
        from phase2_retrieve import HttpResponse
        if "api.unpaywall.org" in url:
            doi = url.split("/v2/", 1)[1].split("?")[0]
            return HttpResponse(200, stub_for_doi(doi), "application/json", url)
        if "api.openaccessbutton.org" in url:
            return HttpResponse(200, _OAB_NO_URL, "application/json", url)
        if "example.org/free.pdf" in url:
            return HttpResponse(200, _FAKE_PDF, "application/pdf", url)
        raise urllib.error.URLError(f"no stub for {url}")

    run = _build_run_dir(tmp_path)
    summary = retrieve_all(run, contact_email="x@y.org", http=http, sleep_between_s=0)
    assert summary["total_included"] == 2
    assert summary["downloaded"] == 1
    assert summary["gap"] == 1

    # Found paper landed in sources/
    pdfs = list((run / "sources").glob("*.pdf"))
    assert len(pdfs) == 1
    # Lost paper in gap_report.md
    gap = (run / "gap_report.md").read_text(encoding="utf-8")
    assert "10.1234/lost" in gap
    assert "Lost paper" in gap
    assert "paywall_no_credential" in gap


def test_retrieve_all_writes_jsonl_log_per_doi(tmp_path):
    from phase2_retrieve import retrieve_all

    http = make_stub_http({
        "https://api.unpaywall.org/v2/": (200, _UNPAYWALL_NO_OA, "application/json"),
        "https://api.openaccessbutton.org/": (200, _OAB_NO_URL, "application/json"),
    })
    run = _build_run_dir(tmp_path)
    retrieve_all(run, contact_email="x@y.org", http=http, sleep_between_s=0)

    log = (run / "logs" / "retrieval.log").read_text(encoding="utf-8")
    lines = [json.loads(line) for line in log.splitlines() if line.strip()]
    assert len(lines) == 2
    # Each record has expected schema
    for rec in lines:
        assert "doi" in rec
        assert "timestamp" in rec
        assert "status" in rec
        assert "attempts" in rec
        assert isinstance(rec["attempts"], list)


# ── CLI smoke ──────────────────────────────────────────────────────────


def test_cli_help_runs():
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "phase2_retrieve.py"), "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "retrieval" in result.stdout.lower()


def test_cli_missing_run_dir_exits_1(tmp_path):
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "phase2_retrieve.py"),
         str(tmp_path / "nope"), "--contact-email", "x@y.org"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert "not found" in result.stderr


def test_cli_missing_contact_email_exits_1(tmp_path):
    import subprocess
    run = _build_run_dir(tmp_path)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "phase2_retrieve.py"),
         str(run)],
        capture_output=True, text=True, check=False,
        env={"PATH": "/usr/bin:/bin"},  # blank env so IGNORANTIA_CONTACT_EMAIL unset
    )
    assert result.returncode == 1
    assert "contact-email" in result.stderr.lower() or "polite" in result.stderr.lower()
