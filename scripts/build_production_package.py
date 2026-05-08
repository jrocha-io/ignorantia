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
import zipfile
from pathlib import Path

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
ROOT_FILES: tuple[str, ...] = (
    "SKILL.md",            # entry point read by Claude
    "README.md",           # user-facing landing
    "LICENSE",
    "CHANGELOG.md",
    "pyproject.toml",      # package metadata; consumed by build_production_package
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
    ("references", "*.md"),
    ("references", "*.json"),
    ("references/citation-styles", "*.md"),
    ("references/databases", "*"),
    ("references/modes", "*.md"),
    # _schema/ is documentation-only — referenced as a comment in
    # scripts/assessor/eliminators.py but never loaded at runtime.
    # Excluded to fit under the 200-file cap.
    ("references/profiles/venues_a1_br", "*.yaml"),
    ("references/profiles/venues_a3_br", "*.yaml"),
    ("references/profiles/venues_b1_br", "*.yaml"),
    ("references/profiles/venues_q1_int", "*.yaml"),
    ("references/user-guidance", "*"),
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
# protocol scaffolds under modes/ (mode-systematic-review-strict.md,
# mode-scoping-review.md, mode-rapid-review.md, etc. — one per skill
# mode in `references/modes/`).
ASSETS_GLOB: tuple[tuple[str, str], ...] = (
    ("assets/templates", "*"),
    ("assets/templates/modes", "*.md"),
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
# Together: 200 → ~212. The ceiling at 220 leaves modest headroom for
# the remaining Fixes 13/14/16/17 without forcing immediate trimming.
# Bump back to 200 once the remediation series stabilises and any
# now-redundant files are removed.
MAX_FILES = 220


# ----------------------------------------------------------------------
# Allowlist resolution
# ----------------------------------------------------------------------


def _glob_dir(root: Path, rel_dir: str, pattern: str) -> list[Path]:
    """Expand ``rel_dir/pattern`` non-recursively, sorted, files only."""
    base = root / rel_dir
    if not base.is_dir():
        return []
    return sorted(p for p in base.glob(pattern) if p.is_file())


def resolve_allowlist(root: Path) -> list[Path]:
    """Return the full ordered list of files to ship.

    Sorted, deduplicated, all relative paths existing on disk.
    """
    out: list[Path] = []

    # Root files — explicit names.
    for name in ROOT_FILES:
        path = root / name
        if path.is_file():
            out.append(path)

    # References (with the per-file exclude list).
    excluded = {root / rel for rel in REFERENCES_EXCLUDE}
    for rel_dir, pattern in REFERENCES_ROOT_GLOB:
        for path in _glob_dir(root, rel_dir, pattern):
            if path not in excluded:
                out.append(path)

    # Assets, scripts.
    for rel_dir, pattern in ASSETS_GLOB:
        out.extend(_glob_dir(root, rel_dir, pattern))
    for rel_dir, pattern in SCRIPTS_TOP_GLOB:
        out.extend(_glob_dir(root, rel_dir, pattern))
    for rel_dir, pattern in SCRIPTS_SUBDIR_GLOB:
        out.extend(_glob_dir(root, rel_dir, pattern))

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


def build(
    *,
    root: Path,
    name: str,
    version: str,
    output_dir: Path,
    dry_run: bool,
) -> Path:
    """Resolve the allowlist, validate the count, write the zip.

    Returns the absolute path of the zip (or the would-be path on
    ``--dry-run``).
    """
    files = resolve_allowlist(root)
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
            print(f"  {p.relative_to(root)}", file=sys.stderr)
        raise SystemExit(2)

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{name}-{version}.zip"

    if dry_run:
        print(f"\n[dry-run] Would write {zip_path} containing:")
        for p in files:
            print(f"  {p.relative_to(root)}")
        return zip_path

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            zf.write(p, arcname=str(p.relative_to(root)))

    print(f"\nWrote {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")
    return zip_path


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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
