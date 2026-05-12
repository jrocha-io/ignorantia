"""Fix 22 / Phase A — phase1_emit_zip: deposit ZIP with download lists.

phase1_emit_zip is invoked at the end of the chat session. It reads
the schema-validated handoff, resolves OA URLs for each included DOI
via the Unpaywall/arXiv/OAB cascade (lookup only — no PDF download),
and writes a deposit ZIP with three download-list formats plus a
README so the operator can fetch papers externally and dump them into
the Phase 2 run dir.

Tests use an in-memory HttpFetcher stub so the resolver cascade runs
deterministically without network.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.error
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "phase1_emit_zip.py"
sys.path.insert(0, str(ROOT / "scripts"))


# ── fixtures ───────────────────────────────────────────────────────────


_UNPAYWALL_HIT = json.dumps(
    {
        "doi": "10.1234/foo",
        "best_oa_location": {
            "url_for_pdf": "https://example.org/foo.pdf",
            "license": "cc-by",
            "host_type": "repository",
        },
    }
).encode("utf-8")

_UNPAYWALL_NO_OA = json.dumps(
    {"doi": "10.1234/paywalled", "best_oa_location": None}
).encode("utf-8")

_OAB_NO_URL = json.dumps({"status": "no copy"}).encode("utf-8")


def make_stub_http(per_doi: dict[str, bytes]):
    """Build an HttpFetcher whose Unpaywall response depends on the DOI
    in the URL. OAB always returns "no copy" for simplicity."""
    from phase2_retrieve import HttpResponse

    def fetch(url: str, headers: dict[str, str]):
        if "api.unpaywall.org" in url:
            doi = url.split("/v2/", 1)[1].split("?")[0]
            payload = per_doi.get(doi, _UNPAYWALL_NO_OA)
            return HttpResponse(200, payload, "application/json", url)
        if "api.openaccessbutton.org" in url:
            return HttpResponse(200, _OAB_NO_URL, "application/json", url)
        raise urllib.error.URLError(f"unmocked: {url}")

    return fetch


def _canonical_hash(handoff: dict) -> str:
    copy = {k: v for k, v in handoff.items() if k != "handoff_hash"}
    raw = json.dumps(copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _make_handoff(tmp_path: Path, *, included: list[dict]) -> Path:
    body = {
        "phase": 1,
        "schema_version": "1.0",
        "created_at": "2026-05-12T12:00:00Z",
        "protocol": {
            "title": "Validade de revisões assistidas por IA",
            "authors": [{"name": "Test Author", "orcid": "0009-0000-0000-0001"}],
            "review_type": "scoping_review",
            "review_purpose": "design_foundational",
            "language": "pt-BR",
            "citation_style": "abnt",
            "temporal_window": {"start_date": "2018-01-01", "end_date": "2026-05-12"},
            "pcc": {"population": "x" * 20, "concept": "y" * 20, "context": "z" * 20},
            "sub_questions": [{"id": "RQ1.1", "text": "test question here"}],
            "inclusion_criteria": [{"id": "IC1", "text": "peer-reviewed"}],
            "exclusion_criteria": [{"id": "EC1", "text": "pre-2018"}],
            "bases": [
                {"id": "arxiv", "name": "arXiv",
                 "access_tier": "open_access", "execution_mode": "direct_api"},
                {"id": "openalex", "name": "OpenAlex",
                 "access_tier": "open_access", "execution_mode": "direct_api"},
                {"id": "crossref", "name": "Crossref",
                 "access_tier": "open_access", "execution_mode": "direct_api"},
            ],
            "search_strings": {
                "arxiv": "test query string with terms",
                "openalex": "test query string with terms",
                "crossref": "test query string with terms",
            },
            "ai_disclosure": {
                "template": "industrial_secret_cnpq_pt",
                "stages_used": ["screening_title_abstract"],
            },
        },
        "searches": [
            {"base_id": b, "query": "x", "executed_at": "2026-05-12T03:00:00Z",
             "n_hits_raw": 100, "status": "success"}
            for b in ("arxiv", "openalex", "crossref")
        ],
        "dedup": {"n_in": 300, "n_out": 280,
                  "hierarchy": ["doi", "arxiv_id", "title_author_year_normalized"]},
        "screening": {
            "passes": [{"name": "p1", "n_in": 280, "n_out": len(included),
                        "criteria": "scope match"}],
            "trace_per_doi": {
                item["doi"]: [{"pass_name": "p1", "decision": "include",
                               "reason": "match"}]
                for item in included
            },
        },
        "included_for_fulltext": included,
        "metadata": {
            "skill_version": "3.0.0",
            "model": "anthropic/claude-opus-4-7",
            "phase1_session_id": "phase1-test-001",
        },
    }
    body["handoff_hash"] = _canonical_hash(body)
    handoff_path = tmp_path / "handoff-v1.0.0.json"
    handoff_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return handoff_path


# ── URL resolution ─────────────────────────────────────────────────────


def test_resolve_returns_url_when_unpaywall_hits(tmp_path):
    from phase1_emit_zip import resolve_download_list

    http = make_stub_http({"10.1234/foo": _UNPAYWALL_HIT})
    items = [{"doi": "10.1234/foo", "title": "Foo Paper", "year": 2024,
              "expected_access_tier": "open_access"}]
    resolved = resolve_download_list(
        items, contact_email="x@y.org", http_fetch=http, sleep_between_s=0,
    )
    assert len(resolved) == 1
    assert resolved[0].resolved_url == "https://example.org/foo.pdf"
    assert resolved[0].resolver == "unpaywall"
    assert resolved[0].license == "cc-by"
    assert resolved[0].error == ""


def test_resolve_records_error_when_all_resolvers_miss(tmp_path):
    from phase1_emit_zip import resolve_download_list

    http = make_stub_http({"10.1234/paywalled": _UNPAYWALL_NO_OA})
    items = [{"doi": "10.1234/paywalled", "title": "Paywalled", "year": 2024,
              "expected_access_tier": "paywall_no_credential"}]
    resolved = resolve_download_list(
        items, contact_email="x@y.org", http_fetch=http, sleep_between_s=0,
    )
    assert len(resolved) == 1
    assert resolved[0].resolved_url == ""
    assert "paywall" in resolved[0].error.lower() or "manual" in resolved[0].error.lower()


def test_resolve_uses_arxiv_direct_when_arxiv_doi(tmp_path):
    from phase1_emit_zip import resolve_download_list

    # arXiv resolver doesn't call HTTP — it derives the URL from DOI prefix
    http = make_stub_http({})
    items = [{"doi": "10.48550/arxiv.2403.12345", "title": "arXiv paper",
              "year": 2024, "expected_access_tier": "open_access"}]
    resolved = resolve_download_list(
        items, contact_email="x@y.org", http_fetch=http, sleep_between_s=0,
    )
    assert resolved[0].resolver == "arxiv"
    assert "arxiv.org/pdf" in resolved[0].resolved_url


# ── artifact builders ──────────────────────────────────────────────────


def _sample_resolved():
    from phase1_emit_zip import ResolvedDownload

    return [
        ResolvedDownload(
            doi="10.1234/foo", title="Foo Paper", year=2024,
            expected_tier="open_access", resolved_url="https://example.org/foo.pdf",
            resolver="unpaywall", license="cc-by",
        ),
        ResolvedDownload(
            doi="10.1234/bar", title="Bar Paper", year=2023,
            expected_tier="paywall_no_credential",
            error="paywalled — needs manual lookup",
        ),
    ]


def test_build_crawljob_emits_jdownloader_compatible_json():
    from phase1_emit_zip import build_downloads_crawljob

    raw = build_downloads_crawljob(_sample_resolved())
    parsed = json.loads(raw)
    assert isinstance(parsed, list)
    # Only items with resolved URLs make it into the crawljob
    assert len(parsed) == 1
    entry = parsed[0]
    assert entry["text"] == "https://example.org/foo.pdf"
    assert "10.1234/foo" in entry["comment"]
    assert entry["filename"] == "10-1234-foo.pdf"
    assert entry["packageName"] == "ignorantia-phase1-downloads"


def test_build_txt_one_url_per_line_with_doi_comment():
    from phase1_emit_zip import build_downloads_txt

    txt = build_downloads_txt(_sample_resolved())
    lines = [line for line in txt.splitlines() if line.strip()]
    # Pairs of (comment, URL) — comment starts with #
    assert lines[0].startswith("#")
    assert "10.1234/foo" in lines[0]
    assert lines[1] == "https://example.org/foo.pdf"
    # Paywalled item not in list
    assert "bar" not in txt


def test_build_index_md_has_table_with_all_items():
    from phase1_emit_zip import build_downloads_index

    md = build_downloads_index(_sample_resolved())
    assert "| # | DOI |" in md  # table header
    assert "10.1234/foo" in md
    assert "10.1234/bar" in md  # paywalled items still listed
    assert "unpaywall" in md
    assert "manual" in md.lower()
    # Stats footer
    assert "Resolved" in md and "1 of 2" in md


def test_build_readme_documents_phase2_invocation():
    from phase1_emit_zip import build_readme

    readme = build_readme(_sample_resolved(), handoff_filename="handoff-v1.0.0.json")
    assert "JDownloader" in readme or "downloads.crawljob" in readme
    assert "downloads.txt" in readme
    assert "phase2_orchestrator.py" in readme
    assert "sources/" in readme
    assert "handoff-v1.0.0.json" in readme


# ── ZIP assembly ───────────────────────────────────────────────────────


def test_emit_zip_writes_brand_free_filename(tmp_path):
    from phase1_emit_zip import emit_zip

    items = [{"doi": "10.1234/foo", "title": "Foo", "year": 2024,
              "expected_access_tier": "open_access"}]
    handoff_path = _make_handoff(tmp_path, included=items)
    http = make_stub_http({"10.1234/foo": _UNPAYWALL_HIT})
    zip_path, resolved = emit_zip(
        handoff_path, output_dir=tmp_path / "out",
        contact_email="x@y.org", http_fetch=http, sleep_between_s=0,
    )
    assert zip_path.exists()
    assert "ignorantia" not in zip_path.name  # brand-free filename
    assert zip_path.name.endswith("-phase1.zip")
    assert len(resolved) == 1


def test_emit_zip_contains_all_five_artifacts(tmp_path):
    from phase1_emit_zip import emit_zip

    items = [{"doi": "10.1234/foo", "title": "Foo Paper", "year": 2024,
              "expected_access_tier": "open_access"}]
    handoff_path = _make_handoff(tmp_path, included=items)
    http = make_stub_http({"10.1234/foo": _UNPAYWALL_HIT})
    zip_path, _ = emit_zip(
        handoff_path, output_dir=tmp_path / "out",
        contact_email="x@y.org", http_fetch=http, sleep_between_s=0,
    )
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    assert "handoff-v1.0.0.json" in names
    assert "downloads.crawljob" in names
    assert "downloads.txt" in names
    assert "downloads-index.md" in names
    assert "README.md" in names


def test_emit_zip_handoff_inside_is_byte_identical(tmp_path):
    """The handoff inside the ZIP must match the source byte-for-byte
    (so Phase 2's hash check passes)."""
    from phase1_emit_zip import emit_zip

    items = [{"doi": "10.1234/foo", "title": "Foo", "year": 2024,
              "expected_access_tier": "open_access"}]
    handoff_path = _make_handoff(tmp_path, included=items)
    original = handoff_path.read_bytes()
    http = make_stub_http({"10.1234/foo": _UNPAYWALL_HIT})
    zip_path, _ = emit_zip(
        handoff_path, output_dir=tmp_path / "out",
        contact_email="x@y.org", http_fetch=http, sleep_between_s=0,
    )
    with zipfile.ZipFile(zip_path) as zf:
        inside = zf.read(handoff_path.name)
    assert inside == original


def test_suggested_filename_matches_phase2_doi_slug():
    """The filename the operator should save under must match the slug
    phase2_retrieve.doi_to_filename_slug produces — otherwise Phase 2
    won't auto-match dumped PDFs to their DOIs in F22-B."""
    from phase1_emit_zip import _suggest_filename, ResolvedDownload
    from phase2_retrieve import doi_to_filename_slug

    r = ResolvedDownload(
        doi="10.1234/foo.bar", title="x", year=2024,
        expected_tier="open_access", resolved_url="https://x/y.pdf",
    )
    suggested = _suggest_filename(r)
    expected_slug = doi_to_filename_slug("10.1234/foo.bar")
    assert suggested == f"{expected_slug}.pdf"


# ── CLI ────────────────────────────────────────────────────────────────


def test_cli_help_runs():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "Phase 1" in result.stdout
    assert "ZIP" in result.stdout or "zip" in result.stdout


def test_cli_missing_handoff_exits_1(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "nope.json"),
         "--contact-email", "x@y.org"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1


def test_cli_missing_contact_email_exits_1(tmp_path):
    items = [{"doi": "10.1234/foo", "title": "Foo", "year": 2024,
              "expected_access_tier": "open_access"}]
    handoff_path = _make_handoff(tmp_path, included=items)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(handoff_path),
         "--output-dir", str(tmp_path / "out")],
        capture_output=True, text=True, check=False,
        env={"PATH": "/usr/bin:/bin"},  # blank env so IGNORANTIA_CONTACT_EMAIL unset
    )
    assert result.returncode == 1
