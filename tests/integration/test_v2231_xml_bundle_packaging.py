"""Fix 18 / Phase 8 — XML bundle packaging (RS-42 dogfood remediation).

The Markdown-to-XML migration (F1-F5) wraps each reference doc in a
single-file XML envelope. The bundler (F6) consolidates same-stage docs
into single artifacts. This phase wires bundling into the production
packager (``scripts/build_production_package.py``):

  - Default globs in REFERENCES_ROOT_GLOB and ASSETS_GLOB now match
    *.xml (was *.md).
  - The new ``--bundle-xml`` flag generates ``bundle-<stage>.xml``
    artifacts at build time and substitutes them for the individual
    XMLs they cover. Source tree is untouched.
  - Bundle artifacts ship under ``references/bundles/`` inside the zip.

These tests pin the contract:

  - The static glob constants point at *.xml (not *.md).
  - ``BUNDLE_STAGES`` covers the 4 bundleable directories (top-level
    references/ is intentionally NOT bundled).
  - ``resolve_allowlist(bundle_xml=True)`` substitutes individual XMLs
    with the matching bundle artifact.
  - ``--bundle-xml`` reduces the total file count vs the default flow.
  - Both flows stay under the MAX_FILES ceiling.
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))


# ── static config ──────────────────────────────────────────────────────


def test_references_root_glob_uses_xml_not_md():
    from build_production_package import REFERENCES_ROOT_GLOB
    md_entries = [(d, p) for d, p in REFERENCES_ROOT_GLOB if p == "*.md"]
    assert md_entries == [], (
        f"REFERENCES_ROOT_GLOB still has *.md entries (Fix 18 should have "
        f"switched all to *.xml): {md_entries}"
    )
    # And the migrated subdirs are present with *.xml.
    expected = {
        ("references", "*.xml"),
        ("references/citation-styles", "*.xml"),
        ("references/databases", "*.xml"),
        ("references/modes", "*.xml"),
    }
    assert expected.issubset(set(REFERENCES_ROOT_GLOB))


def test_assets_glob_uses_xml_for_modes_templates():
    from build_production_package import ASSETS_GLOB
    md_entries = [(d, p) for d, p in ASSETS_GLOB if p == "*.md"]
    assert md_entries == []
    assert ("assets/templates/modes", "*.xml") in ASSETS_GLOB
    # The HTML manuscript template is still picked up.
    assert ("assets/templates", "*.html") in ASSETS_GLOB


def test_bundle_stages_covers_the_four_bundleable_dirs():
    from build_production_package import BUNDLE_STAGES
    stages = {stage for _, stage in BUNDLE_STAGES}
    # Top-level references/ is intentionally NOT in BUNDLE_STAGES.
    assert "citation-styles" in stages
    assert "databases" in stages
    assert "modes" in stages
    assert "templates-modes" in stages


# ── allowlist behaviour with bundling ──────────────────────────────────


def test_resolve_allowlist_default_includes_individual_xmls():
    from build_production_package import resolve_allowlist
    files = resolve_allowlist(REPO)
    rels = {p.relative_to(REPO).as_posix() for p in files}
    # Default mode (no bundling) should include every individual XML.
    assert "references/citation-styles/abnt.xml" in rels
    assert "references/citation-styles/apa.xml" in rels
    assert "references/modes/MODES_OVERVIEW.xml" in rels
    assert "assets/templates/modes/mode-scoping-review.xml" in rels


def test_resolve_allowlist_with_bundles_substitutes_individual_xmls(tmp_path):
    """``bundle_xml=True`` should drop the individuals from a bundleable
    stage and append the bundle artifact instead."""
    from bundle_xml import write_bundle
    from build_production_package import BUNDLE_STAGES, resolve_allowlist

    # Pre-generate bundles into a temp dir (the real build flow does this).
    for rel_dir, stage in BUNDLE_STAGES:
        source_dir = REPO / rel_dir
        if not source_dir.is_dir() or not list(source_dir.glob("*.xml")):
            pytest.skip(f"{rel_dir} not migrated yet; skipping bundle test")
        write_bundle(source_dir, stage, tmp_path / f"bundle-{stage}.xml")

    files = resolve_allowlist(REPO, bundle_xml=True, bundle_dir=tmp_path)
    rels = {p.resolve().as_posix() for p in files}

    # Individual XMLs in bundleable dirs are gone.
    cs = (REPO / "references" / "citation-styles" / "abnt.xml").resolve().as_posix()
    assert cs not in rels, "bundled stage's individual XMLs should be excluded"
    # Bundle artifacts are present (resolved-temp paths).
    bundle = (tmp_path / "bundle-citation-styles.xml").resolve().as_posix()
    assert bundle in rels, "bundle artifact must be in the allowlist"


def test_bundle_xml_reduces_total_file_count(tmp_path):
    """The packager flow with bundles must yield fewer files than without."""
    from bundle_xml import write_bundle
    from build_production_package import BUNDLE_STAGES, resolve_allowlist

    for rel_dir, stage in BUNDLE_STAGES:
        source_dir = REPO / rel_dir
        if not source_dir.is_dir() or not list(source_dir.glob("*.xml")):
            pytest.skip(f"{rel_dir} not migrated yet; skipping count test")
        write_bundle(source_dir, stage, tmp_path / f"bundle-{stage}.xml")

    default_count = len(resolve_allowlist(REPO))
    bundled_count = len(resolve_allowlist(REPO, bundle_xml=True, bundle_dir=tmp_path))
    assert bundled_count < default_count
    # Individual count: 4 + 3 + 11 + 10 = 28 individuals replaced by 4 bundles
    # → net savings = 28 - 4 = 24 files.
    assert default_count - bundled_count == 24


# ── ceiling sanity ──────────────────────────────────────────────────────


def test_default_flow_stays_under_max_files():
    from build_production_package import MAX_FILES, resolve_allowlist
    count = len(resolve_allowlist(REPO))
    assert count <= MAX_FILES, (
        f"default packaging flow ({count} files) exceeds MAX_FILES ({MAX_FILES})"
    )


def test_bundled_flow_stays_under_max_files(tmp_path):
    from bundle_xml import write_bundle
    from build_production_package import (
        BUNDLE_STAGES, MAX_FILES, resolve_allowlist,
    )
    for rel_dir, stage in BUNDLE_STAGES:
        source_dir = REPO / rel_dir
        if not source_dir.is_dir() or not list(source_dir.glob("*.xml")):
            pytest.skip(f"{rel_dir} not migrated yet")
        write_bundle(source_dir, stage, tmp_path / f"bundle-{stage}.xml")
    count = len(resolve_allowlist(REPO, bundle_xml=True, bundle_dir=tmp_path))
    assert count <= MAX_FILES


# ── archive name mapping for bundle artifacts ──────────────────────────


def test_archive_name_routes_bundle_to_references_bundles_dir(tmp_path):
    """Bundle artifacts live in a temp dir; in-zip they go under
    ``references/bundles/`` so the zip layout is predictable."""
    from build_production_package import _archive_name
    bundle_file = tmp_path / "bundle-citation-styles.xml"
    bundle_file.write_text("<doc_bundle/>", encoding="utf-8")
    arc = _archive_name(bundle_file, REPO, tmp_path)
    assert arc == "references/bundles/bundle-citation-styles.xml"


def test_archive_name_keeps_repo_relative_for_normal_files():
    from build_production_package import _archive_name
    # Any in-repo file uses its repo-relative path.
    src = REPO / "SKILL.md"
    arc = _archive_name(src, REPO, None)
    assert arc == "SKILL.md"


# ── end-to-end build + zip layout ──────────────────────────────────────


def test_build_with_bundle_xml_writes_zip_with_bundles(tmp_path):
    """End-to-end: invoke ``build(bundle_xml=True)`` and inspect the zip."""
    from build_production_package import build
    out_dir = tmp_path / "dist"
    zip_path = build(
        root=REPO, name="ignorantia-test", version="0.0.0-test",
        output_dir=out_dir, dry_run=False, bundle_xml=True,
    )
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    # Bundle artifacts present.
    assert "references/bundles/bundle-citation-styles.xml" in names
    assert "references/bundles/bundle-databases.xml" in names
    assert "references/bundles/bundle-modes.xml" in names
    assert "references/bundles/bundle-templates-modes.xml" in names
    # Bundleable individuals absent.
    assert "references/citation-styles/abnt.xml" not in names
    assert "references/modes/MODES_OVERVIEW.xml" not in names
    # Non-bundled top-level XML is still there.
    assert "references/quality-rubric.xml" in names


def test_build_default_flow_writes_zip_without_bundles(tmp_path):
    from build_production_package import build
    out_dir = tmp_path / "dist"
    zip_path = build(
        root=REPO, name="ignorantia-test", version="0.0.0-test",
        output_dir=out_dir, dry_run=False, bundle_xml=False,
    )
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    # No bundles when --bundle-xml is off.
    assert not any(n.startswith("references/bundles/") for n in names)
    # Individuals are present.
    assert "references/citation-styles/abnt.xml" in names
