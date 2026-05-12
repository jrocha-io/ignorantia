#!/usr/bin/env python3
"""Production-package generator for the ignorantia skill.

Produces a zip archive ``<name>-<version>.zip`` (e.g.
``ignorantia-2.23.0.zip``) containing only the files needed at
runtime by the skill — everything else (tests, CI config, IDE
metadata, build caches, v3 alpha source, build-only docs) is
excluded by an explicit allowlist.

The zip is capped at **MAX_FILES** (currently 220) by hard
assertion. If the allowlist resolves to more than that, the script
aborts and prints the offenders so the operator can trim. The cap
is a self-imposed ceiling; see the comment near ``MAX_FILES`` for
the current rationale.

**Usage**::

    python3 scripts/build_production_package.py

By default the archive name is read from ``pyproject.toml``
(``project.name`` + ``project.version``). Override either with the
matching CLI flag.

**Why an allowlist (not a denylist)?** Repository contents grow over
time. A denylist silently lets new files in; an allowlist forces a
review when a new path needs to ship. The 200-file cap is the
upstream constraint we are deliberately enforcing.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bundle_xml import write_bundle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# ----------------------------------------------------------------------
# Allowlist
# ----------------------------------------------------------------------
#
# Each entry is either:
#   * a plain filename relative to ROOT, e.g. "SKILL.md"
#   * a directory + glob pattern, e.g. ("scripts/searches", "*.py")
#
# The expansion is shallow per directory — globs do not recurse unless
# explicitly written with "**". This forces every directory inclusion
# to be a deliberate decision.

# --- Top-level skill manifest + project metadata -----------------------
# CHANGELOG.md is intentionally NOT shipped: it carries fix-history
# breadcrumbs (`Fix N`, `RS-42 dogfood`, version-trajectory annotations)
# that are developer-facing. The operator (Claude reading the skill in
# chat) must never reproduce those tokens in deposited artifacts. The
# full changelog stays at the repo root for developers.
ROOT_FILES: tuple[str, ...] = (
    "SKILL.md",            # entry point Claude Desktop reads (Phase 1, chat)
    "SKILL-PHASE-2.md",    # entry point Anthropic Cowork reads (Phase 2)
    "LICENSE",
    "pyproject.toml",      # package metadata; consumed by build_production_package
    # README.md is intentionally NOT shipped: it is the developer-facing
    # repo landing on GitHub (installation instructions, architecture
    # overview, Sprint Badge calibration corpus references). The operator
    # entry point is SKILL.md; the operator never needs the GitHub README.
    # CHANGELOG.md is intentionally NOT shipped: developer fix-history.
)

# --- v3.0.0 biphasic artifacts ----------------------------------------
# Phase 2 (Cowork) consumes:
#   - SKILL-PHASE-2.md (the Phase 2 operator manifest)
#   - schemas/handoff-v1.schema.json (handoff contract from Phase 1)
#   - docs/BIPHASIC-ARCHITECTURE.md (reference for the 7 gates)
#   - scripts/phase2_*.py + the 3 new gate scripts
# Phase 1 (chat) needs only SKILL.md + references/ + assets/templates/.
BIPHASIC_GLOB: tuple[tuple[str, str], ...] = (
    ("schemas", "*.json"),
    ("docs", "BIPHASIC-ARCHITECTURE.md"),
)

# --- Runtime knowledge base (references/) ------------------------------
# What the skill *reads* at runtime. Excluded:
#   - calibration-corpus.json (907 KB benchmark fixture, not runtime)
#   - audits/ (internal audit reports), claude-chat-tasks/, draft/,
#     calibrations/ — historical/operational, not consumed at runtime
#   - profiles/_guidelines/ — reporting standards consumed only when
#     the matching mode is selected; lazy-loadable by mode
#   - profiles/venues_q2_int/ + profiles/venues_fallback_br/ — lower-
#     priority Qualis strata, deferred to a follow-up package
REFERENCES_ROOT_GLOB: tuple[tuple[str, str], ...] = (
    # Fix 18 (RS-42 / XML migration): the long-form reference docs
    # migrated from Markdown to XML in F1-F5. The XML envelope wraps the
    # original Markdown body inside CDATA — lossless, with a tiny
    # semantic envelope (id / path / type / lang / <title>) for
    # downstream tooling.
    ("references", "*.xml"),
    ("references", "*.json"),
    ("references/citation-styles", "*.xml"),
    ("references/databases", "*.xml"),
    ("references/modes", "*.xml"),
    # _schema/ is documentation-only — referenced as a comment in
    # scripts/assessor/eliminators.py but never loaded at runtime.
    # Excluded to fit under the 200-file cap.
    ("references/profiles/venues_a1_br", "*.yaml"),
    ("references/profiles/venues_a3_br", "*.yaml"),
    ("references/profiles/venues_b1_br", "*.yaml"),
    ("references/profiles/venues_q1_int", "*.yaml"),
    ("references/user-guidance", "*.xml"),
)
# Excluded individually (subtracted from the glob result above):
REFERENCES_EXCLUDE: frozenset[str] = frozenset(
    {
        "references/calibration-corpus.json",  # 907 KB benchmark, not runtime
    }
)

# --- Templates the skill emits as scaffolding --------------------------
# The skill consumes both the top-level templates (manuscript skeleton,
# extraction form, quality appraisal, protocol) AND the per-mode
# protocol scaffolds under modes/ (mode-systematic-review-strict.xml,
# mode-scoping-review.xml, mode-rapid-review.xml, etc. — one per skill
# mode in `references/modes/`). The Markdown sources were migrated to
# XML in Fix 18 (RS-42 remediation, F1-F5).
ASSETS_GLOB: tuple[tuple[str, str], ...] = (
    # *.html (manuscript-template.html) + *.xml (the migrated templates).
    # The previous "*" glob also picked up build artifacts; explicit
    # extensions are safer.
    ("assets/templates", "*.html"),
    ("assets/templates", "*.xml"),
    ("assets/templates/modes", "*.xml"),
)


# --- XML bundle stages (Fix 18 / F8) -----------------------------------
# When ``--bundle-xml`` is passed at build time, individual XML files in
# the directories below are *replaced* in the final package by a single
# ``bundle-<stage>.xml`` artifact each — collapsing 32 docs to 5 bundle
# files (saves 27 files in the production zip). Authors keep editing
# one source XML per concept; the bundles are build-only artifacts.
#
# The mapping mirrors :data:`bundle_xml.DEFAULT_BUNDLES`. Top-level
# ``references/*.xml`` is intentionally NOT bundled (heterogeneous docs).
BUNDLE_STAGES: tuple[tuple[str, str], ...] = (
    ("references/citation-styles", "citation-styles"),
    ("references/databases", "databases"),
    ("references/modes", "modes"),
    ("assets/templates/modes", "templates-modes"),
)

# --- v2 production scripts (currently the production runtime path) ----
# v3 src/ignorantia is alpha (rc1) and lives in the tree but ships with
# its own pip-installable package; the skill still drives v2 entry
# points until the dogfooding sprint signs off (see issue #10).
SCRIPTS_TOP_GLOB: tuple[tuple[str, str], ...] = (
    ("scripts", "*.py"),
)
SCRIPTS_SUBDIR_GLOB: tuple[tuple[str, str], ...] = (
    ("scripts/searches", "*.py"),
    # Fix 15 — scripts/assessor/ is required at runtime by render_v2.py
    # (which imports from assessor.visual_aids) and unified_assessment.py.
    # Excluding it broke both modules in deployed skills until v2.23.x;
    # the dogfood RS-42 transcripts diagnosed this as a packaging bug,
    # not a code bug. Adding the directory ships the ~10 modules that
    # the renderers and assessor entry points actually need.
    ("scripts/assessor", "*.py"),
)

# Upstream Anthropic skill packaging is documented to accept several
# hundred files; the previous cap of 200 was a self-imposed ceiling to
# force conscious review of additions. v2.23.1 raises the ceiling to
# 220 to admit the RS-42 remediation additions:
#   * Fix 12 — persona-voice scaffold (1 file under assets/templates/,
#     1 file under scripts/) → +2.
#   * Fix 15 — scripts/assessor/ packaging fix (~10 files) → +10.
# v3.0.0 biphasic refactor added ~10 files (SKILL-PHASE-2.md, the
# handoff schema, BIPHASIC-ARCHITECTURE.md, four phase2_*.py scripts,
# three new gate scripts). Default flow lands at ~222 files; with
# --bundle-xml the four bundleable directories collapse 28 individuals
# → 4 bundles, dropping the count by 24 to ~198. The ceiling at 250
# keeps modest headroom for follow-up.
MAX_FILES = 250


# ----------------------------------------------------------------------
# Allowlist resolution
# ----------------------------------------------------------------------


def _glob_dir(root: Path, rel_dir: str, pattern: str) -> list[Path]:
    """Expand ``rel_dir/pattern`` non-recursively, sorted, files only."""
    base = root / rel_dir
    if not base.is_dir():
        return []
    return sorted(p for p in base.glob(pattern) if p.is_file())


def resolve_allowlist(
    root: Path,
    *,
    bundle_xml: bool = False,
    bundle_dir: Path | None = None,
) -> list[Path]:
    """Return the full ordered list of files to ship.

    Sorted, deduplicated, all relative paths existing on disk.

    When ``bundle_xml`` is true, individual XML files inside
    :data:`BUNDLE_STAGES` directories are replaced by their corresponding
    ``bundle-<stage>.xml`` artifact (must already exist in
    ``bundle_dir``). The caller is responsible for generating the
    bundles before calling this function — :func:`build` does that via
    ``scripts/bundle_xml.py``.
    """
    out: list[Path] = []

    # Root files — explicit names.
    for name in ROOT_FILES:
        path = root / name
        if path.is_file():
            out.append(path)

    # References (with the per-file exclude list).
    excluded = {root / rel for rel in REFERENCES_EXCLUDE}

    # When bundling is on, individual XMLs in bundleable stage dirs are
    # replaced by their bundle. Build the suppression set first.
    bundled_dirs: set[Path] = set()
    bundle_artifacts: list[Path] = []
    if bundle_xml:
        if bundle_dir is None:
            raise ValueError("bundle_xml=True requires a bundle_dir")
        for rel_dir, stage in BUNDLE_STAGES:
            stage_dir = root / rel_dir
            if not stage_dir.is_dir():
                continue
            bundle_path = bundle_dir / f"bundle-{stage}.xml"
            if not bundle_path.is_file():
                raise FileNotFoundError(
                    f"bundle missing: {bundle_path} (expected one of "
                    f"--bundle-xml flow's pre-build artifacts)"
                )
            bundled_dirs.add(stage_dir.resolve())
            bundle_artifacts.append(bundle_path)

    def _maybe_skip(path: Path) -> bool:
        return path.suffix == ".xml" and path.parent.resolve() in bundled_dirs

    for rel_dir, pattern in REFERENCES_ROOT_GLOB:
        for path in _glob_dir(root, rel_dir, pattern):
            if path not in excluded and not _maybe_skip(path):
                out.append(path)

    # Assets, scripts.
    for rel_dir, pattern in ASSETS_GLOB:
        for path in _glob_dir(root, rel_dir, pattern):
            if not _maybe_skip(path):
                out.append(path)
    for rel_dir, pattern in SCRIPTS_TOP_GLOB:
        out.extend(_glob_dir(root, rel_dir, pattern))
    for rel_dir, pattern in SCRIPTS_SUBDIR_GLOB:
        out.extend(_glob_dir(root, rel_dir, pattern))
    # v3.0.0 biphasic artifacts (schema + design doc).
    for rel_dir, pattern in BIPHASIC_GLOB:
        out.extend(_glob_dir(root, rel_dir, pattern))

    # Append bundle artifacts last so they sit alongside the existing
    # references in the zip's TOC.
    out.extend(bundle_artifacts)

    # Dedup while preserving order.
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in out:
        if p in seen:
            continue
        seen.add(p)
        deduped.append(p)
    return deduped


# ----------------------------------------------------------------------
# pyproject parsing (no toml dep — read project.name + project.version)
# ----------------------------------------------------------------------

_NAME_RE = re.compile(r'^name\s*=\s*"([^"]+)"', re.MULTILINE)
_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def parse_pyproject(root: Path) -> tuple[str, str]:
    """Return ``(name, version)`` from ``pyproject.toml``."""
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    name_m = _NAME_RE.search(text)
    version_m = _VERSION_RE.search(text)
    if not name_m or not version_m:
        raise SystemExit("pyproject.toml is missing project.name or project.version")
    return name_m.group(1), version_m.group(1)


# ----------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------


def _generate_bundles(root: Path, bundle_dir: Path) -> None:
    """Generate every ``BUNDLE_STAGES`` artifact into ``bundle_dir``.

    Skips stage directories that don't exist or contain no XMLs. The
    bundles are temporary build artifacts — the function does not check
    them in.
    """
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for rel_dir, stage in BUNDLE_STAGES:
        source_dir = root / rel_dir
        if not source_dir.is_dir():
            continue
        if not list(source_dir.glob("*.xml")):
            continue
        out_path = bundle_dir / f"bundle-{stage}.xml"
        write_bundle(source_dir, stage, out_path)


def build(
    *,
    root: Path,
    name: str,
    version: str,
    output_dir: Path,
    dry_run: bool,
    bundle_xml: bool = False,
) -> Path:
    """Resolve the allowlist, validate the count, write the zip.

    Returns the absolute path of the zip (or the would-be path on
    ``--dry-run``). When ``bundle_xml`` is true, generates the
    ``BUNDLE_STAGES`` artifacts into a temp directory and substitutes
    them for the individual XMLs they cover (cuts the zip's file count).
    """
    bundle_tempdir: tempfile.TemporaryDirectory | None = None
    try:
        bundle_path: Path | None = None
        if bundle_xml:
            bundle_tempdir = tempfile.TemporaryDirectory(prefix="ignorantia-bundles-")
            bundle_path = Path(bundle_tempdir.name)
            _generate_bundles(root, bundle_path)

        files = resolve_allowlist(root, bundle_xml=bundle_xml, bundle_dir=bundle_path)
        count = len(files)

        print(f"Allowlist resolved: {count} files (limit {MAX_FILES})")
        if count == 0:
            raise SystemExit("ERROR: allowlist resolved to zero files; nothing to package")

        if count > MAX_FILES:
            print(
                f"\nERROR: {count} > {MAX_FILES} files. Trim the allowlist before "
                f"building. Last {count - MAX_FILES} files (alphabetical tail):",
                file=sys.stderr,
            )
            for p in files[MAX_FILES:]:
                print(f"  {_archive_name(p, root, bundle_path)}", file=sys.stderr)
            raise SystemExit(2)

        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / f"{name}-{version}.zip"

        if dry_run:
            print(f"\n[dry-run] Would write {zip_path} containing:")
            for p in files:
                print(f"  {_archive_name(p, root, bundle_path)}")
            return zip_path

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for p in files:
                zf.write(p, arcname=_archive_name(p, root, bundle_path))

        print(f"\nWrote {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")
        return zip_path
    finally:
        if bundle_tempdir is not None:
            bundle_tempdir.cleanup()


def _archive_name(p: Path, root: Path, bundle_dir: Path | None) -> str:
    """Compute the in-zip path for a source file.

    Bundle artifacts live in a temp directory (not under ``root``); they
    are stored at ``references/bundles/<name>.xml`` inside the zip so
    the production layout has a predictable home for them. Everything
    else uses its repo-relative path.
    """
    if bundle_dir is not None:
        try:
            rel = p.resolve().relative_to(bundle_dir.resolve())
            return f"references/bundles/{rel.as_posix()}"
        except ValueError:
            pass
    return p.relative_to(root).as_posix()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dist",
        help="Directory to write the zip into (default: ./dist).",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Override project name (default: from pyproject.toml).",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Override SemVer (default: from pyproject.toml).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the file list and the count without writing the zip.",
    )
    parser.add_argument(
        "--bundle-xml",
        action="store_true",
        help=("Bundle same-stage XML reference docs into single artifacts at "
              "build time (Fix 18 / F8). Reduces the production zip's file "
              "count without touching the source tree."),
    )
    args = parser.parse_args(argv)

    pyproj_name, pyproj_version = parse_pyproject(ROOT)
    name = args.name or pyproj_name
    version = args.version or pyproj_version

    build(
        root=ROOT,
        name=name,
        version=version,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        bundle_xml=args.bundle_xml,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
