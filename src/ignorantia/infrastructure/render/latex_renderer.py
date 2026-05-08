r"""``LatexRenderer`` — concrete :class:`RendererPort` for LaTeX output.

Produces a self-contained ``article``-class LaTeX document with
``inputenc`` (UTF-8) and ``hyperref`` so the generated source can be
compiled by any modern engine (pdfLaTeX, xelatex, lualatex). Body
sections are passed through :func:`markdown_to_latex` to translate
the small Markdown vocabulary into ``\textbf{...}`` / ``\textit{...}``
commands.

The renderer has two bibliography modes:

* **Inline** (default, legacy): references are formatted via the
  injected :class:`CitationFormatterPort` and emitted in a
  ``thebibliography`` environment in the same ``.tex`` file.
  Compiles to PDF without an external ``.bib``, but is not the
  academic convention.

* **External BibTeX** (preferred for academic deposit, Decisão 36):
  pass ``bib_file`` + ``bibliography_style`` to the constructor.
  The renderer emits ``\bibliography{<bib_file>}`` +
  ``\bibliographystyle{<style>}`` + ``\nocite{*}`` so the
  ``pdflatex+bibtex+pdflatex+pdflatex`` cycle resolves entries
  from a sibling ``<bib_file>.bib`` (produced separately by
  :class:`BibFileRenderer`). The compile pipeline is the
  PDF-canonical academic path.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import BibTexStyle
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import OutputFormat
from ignorantia.infrastructure.render.markdown_to_latex import (
    latex_escape,
    markdown_to_latex,
)


class LatexRenderer(RendererPort):
    """Render :class:`ManuscriptDoc` as a standalone LaTeX article."""

    def __init__(
        self,
        *,
        formatter: CitationFormatterPort,
        bib_file: str | None = None,
        bibliography_style: BibTexStyle | None = None,
    ) -> None:
        r"""Wire the renderer to a citation formatter (Strategy).

        Args:
            formatter: The :class:`CitationFormatterPort` used by
                inline-mode bibliography rendering. Always required
                for backwards compatibility, even when ``bib_file``
                is supplied (the formatter is unused in external-
                BibTeX mode but kept on the constructor signature
                so call sites need not branch).
            bib_file: Filename (without ``.bib`` suffix) of the
                companion BibTeX database. When supplied, the
                renderer emits ``\\bibliography{<bib_file>}`` and
                ``\\bibliographystyle{<style>}`` instead of the
                inline ``thebibliography`` environment. Pair with
                :class:`BibFileRenderer` to produce both files.
            bibliography_style: The :class:`BibTexStyle` for
                ``\\bibliographystyle{}``. Required iff
                ``bib_file`` is given.

        Raises:
            ValueError: ``bib_file`` is given without
                ``bibliography_style`` (or vice-versa).
        """
        if (bib_file is None) != (bibliography_style is None):
            raise ValueError(
                "LatexRenderer: bib_file and bibliography_style must be supplied "
                "together (both or neither)"
            )
        self._formatter = formatter
        self._bib_file = bib_file
        self._bibliography_style = bibliography_style

    @property
    def output_format(self) -> OutputFormat:
        """Return :class:`OutputFormat.LATEX`."""
        return OutputFormat.LATEX

    def render(self, doc: ManuscriptDoc) -> bytes:
        """Render ``doc`` and return the LaTeX source as UTF-8 bytes."""
        parts: list[str] = [
            r"\documentclass{article}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage{hyperref}",
            f"\\title{{{latex_escape(doc.title)}}}",
            r"\begin{document}",
            r"\maketitle",
            _render_abstract(doc),
        ]
        if doc.keywords:
            parts.append(_render_keywords(doc.keywords))
        for section in doc.sections:
            parts.append(_render_section(section))
        if doc.references:
            parts.append(self._render_bibliography(doc.references))
        parts.append(r"\end{document}")
        return "\n".join(p for p in parts if p).encode("utf-8")

    def _render_bibliography(self, references: tuple[Reference, ...]) -> str:
        if self._bib_file is not None and self._bibliography_style is not None:
            return self._render_external_bibtex()
        return self._render_inline_bibliography(references)

    def _render_external_bibtex(self) -> str:
        r"""Emit ``\\nocite{*}`` + ``\\bibliographystyle{}`` + ``\\bibliography{}``.

        ``\\nocite{*}`` ensures every entry in the ``.bib`` appears
        in the rendered bibliography even when the manuscript body
        does not (yet) contain ``\\cite{<key>}`` calls. Once the
        prose pipeline learns to insert ``\\cite{}`` at inline
        citation sites, ``\\nocite{*}`` can be dropped.
        """
        return (
            r"\nocite{*}"
            "\n"
            f"\\bibliographystyle{{{self._bibliography_style}}}\n"
            f"\\bibliography{{{self._bib_file}}}"
        )

    def _render_inline_bibliography(self, references: tuple[Reference, ...]) -> str:
        digits = max(2, len(str(len(references))))
        items = "\n".join(
            f"\\bibitem{{ref{i + 1}}} {self._formatter.format_reference(r)}"
            for i, r in enumerate(references)
        )
        return (
            f"\\begin{{thebibliography}}{{{'9' * digits}}}\n"
            f"{items}\n"
            r"\end{thebibliography}"
        )


def _render_abstract(doc: ManuscriptDoc) -> str:
    if not doc.abstract:
        return ""
    body = markdown_to_latex(doc.abstract)
    return f"\\begin{{abstract}}\n{body}\n\\end{{abstract}}"


def _render_keywords(keywords: tuple[str, ...]) -> str:
    text = ", ".join(latex_escape(k) for k in keywords)
    return f"\\noindent\\textbf{{Keywords:}} {text}"


def _render_section(section: Section) -> str:
    body = markdown_to_latex(section.body_md)
    return f"\\section{{{latex_escape(section.title)}}}\n{body}"
