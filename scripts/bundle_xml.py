#!/usr/bin/env python3
"""
bundle_xml.py — Consolidate same-stage XML reference documents.

Fix 18 / Phase 6 of the RS-42 dogfood remediation series.

Background
----------
F1-F5 migrated 71 reference Markdown files to individual XML envelopes
(``<doc>`` per file). The skill ships these as prompt material; the
production-package allowlist (in ``build_production_package.py``) is
ceiling-bound at 220 files. Even after the migration, individual XML
files for each citation style / database / mode add up.

This phase ships the **bundler**: a tool that consolidates several
``<doc>`` files of the same semantic stage into a single
``<doc_bundle>`` artifact. Bundling preserves all content (each
``<doc>`` element is embedded verbatim) and reduces the file count.

Categories that benefit (savings per category):

  references/citation-styles/      4 docs → 1 bundle (saves 3 files)
  references/databases/            3 docs → 1 bundle (saves 2 files)
  references/claude-chat-tasks/    4 docs → 1 bundle (saves 3 files)
  references/modes/                11 docs → 1 bundle (saves 10 files)
  assets/templates/modes/          10 docs → 1 bundle (saves 9 files)

Top-level ``references/*.xml`` (24 heterogeneous docs) is intentionally
**not** bundled — each top-level doc stands on its own semantically.

Output schema
-------------
::

    <?xml version="1.0" encoding="UTF-8"?>
    <doc_bundle stage="citation-styles" count="4">
      <doc id="abnt" path="references/citation-styles/abnt.xml"
           type="citation-style" lang="pt-BR">
        <title>ABNT — Norma brasileira para citações e referências</title>
        <markdown><![CDATA[...]]></markdown>
      </doc>
      <doc id="apa" ...>
        <title>...</title>
        <markdown><![CDATA[...]]></markdown>
      </doc>
      ...
    </doc_bundle>

The ``stage`` attribute identifies the semantic category; ``count``
records the number of bundled docs for quick inspection. Each
``<doc>`` is preserved verbatim from its source file.

Usage
-----
::

    # Bundle one directory
    python3 scripts/bundle_xml.py references/citation-styles \\
        --stage citation-styles --out dist/bundle-citation-styles.xml

    # Bundle every documented category at once (default mapping below)
    python3 scripts/bundle_xml.py --all --out-dir dist/bundles/

    # Dry-run (show source files + planned output)
    python3 scripts/bundle_xml.py references/modes \\
        --stage modes --out dist/bundle-modes.xml --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Default mapping used by ``--all``. Each entry is (source_dir, stage_name).
# The stage name becomes the ``stage="..."`` attribute on the bundle root
# and the suffix of the output filename (``bundle-<stage>.xml``).
DEFAULT_BUNDLES: tuple[tuple[str, str], ...] = (
    ("references/citation-styles", "citation-styles"),
    ("references/databases", "databases"),
    ("references/claude-chat-tasks", "claude-chat-tasks"),
    ("references/modes", "modes"),
    ("assets/templates/modes", "templates-modes"),
)


def _read_doc_xml(source: Path) -> str:
    """Read a single-doc XML file and return the inner ``<doc>...</doc>`` text.

    We avoid round-tripping through ``ElementTree.tostring`` because that
    would strip the CDATA section and re-emit the body as plain text with
    XML escapes — defeating the lossless contract the converter
    established. Instead we slice the file text between the first ``<doc``
    occurrence and the closing ``</doc>`` and copy it verbatim.
    """
    text = source.read_text(encoding="utf-8")
    open_match = re.search(r"<doc[\s>]", text)
    if not open_match:
        raise ValueError(f"{source}: no <doc> opening tag found")
    close_idx = text.rfind("</doc>")
    if close_idx == -1:
        raise ValueError(f"{source}: no </doc> closing tag found")
    return text[open_match.start():close_idx + len("</doc>")]


def bundle_directory(
    source_dir: Path,
    stage: str,
    *,
    pattern: str = "*.xml",
    skip_bundles: bool = True,
) -> str:
    """Read every ``*.xml`` in ``source_dir`` and return one bundle string.

    ``skip_bundles`` filters out files whose root tag is already a
    ``<doc_bundle>`` so re-bundling is idempotent.
    """
    sources = sorted(source_dir.glob(pattern))
    docs: list[str] = []
    for src in sources:
        # Skip pre-existing bundles to keep --all idempotent.
        if skip_bundles:
            head = src.read_text(encoding="utf-8")[:512]
            if "<doc_bundle" in head:
                continue
        docs.append(_read_doc_xml(src))

    if not docs:
        raise ValueError(f"no <doc> sources found under {source_dir}")

    # Indent each <doc> block by two spaces for readability inside the bundle.
    indented = []
    for d in docs:
        indented.append("\n".join("  " + line if line else line
                                   for line in d.splitlines()))

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<doc_bundle stage="{stage}" count="{len(docs)}">\n'
        + "\n".join(indented)
        + "\n</doc_bundle>\n"
    )


def write_bundle(
    source_dir: Path,
    stage: str,
    out_path: Path,
    *,
    pattern: str = "*.xml",
    dry_run: bool = False,
) -> Path:
    """Build a bundle from ``source_dir`` and write it to ``out_path``."""
    bundle = bundle_directory(source_dir, stage, pattern=pattern)
    if dry_run:
        sources = sorted(source_dir.glob(pattern))
        print(f"[dry-run] {source_dir} ({len(sources)} files) → {out_path}")
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(bundle, encoding="utf-8")
    print(f"[bundle] {source_dir} → {out_path}")
    return out_path


def bundle_all_defaults(
    out_dir: Path,
    *,
    repo_root: Path,
    dry_run: bool = False,
) -> list[Path]:
    """Build every bundle in :data:`DEFAULT_BUNDLES` under ``out_dir``."""
    written: list[Path] = []
    for rel_source, stage in DEFAULT_BUNDLES:
        source_dir = repo_root / rel_source
        if not source_dir.is_dir():
            print(f"[skip] {source_dir} does not exist", file=sys.stderr)
            continue
        out_path = out_dir / f"bundle-{stage}.xml"
        written.append(write_bundle(source_dir, stage, out_path, dry_run=dry_run))
    return written


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bundle same-stage XML reference documents into one file.",
    )
    parser.add_argument("source", type=Path, nargs="?", default=None,
                        help="Source directory (single-bundle mode).")
    parser.add_argument("--stage", default=None,
                        help="Stage name (single-bundle mode).")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output bundle path (single-bundle mode).")
    parser.add_argument("--all", dest="bundle_all", action="store_true",
                        help="Build every default-mapping bundle (uses --out-dir).")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output directory (--all mode).")
    parser.add_argument("--pattern", default="*.xml",
                        help="Source glob pattern (default: *.xml).")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(),
                        help="Repo root used in --all mode to resolve sources.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without touching disk.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    if args.bundle_all:
        if args.out_dir is None:
            print("ERRO: --all requer --out-dir.", file=sys.stderr)
            return 2
        bundle_all_defaults(args.out_dir, repo_root=args.repo_root, dry_run=args.dry_run)
        return 0

    if args.source is None:
        print("ERRO: forneça <source> e --stage/--out, ou use --all com --out-dir.",
              file=sys.stderr)
        return 2

    if args.stage is None or args.out is None:
        print("ERRO: --stage e --out são obrigatórios em modo single-bundle.",
              file=sys.stderr)
        return 2

    if not args.source.is_dir():
        print(f"ERRO: source não é um diretório: {args.source}", file=sys.stderr)
        return 1

    write_bundle(args.source, args.stage, args.out,
                 pattern=args.pattern, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
