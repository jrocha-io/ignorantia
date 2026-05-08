#!/usr/bin/env python3
"""
migrate_md_to_xml.py — Convert reference Markdown files to semantic XML.

Fix 18 / Phase 1 of the RS-42 dogfood remediation series.

Background
----------
The skill ships ~72 long-form reference documents (citation styles, mode
templates, database catalogs, claude-chat-tasks recipes). They are used
as prompt material — never parsed programmatically. The dogfood revealed
two structural problems:

  1. The production package's 220-file ceiling is approached by these MD
     files alone. Bundling reduces the count without losing information.
  2. Markdown is heuristically structured; XML with semantic tags lets a
     bundler consolidate same-stage documents and keeps content addressable.

Strategy
--------
Wrap the Markdown body in a CDATA section inside a tiny XML envelope that
records identity (``id``, ``path``, ``type``, ``lang``) and exposes the
title as an XML attribute for downstream tools. The body itself remains
Markdown — authors keep writing naturally, and the (already lossless)
prompt-injection consumers can either embed the XML as-is or extract the
``<markdown>`` payload.

Output schema
-------------
Single-document file::

    <?xml version="1.0" encoding="UTF-8"?>
    <doc id="abnt" path="references/citation-styles/abnt.md"
         type="citation-style" lang="pt-BR">
      <title>ABNT — Norma brasileira para citações e referências</title>
      <markdown><![CDATA[
    # ABNT — Norma brasileira para citações e referências
    ...full markdown body...
      ]]></markdown>
    </doc>

The schema is intentionally minimal. Phase 6 (the bundler) will wrap
multiple ``<doc>`` elements in a ``<doc_bundle stage="...">`` envelope.

Usage
-----
::

    # Single file
    python3 scripts/migrate_md_to_xml.py path/to/file.md \\
        --type citation-style --out path/to/file.xml

    # Whole directory (preserves layout, .md → .xml)
    python3 scripts/migrate_md_to_xml.py references/citation-styles/ \\
        --type citation-style --out-dir references/citation-styles/

    # Dry-run (print what would be written, no file writes)
    python3 scripts/migrate_md_to_xml.py references/modes/ \\
        --type mode --out-dir references/modes/ --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Default heuristics for inferring the ``type`` attribute from a source path.
# Phase 2-5 migrations explicitly pass ``--type`` so these are best-effort
# defaults for ad-hoc invocations.
_TYPE_BY_DIR_FRAGMENT: tuple[tuple[str, str], ...] = (
    ("citation-styles", "citation-style"),
    ("databases", "database-catalog"),
    ("modes", "mode-spec"),
    ("claude-chat-tasks", "chat-task"),
    ("user-guidance", "user-guidance"),
    ("audits", "audit-log"),
    ("calibrations", "calibration"),
    ("draft", "draft"),
    ("templates", "template"),
)

# CDATA close marker — must be neutralized inside the body so the section is
# not closed prematurely. `]]>` becomes `]]]]><![CDATA[>` (the standard split).
_CDATA_END = "]]>"
_CDATA_END_ESCAPE = "]]]]><![CDATA[>"


def slugify(text: str) -> str:
    """Lowercase ASCII slug used for the ``id`` attribute when not derived
    from the filename."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def infer_type(source_path: Path) -> str:
    """Best-effort ``type`` inference from path components."""
    parts = [p.lower() for p in source_path.parts]
    for fragment, label in _TYPE_BY_DIR_FRAGMENT:
        if fragment in parts:
            return label
    return "document"


def extract_title(markdown_body: str, fallback: str) -> str:
    """Return the first ATX H1 heading (``# Title``) or the fallback when
    no H1 is found."""
    for line in markdown_body.splitlines():
        line = line.lstrip()
        if line.startswith("# ") and not line.startswith("##"):
            return line[2:].strip()
    return fallback


def escape_for_xml_attribute(text: str) -> str:
    """Minimal XML attribute escaping: ``<>&"`` only.

    ``&`` must come first to avoid double-escaping the others.
    """
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def escape_cdata_body(text: str) -> str:
    """Neutralize ``]]>`` sequences inside the body so they do not close
    the surrounding CDATA section prematurely."""
    return text.replace(_CDATA_END, _CDATA_END_ESCAPE)


