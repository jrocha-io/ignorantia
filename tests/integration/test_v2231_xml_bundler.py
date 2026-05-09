"""Fix 18 / Phase 6 — XML bundler (RS-42 dogfood remediation).

After F1-F5, the repo holds 71 individual ``<doc>`` XML envelopes. The
bundler consolidates same-stage envelopes into one ``<doc_bundle>``
artifact each, cutting the production-package file count without
losing information. These tests pin the bundler contract:

  - Each bundle is well-formed XML with a ``<doc_bundle stage=... count=...>``
    root and every source ``<doc>`` embedded verbatim.
  - The CDATA payloads survive the round-trip (Markdown bodies remain
    intact — bundling must be lossless).
  - ``--all`` walks the default mapping and emits one bundle per stage.
  - Pre-existing bundles are skipped on re-bundle (idempotency).
  - CLI error paths are explicit.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))


# ── helpers ─────────────────────────────────────────────────────────────


def _make_doc(tmp: Path, *, doc_id: str, body: str) -> Path:
    src = tmp / f"{doc_id}.xml"
    src.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<doc id="{doc_id}" path="{tmp.name}/{doc_id}.xml" '
        f'type="test" lang="pt-BR">\n'
        f"  <title>Doc {doc_id}</title>\n"
        "  <markdown><![CDATA[\n"
        f"{body}\n"
        "  ]]></markdown>\n"
        "</doc>\n",
        encoding="utf-8",
    )
    return src


# ── core contract ──────────────────────────────────────────────────────


def test_bundle_directory_emits_well_formed_xml(tmp_path):
    from bundle_xml import bundle_directory
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    _make_doc(src_dir, doc_id="abnt", body="# ABNT\nBody A.")
    _make_doc(src_dir, doc_id="apa", body="# APA\nBody B.")

    bundle = bundle_directory(src_dir, "citation-styles")
    root = ET.fromstring(bundle)
    assert root.tag == "doc_bundle"
    assert root.attrib["stage"] == "citation-styles"
    assert root.attrib["count"] == "2"
    docs = root.findall("doc")
    assert len(docs) == 2
    assert {d.attrib["id"] for d in docs} == {"abnt", "apa"}


def test_bundle_preserves_cdata_bodies_verbatim(tmp_path):
    """Bundled <doc> elements must retain the literal CDATA payload — the
    Markdown body cannot be re-escaped or re-emitted as plain text."""
    from bundle_xml import bundle_directory
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    body = "# Title\n\nLine with <angle> and & ampersand."
    _make_doc(src_dir, doc_id="x", body=body)
    bundle = bundle_directory(src_dir, "test")
    # The literal angle bracket and ampersand must survive (they would be
    # escaped to &lt;/&amp; if the body were re-emitted as plain text).
    assert "<angle>" in bundle
    assert "& ampersand" in bundle


def test_bundle_orders_docs_alphabetically_by_filename(tmp_path):
    """Stable ordering matters — the bundle is checked into source
    control and reviewers should see deterministic diffs."""
    from bundle_xml import bundle_directory
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    for name in ["zebra", "apple", "mango"]:
        _make_doc(src_dir, doc_id=name, body="# " + name)
    bundle = bundle_directory(src_dir, "fruits")
    root = ET.fromstring(bundle)
    ids = [d.attrib["id"] for d in root.findall("doc")]
    assert ids == ["apple", "mango", "zebra"]


def test_bundle_skips_existing_bundles_for_idempotency(tmp_path):
    """Re-bundling the same directory should not re-include a prior bundle
    artifact stored alongside the source docs."""
    from bundle_xml import bundle_directory
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    _make_doc(src_dir, doc_id="real", body="# Real")
    # A previous bundle artifact left in the directory.
    (src_dir / "bundle-prev.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<doc_bundle stage="prev" count="0"></doc_bundle>\n',
        encoding="utf-8",
    )
    bundle = bundle_directory(src_dir, "real")
    root = ET.fromstring(bundle)
    docs = root.findall("doc")
    assert len(docs) == 1
    assert docs[0].attrib["id"] == "real"


def test_bundle_directory_raises_when_no_docs_found(tmp_path):
    from bundle_xml import bundle_directory
    src_dir = tmp_path / "empty"
    src_dir.mkdir()
    with pytest.raises(ValueError):
        bundle_directory(src_dir, "empty")


# ── write_bundle ─────────────────────────────────────────────────────────


def test_write_bundle_writes_file_unless_dry_run(tmp_path):
    from bundle_xml import write_bundle
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    _make_doc(src_dir, doc_id="x", body="# X")
    out = tmp_path / "out" / "bundle-test.xml"
    write_bundle(src_dir, "test", out)
    assert out.exists()
    # Round-trip parses well-formed.
    ET.parse(out)


def test_write_bundle_dry_run_skips_disk(tmp_path, capsys):
    from bundle_xml import write_bundle
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    _make_doc(src_dir, doc_id="x", body="# X")
    out = tmp_path / "out" / "bundle-test.xml"
    write_bundle(src_dir, "test", out, dry_run=True)
    assert not out.exists()
    captured = capsys.readouterr()
    assert "dry-run" in captured.out


# ── --all default mapping ────────────────────────────────────────────────


def test_bundle_all_defaults_writes_one_per_existing_dir(tmp_path):
    """Build a fake repo with two of the default-mapping directories and
    verify only those produce bundles."""
    from bundle_xml import bundle_all_defaults
    fake_repo = tmp_path / "repo"
    cs = fake_repo / "references" / "citation-styles"
    cs.mkdir(parents=True)
    _make_doc(cs, doc_id="abnt", body="# ABNT")
    _make_doc(cs, doc_id="apa", body="# APA")

    db = fake_repo / "references" / "databases"
    db.mkdir(parents=True)
    _make_doc(db, doc_id="intl", body="# Intl")

    out_dir = tmp_path / "bundles"
    written = bundle_all_defaults(out_dir, repo_root=fake_repo)
    names = sorted(p.name for p in written)
    assert "bundle-citation-styles.xml" in names
    assert "bundle-databases.xml" in names
    # Missing default dirs (modes/, claude-chat-tasks/, templates-modes) skip silently.
    cs_bundle = ET.parse(out_dir / "bundle-citation-styles.xml").getroot()
    assert cs_bundle.attrib["count"] == "2"


# ── CLI ──────────────────────────────────────────────────────────────────


def test_cli_single_bundle_round_trip(tmp_path):
    from bundle_xml import main
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    _make_doc(src_dir, doc_id="x", body="# X")
    out = tmp_path / "bundle-test.xml"
    rc = main([str(src_dir), "--stage", "test", "--out", str(out)])
    assert rc == 0
    assert out.exists()


def test_cli_errors_when_neither_source_nor_all(tmp_path):
    from bundle_xml import main
    rc = main([])
    assert rc == 2


def test_cli_errors_when_all_lacks_out_dir(tmp_path):
    from bundle_xml import main
    rc = main(["--all"])
    assert rc == 2


def test_cli_errors_when_source_dir_missing(tmp_path):
    from bundle_xml import main
    rc = main([str(tmp_path / "nope"), "--stage", "x", "--out", str(tmp_path / "o.xml")])
    assert rc != 0


def test_cli_errors_when_single_mode_lacks_stage_or_out(tmp_path):
    from bundle_xml import main
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    rc = main([str(src_dir)])
    assert rc == 2


# ── real-repo smoke ──────────────────────────────────────────────────────


def test_real_repo_citation_styles_bundle_smoke(tmp_path):
    """Smoke-bundle the real ``references/citation-styles/`` directory and
    verify the bundle round-trips and contains the expected docs."""
    from bundle_xml import write_bundle
    src_dir = REPO / "references" / "citation-styles"
    if not src_dir.is_dir() or not list(src_dir.glob("*.xml")):
        pytest.skip("citation-styles XMLs not yet migrated on this branch")
    out = tmp_path / "bundle-citation-styles.xml"
    write_bundle(src_dir, "citation-styles", out)
    root = ET.parse(out).getroot()
    assert root.tag == "doc_bundle"
    ids = {d.attrib["id"] for d in root.findall("doc")}
    assert {"abnt", "apa", "ieee", "vancouver"}.issubset(ids)
