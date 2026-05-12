#!/usr/bin/env python3
"""Phase 2 — parse retrieved sources into LLM-readable text.

Reads every file in ``<run_dir>/sources/`` (output of
``phase2_retrieve.py``), extracts text plus structural metadata, and
writes:

- ``<run_dir>/parsed/<doi-slug>.txt`` — one plain-text file per source,
  with page boundaries (``--- p.N ---``) preserved for PDFs and
  semantic ``<h1>``/``<h2>`` boundaries preserved for HTML.
- ``<run_dir>/sources_index.json`` — one record per source with
  ``{doi, source_file, source_kind, page_count, word_count,
  title_guess, parsed_path}``. The cowork session uses this index to
  decide which sources to read in depth.

This script intentionally does *not* synthesise the manuscript or
build ``claim_to_source.json``. Those are LLM tasks performed by the
operator-Claude in cowork — phase2_extract gives that Claude the raw
materials it needs (parsed text + an index of what's available).

PDF parsing uses ``pypdf`` when installed (declared as the optional
``[parse]`` extra). When ``pypdf`` is missing, a minimal pure-Python
fallback extracts the catalog page count and a best-effort text dump
— enough for the index but not for serious extraction.

HTML parsing uses stdlib ``html.parser`` to strip tags while
preserving heading anchors.

Usage::

    python3 scripts/phase2_extract.py runs/<run-id>/

Exit codes:

* ``0`` — every source was parsed (or sniffed as unsupported); index written.
* ``1`` — input error (run dir missing, no sources, etc.).
* ``2`` — at least one source failed parsing AND the failure is hard
  enough to block downstream extraction.
"""

from __future__ import annotations

import argparse
import html
import html.parser
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# ── DOI recovery from filename ─────────────────────────────────────────


def filename_slug_to_doi(slug: str) -> str:
    """Best-effort reverse of ``doi_to_filename_slug``.

    The slug encoding (``10.1234/foo.bar`` → ``10-1234-foo-bar``) is
    lossy: dashes in the original DOI become indistinguishable from
    dashes used as separators. We split on the FIRST dash (between
    ``10`` and the registrant) and use a slash there, then leave the
    rest as the suffix with original-style separators.

    Returns ``slug`` itself if we can't recover a plausible DOI shape.
    """
    if not slug.startswith("10-"):
        return slug
    parts = slug.split("-", 2)
    if len(parts) < 3:
        return slug
    return f"{parts[0]}.{parts[1]}/{parts[2]}"


# ── PDF text extraction ────────────────────────────────────────────────


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedSource:
    doi: str
    source_file: Path
    source_kind: str  # "pdf" | "html"
    page_count: int = 0
    word_count: int = 0
    title_guess: str = ""
    pages: list[ParsedPage] = field(default_factory=list)
    error: str = ""


