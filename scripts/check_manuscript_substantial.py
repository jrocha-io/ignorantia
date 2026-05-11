#!/usr/bin/env python3
"""Gate 7 — manuscript-substantial.

Catches the failure mode where the synthesis is too thin to be a real
scientific manuscript — empty PDF, missing required sections, or
word-count below the threshold a peer reviewer would accept.

Three checks:

1. **PDF exists and compiled.** ``manuscript.pdf`` must be readable
   and have at least one page (rules out zero-byte / corrupted output
   from a silent ``pdflatex`` failure).
2. **Page count** ≥ ``--min-pages`` (default 12; 8 for rapid mode).
3. **Word count of body** ≥ ``--min-words`` (default 5000;
   3000 for rapid mode). Counted from ``manuscript.tex`` after
   stripping LaTeX commands.
4. **Required section headings** all present in ``manuscript.tex``:
   §00 Propósito, §01 CoI, §02 Introdução, §03 Pergunta de pesquisa,
   §04 Métodos, §05 Resultados, §06 Discussão, §07 Conclusões,
   §08 Evidência contrária, §09 Limitações. (Realist/Software/etc.
   modes can override via ``--required-sections``.)

PDF page counting uses ``pdfinfo`` from poppler-utils when available
(common in TeX Live installs); falls back to a tiny pure-Python parser
that reads ``/Count`` from the PDF's root page tree.

Exit codes:

* ``0`` — manuscript is substantial.
* ``1`` — input missing.
* ``2`` — at least one check failed.

Sidecar: ``manuscript_substantial_gate.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_GATE_SIDECAR_FILENAME = "manuscript_substantial_gate.json"
_GATE_EXIT_CODE = 2

_DEFAULT_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Propósito",
    "Conflito de interesse",
    "Introdução",
    "Pergunta de pesquisa",
    "Métodos",
    "Resultados",
    "Discussão",
    "Conclusões",
    "Evidência contrária",
    "Limitações",
)

# Matches \section{...}, \section*{...}, \subsection{...}, etc.
_SECTION_HEADING = re.compile(
    r"\\(?:section\*?|chapter\*?|paragraph\*?)\s*\{([^}]+)\}"
)


def count_pdf_pages(pdf_path: Path) -> int:
    """Return the page count of ``pdf_path``. Tries ``pdfinfo`` first,
    falls back to a minimal pure-Python PDF reader.

    Returns 0 when the file is unreadable or malformed.
    """
    if shutil.which("pdfinfo"):
        try:
            out = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if out.returncode == 0:
                m = re.search(r"^Pages:\s+(\d+)", out.stdout, re.MULTILINE)
                if m:
                    return int(m.group(1))
        except (subprocess.TimeoutExpired, OSError):
            pass
    # Fallback: read /Count from the catalog's Pages object.
    try:
        raw = pdf_path.read_bytes()
    except OSError:
        return 0
    # The page-tree root has ``/Type /Pages`` plus ``/Count N``. We look
    # for the first occurrence, which is the root in well-formed PDFs.
    m = re.search(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", raw)
    if m:
        return int(m.group(1))
    # Some PDFs put /Count before /Type — try the inverse order.
    m = re.search(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages", raw)
    if m:
        return int(m.group(1))
    return 0


def count_body_words(manuscript_tex: str) -> int:
    """Word count of the manuscript body after stripping LaTeX commands.

    The count is approximate — good enough to distinguish a 5000-word
    real manuscript from a 200-word stub. We strip:

      - preamble (everything before ``\\begin{document}``);
      - LaTeX commands ``\\command{...}`` (keep the inner text);
      - inline math ``$...$`` and display math;
      - comments (``% ... \\n``);
      - tables and figures (best-effort).
    """
    body_start = manuscript_tex.find(r"\begin{document}")
    if body_start == -1:
        return 0
    text = manuscript_tex[body_start:]
    text = re.sub(r"%[^\n]*", "", text)
    text = re.sub(r"\$[^$]*\$", "", text)
    text = re.sub(r"\\\[(.*?)\\\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{(table|figure|equation)\*?\}.*?\\end\{\1\*?\}", "",
                  text, flags=re.DOTALL)
    # Replace \command{arg} with the arg's text (keep word content).
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    words = re.findall(r"\w+", text)
    return len(words)


def find_required_sections(
    manuscript_tex: str, required: tuple[str, ...]
) -> list[str]:
    """Return the subset of ``required`` keywords NOT found among the
    section headings of the manuscript. Case-insensitive substring
    match per requirement keyword."""
    headings = " || ".join(_SECTION_HEADING.findall(manuscript_tex)).lower()
    missing: list[str] = []
    for needle in required:
        # Common diacritics: accept ASCII fold heuristically.
        normalised = needle.lower()
        # Try the keyword and a few canonical variants.
        if normalised in headings:
            continue
        # Try the first word (e.g. "Propósito" → "propósito")
        if normalised.split()[0] in headings:
            continue
        # Try without trailing diacritics by stripping common ones.
        ascii_fold = (
            normalised.replace("ó", "o")
            .replace("ê", "e")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ç", "c")
            .replace("ã", "a")
            .replace("õ", "o")
            .replace("á", "a")
            .replace("ú", "u")
        )
        if ascii_fold in headings or ascii_fold.split()[0] in headings:
            continue
        missing.append(needle)
    return missing


def check_substantial(
    pdf_path: Path,
    tex_path: Path,
    *,
    min_pages: int,
    min_words: int,
    required_sections: tuple[str, ...],
) -> dict:
    """Compute the substantive-content report."""
    page_count = count_pdf_pages(pdf_path) if pdf_path.is_file() else 0
    word_count = (
        count_body_words(tex_path.read_text(encoding="utf-8"))
        if tex_path.is_file()
        else 0
    )
    missing_sections = (
        find_required_sections(
            tex_path.read_text(encoding="utf-8"), required_sections
        )
        if tex_path.is_file()
        else list(required_sections)
    )
    return {
        "pdf_exists": pdf_path.is_file(),
        "page_count": page_count,
        "min_pages_required": min_pages,
        "page_count_ok": page_count >= min_pages,
        "word_count": word_count,
        "min_words_required": min_words,
        "word_count_ok": word_count >= min_words,
        "missing_sections": missing_sections,
        "sections_ok": not missing_sections,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gate 7 — verify the manuscript PDF compiled and has substantive "
            "content (page count, word count, required sections)."
        )
    )
    parser.add_argument(
        "deposit_dir",
        type=Path,
        help="Path to the deposit directory containing manuscript.pdf "
        "and manuscript.tex.",
    )
    parser.add_argument(
        "--manuscript-tex",
        default="manuscript.tex",
        help="Filename of the manuscript LaTeX source.",
    )
    parser.add_argument(
        "--manuscript-pdf",
        default="manuscript.pdf",
        help="Filename of the compiled manuscript PDF.",
    )
    parser.add_argument(
        "--min-pages",
        type=int,
        default=12,
        help="Minimum page count for a substantial manuscript (default 12; "
        "use 8 for rapid review).",
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=5000,
        help="Minimum word count for the manuscript body (default 5000; "
        "use 3000 for rapid review).",
    )
    parser.add_argument(
        "--required-sections",
        nargs="*",
        default=list(_DEFAULT_REQUIRED_SECTIONS),
        help="Keywords required to appear in section headings. Defaults to "
        "the 10-section IMRaD-adapted skeleton.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed diagnostics; emit only the summary.",
    )
    args = parser.parse_args(argv)

    if not args.deposit_dir.is_dir():
        print(f"ERROR: {args.deposit_dir} is not a directory", file=sys.stderr)
        return 1

    pdf_path = args.deposit_dir / args.manuscript_pdf
    tex_path = args.deposit_dir / args.manuscript_tex
    if not tex_path.is_file():
        print(f"ERROR: {tex_path} not found", file=sys.stderr)
        return 1

    report = check_substantial(
        pdf_path,
        tex_path,
        min_pages=args.min_pages,
        min_words=args.min_words,
        required_sections=tuple(args.required_sections),
    )
    passed = (
        report["pdf_exists"]
        and report["page_count_ok"]
        and report["word_count_ok"]
        and report["sections_ok"]
    )
    report["passed"] = passed

    sidecar_path = args.deposit_dir / _GATE_SIDECAR_FILENAME
    sidecar_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if passed:
        print(
            f"Manuscript-substantial check PASSED for {args.deposit_dir} "
            f"({report['page_count']} pages, {report['word_count']} words)"
        )
        return 0

    if not args.quiet:
        print(
            f"Manuscript-substantial check FAILED for {args.deposit_dir}",
            file=sys.stderr,
        )
        if not report["pdf_exists"]:
            print("  - manuscript.pdf not found (compilation failed?)", file=sys.stderr)
        elif not report["page_count_ok"]:
            print(
                f"  - page count {report['page_count']} < required "
                f"{report['min_pages_required']}",
                file=sys.stderr,
            )
        if not report["word_count_ok"]:
            print(
                f"  - body word count {report['word_count']} < required "
                f"{report['min_words_required']}",
                file=sys.stderr,
            )
        if report["missing_sections"]:
            print(
                f"  - {len(report['missing_sections'])} required section(s) "
                f"missing from headings:",
                file=sys.stderr,
            )
            for s in report["missing_sections"]:
                print(f"    · {s}", file=sys.stderr)
    return _GATE_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
