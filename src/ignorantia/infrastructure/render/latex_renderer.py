r"""``LatexRenderer`` — concrete :class:`RendererPort` for LaTeX output.

Produces a self-contained ``article``-class LaTeX document with
``inputenc`` (UTF-8) and ``hyperref`` so the generated source can be
compiled by any modern engine (pdfLaTeX, xelatex, lualatex). Body
sections are passed through :func:`markdown_to_latex` to translate
the small Markdown vocabulary into ``\textbf{...}`` / ``\textit{...}``
commands. References are emitted via an injected
:class:`CitationFormatterPort` and wrapped in a
``thebibliography`` environment so a single ``\cite{...}`` call from
downstream callers resolves correctly.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import OutputFormat
from ignorantia.infrastructure.render.markdown_to_latex import (
    latex_escape,
    markdown_to_latex,
)


class LatexRenderer(RendererPort):
    """Render :class:`ManuscriptDoc` as a standalone LaTeX article."""

    def __init__(self, *, formatter: CitationFormatterPort) -> None:
        """Wire the renderer to a citation formatter (Strategy)."""
        self._formatter = formatter

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