def parse_pdf(path: Path) -> ParsedSource:
    """Extract text from a PDF.

    Strategy:
    1. Try ``pypdf`` (the modern PyPDF2 successor) — produces per-page text.
    2. Fallback: minimal pure-Python parser that pulls the catalog
       page count and a best-effort text dump from text streams. The
       fallback is good enough for the index but degrades extraction
       quality.
    """
    out = ParsedSource(
        doi=filename_slug_to_doi(path.stem),
        source_file=path,
        source_kind="pdf",
    )
    try:
        import pypdf  # type: ignore[import-untyped]
    except ImportError:
        pypdf = None

    if pypdf is not None:
        try:
            reader = pypdf.PdfReader(str(path))
            out.page_count = len(reader.pages)
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                out.pages.append(ParsedPage(page_number=i, text=text))
            # Title heuristic: PDF metadata first, else first non-empty line
            try:
                meta_title = reader.metadata.title if reader.metadata else None
                if meta_title:
                    out.title_guess = str(meta_title).strip()
            except Exception:  # noqa: BLE001
                pass
            if not out.title_guess and out.pages:
                first_lines = [
                    line.strip()
                    for line in out.pages[0].text.split("\n")
                    if line.strip()
                ]
                if first_lines:
                    out.title_guess = first_lines[0][:200]
            out.word_count = sum(len(p.text.split()) for p in out.pages)
        except Exception as e:  # noqa: BLE001
            out.error = f"pypdf failed: {e}"
    else:
        # Fallback: read /Count and best-effort text dump.
        try:
            raw = path.read_bytes()
            m = re.search(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", raw)
            if not m:
                m = re.search(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages", raw)
            if m:
                out.page_count = int(m.group(1))
            # Pull text from BT...ET blocks (very rough).
            text_blobs = re.findall(rb"BT\s+(.*?)\s+ET", raw, re.DOTALL)
            text = b"\n".join(text_blobs).decode("utf-8", errors="replace")
            # Strip PostScript operators (heuristic).
            text = re.sub(r"/\w+\s+", "", text)
            text = re.sub(r"\[\s*[\d.-]+\s*\]", "", text)
            text = re.sub(r"<[0-9A-Fa-f]+>", "", text)
            if out.page_count > 0:
                out.pages = [ParsedPage(page_number=1, text=text)]
            out.word_count = len(text.split())
            out.error = "pypdf not installed; fallback parser produced rough text only"
        except Exception as e:  # noqa: BLE001
            out.error = f"fallback parser failed: {e}"

    return out


# ── HTML text extraction ───────────────────────────────────────────────


class _HtmlTextExtractor(html.parser.HTMLParser):
    """Tag-stripping HTML parser that preserves heading boundaries.

    We collect plain text plus a parallel list of headings (level + text)
    so the index can show a section-level outline.
    """

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.headings: list[tuple[int, str]] = []
        self.title: str = ""
        self._in_skip = 0  # depth of <script>/<style> we're inside
        self._in_title = False
        self._in_heading: int | None = None
        self._heading_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs):  # noqa: ANN001
        if tag in ("script", "style", "noscript"):
            self._in_skip += 1
            return
        if tag == "title":
            self._in_title = True
            return
        m = re.match(r"^h([1-6])$", tag)
        if m:
            self._in_heading = int(m.group(1))
            self._heading_buf = []
            self.parts.append(f"\n\n## (h{m.group(1)}) ")
            return

    def handle_endtag(self, tag: str):
        if tag in ("script", "style", "noscript"):
            self._in_skip = max(0, self._in_skip - 1)
            return
        if tag == "title":
            self._in_title = False
            return
        if self._in_heading and re.match(r"^h([1-6])$", tag):
            heading_text = " ".join(self._heading_buf).strip()
            if heading_text:
                self.headings.append((self._in_heading, heading_text))
            self._in_heading = None
            self.parts.append("\n")
            return

    def handle_data(self, data: str):
        if self._in_skip:
            return
        if self._in_title:
            self.title += data
            return
        if self._in_heading is not None:
            self._heading_buf.append(data)
        self.parts.append(data)


def parse_html(path: Path) -> ParsedSource:
    """Extract text + headings from HTML."""
    out = ParsedSource(
        doi=filename_slug_to_doi(path.stem),
        source_file=path,
        source_kind="html",
    )
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        parser = _HtmlTextExtractor()
        parser.feed(raw)
        parser.close()
        text = html.unescape("".join(parser.parts))
        # Squeeze whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        out.pages = [ParsedPage(page_number=1, text=text)]
        out.word_count = len(text.split())
        out.title_guess = parser.title.strip()[:200]
        if not out.title_guess and parser.headings:
            out.title_guess = parser.headings[0][1][:200]
    except Exception as e:  # noqa: BLE001
        out.error = f"HTML parser failed: {e}"
    return out


# ── per-source dispatch ────────────────────────────────────────────────


def parse_source(path: Path) -> ParsedSource:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix in (".html", ".htm"):
        return parse_html(path)
    # Unknown extension — record as empty parsed
    return ParsedSource(
        doi=filename_slug_to_doi(path.stem),
        source_file=path,
        source_kind="unknown",
        error=f"unsupported extension: {suffix}",
    )


def write_parsed_text(parsed: ParsedSource, dest_dir: Path) -> Path:
    """Dump the parsed text with page boundaries to a plain ``.txt`` file."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / f"{parsed.source_file.stem}.txt"
    blocks: list[str] = []
    if parsed.title_guess:
        blocks.append(f"# {parsed.title_guess}\n")
    blocks.append(f"DOI: {parsed.doi}\n")
    blocks.append(f"Source: {parsed.source_file.name}\n")
    if parsed.error:
        blocks.append(f"\n[parser warning: {parsed.error}]\n")
    for page in parsed.pages:
        blocks.append(f"\n--- p.{page.page_number} ---\n")
        blocks.append(page.text or "(no text extracted from this page)\n")
    out_path.write_text("".join(blocks), encoding="utf-8")
    return out_path


# ── main pipeline ──────────────────────────────────────────────────────


def extract_all(run_dir: Path) -> dict:
    """Walk sources/ and build the index. Returns the summary."""
    sources_dir = run_dir / "sources"
    parsed_dir = run_dir / "parsed"
    if not sources_dir.is_dir():
        raise FileNotFoundError(f"{sources_dir} not found")

    index: list[dict] = []
    n_parsed = 0
    n_failed = 0
    for path in sorted(sources_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".pdf", ".html", ".htm"):
            continue
        parsed = parse_source(path)
        parsed_path = write_parsed_text(parsed, parsed_dir)
        if parsed.error and not parsed.pages:
            n_failed += 1
        else:
            n_parsed += 1
        index.append(
            {
                "doi": parsed.doi,
                "source_file": parsed.source_file.name,
                "source_kind": parsed.source_kind,
                "page_count": parsed.page_count,
                "word_count": parsed.word_count,
                "title_guess": parsed.title_guess,
                "parsed_path": str(parsed_path.relative_to(run_dir)),
                "error": parsed.error,
            }
        )

    index_path = run_dir / "sources_index.json"
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "total_sources": len(index),
        "parsed": n_parsed,
        "failed": n_failed,
        "index_path": str(index_path.relative_to(run_dir)),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2 — parse retrieved sources (PDF/HTML) into "
            "plain-text + an index for the cowork session to consume."
        )
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Run dir bootstrapped by phase2_init.py and populated by "
        "phase2_retrieve.py.",
    )
    args = parser.parse_args(argv)

    if not args.run_dir.is_dir():
        print(f"ERROR: run dir not found: {args.run_dir}", file=sys.stderr)
        return 1
    if not (args.run_dir / "sources").is_dir():
        print(
            f"ERROR: {args.run_dir}/sources/ not found. "
            f"Did you run phase2_retrieve.py first?",
            file=sys.stderr,
        )
        return 1

    try:
        summary = extract_all(args.run_dir)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: extraction pipeline crashed: {e}", file=sys.stderr)
        return 2

    state_path = args.run_dir / "phase2_state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("completed_steps", []).append("extract")
        state["extraction"] = summary
        state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(
        f"Extraction complete: {summary['parsed']} parsed, "
        f"{summary['failed']} failed (index at {summary['index_path']})."
    )
    if summary["failed"]:
        return _GATE_EXIT_CODE
    return 0


_GATE_EXIT_CODE = 2


if __name__ == "__main__":
    sys.exit(main())