def build_xml(
    *,
    doc_id: str,
    source_path: Path,
    doc_type: str,
    lang: str | None,
    title: str,
    markdown_body: str,
) -> str:
    """Assemble the XML envelope for one source document."""
    attrs = [
        f'id="{escape_for_xml_attribute(doc_id)}"',
        f'path="{escape_for_xml_attribute(str(source_path))}"',
        f'type="{escape_for_xml_attribute(doc_type)}"',
    ]
    if lang:
        attrs.append(f'lang="{escape_for_xml_attribute(lang)}"')
    attrs_str = " ".join(attrs)

    safe_body = escape_cdata_body(markdown_body)
    safe_title = escape_for_xml_attribute(title)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"<doc {attrs_str}>\n"
        f"  <title>{safe_title}</title>\n"
        "  <markdown><![CDATA[\n"
        f"{safe_body}\n"
        "  ]]></markdown>\n"
        "</doc>\n"
    )


def convert_file(
    source: Path,
    *,
    doc_type: str | None = None,
    lang: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """Read a Markdown file and return the XML envelope as a string."""
    if not source.is_file():
        raise FileNotFoundError(source)

    body = source.read_text(encoding="utf-8")
    inferred_type = doc_type or infer_type(source)
    fallback_title = source.stem.replace("-", " ").replace("_", " ").title()
    title = extract_title(body, fallback_title)
    doc_id = slugify(source.stem) or "document"

    # ``path`` should be relative to the repo root so the artifact stays
    # portable across machines. When ``repo_root`` isn't supplied, fall back
    # to the absolute path.
    if repo_root is not None:
        try:
            relpath = source.resolve().relative_to(repo_root.resolve())
        except ValueError:
            relpath = source
    else:
        relpath = source

    return build_xml(
        doc_id=doc_id,
        source_path=relpath,
        doc_type=inferred_type,
        lang=lang,
        title=title,
        markdown_body=body,
    )


def convert_directory(
    source_dir: Path,
    out_dir: Path,
    *,
    doc_type: str | None,
    lang: str | None,
    repo_root: Path | None,
    pattern: str = "*.md",
    dry_run: bool = False,
) -> list[Path]:
    """Convert every ``*.md`` file in ``source_dir`` and write XML siblings
    under ``out_dir``. Returns the list of output paths (real or planned)."""
    sources = sorted(source_dir.rglob(pattern))
    written: list[Path] = []
    for src in sources:
        relative = src.relative_to(source_dir)
        target = out_dir / relative.with_suffix(".xml")
        xml = convert_file(src, doc_type=doc_type, lang=lang, repo_root=repo_root)
        if dry_run:
            print(f"[dry-run] {src} → {target} ({len(xml)} chars)")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(xml, encoding="utf-8")
            print(f"[migrate] {src} → {target}")
        written.append(target)
    return written


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert reference Markdown documents to semantic XML.",
    )
    parser.add_argument("source", type=Path,
                        help="Markdown file OR directory to convert.")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output XML path (single-file mode).")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output directory (directory mode).")
    parser.add_argument("--type", dest="doc_type", default=None,
                        help="Override the type= attribute (otherwise inferred from path).")
    parser.add_argument("--lang", default=None,
                        help="Set the lang= attribute (e.g., pt-BR, en-US).")
    parser.add_argument("--pattern", default="*.md",
                        help="Glob pattern for directory mode (default: *.md).")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(),
                        help="Root used to compute portable path= attributes.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without touching disk.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    if args.source.is_file():
        if args.out is None:
            print("ERRO: --out é obrigatório quando source é um arquivo.",
                  file=sys.stderr)
            return 2
        xml = convert_file(
            args.source,
            doc_type=args.doc_type,
            lang=args.lang,
            repo_root=args.repo_root,
        )
        if args.dry_run:
            print(f"[dry-run] {args.source} → {args.out} ({len(xml)} chars)")
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(xml, encoding="utf-8")
            print(f"[migrate] {args.source} → {args.out}")
        return 0

    if args.source.is_dir():
        if args.out_dir is None:
            print("ERRO: --out-dir é obrigatório quando source é um diretório.",
                  file=sys.stderr)
            return 2
        convert_directory(
            args.source,
            args.out_dir,
            doc_type=args.doc_type,
            lang=args.lang,
            repo_root=args.repo_root,
            pattern=args.pattern,
            dry_run=args.dry_run,
        )
        return 0

    print(f"ERRO: source não é arquivo nem diretório: {args.source}",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
