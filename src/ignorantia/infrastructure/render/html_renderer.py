"""``HtmlRenderer`` — concrete :class:`RendererPort` for HTML5 output.

The v2 ``render_v2.py`` was a 1042-LOC four-tab layout glued to the
v2 pipeline. v3 replaces it with a clean academic-article skeleton:
``<h1>`` title, ``<section class="abstract">``, body sections (each
its own ``<section>`` with stable ``id``), and a final
``<section class="references">`` driven by an injected
:class:`CitationFormatterPort`.

Section bodies are interpreted as a small Markdown subset
(paragraphs, bold ``**``, italic ``*``); raw HTML in a section body
is escaped so user-provided content cannot inject scripts.
"""

from __future__ import annotations

import html
import re

from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import OutputFormat


class HtmlRenderer(RendererPort):
    """Render :class:`ManuscriptDoc` as a self-contained HTML5 document."""

    def __init__(self, *, formatter: CitationFormatterPort) -> None:
        """Wire the renderer to a citation formatter (Strategy)."""
        self._formatter = formatter

    @property
    def output_format(self) -> OutputFormat:
        """Return :class:`OutputFormat.HTML`."""
        return OutputFormat.HTML

    def render(self, doc: ManuscriptDoc) -> bytes:
        """Render ``doc`` and return the HTML5 document as UTF-8 bytes."""
        title = html.escape(doc.title)
        parts: list[str] = [
            "<!DOCTYPE html>",
            f'<html lang="{html.escape(doc.language)}">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{title}</title>",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>",
            _render_abstract(doc),
        ]
        if doc.keywords:
            parts.append(_render_keywords(doc.keywords))
        for section in doc.sections:
            parts.append(_render_section(section))
        if doc.references:
            parts.append(self._render_references(doc.references))
        parts.append("</body>")
        parts.append("</html>")
        return "\n".join(p for p in parts if p).encode("utf-8")

    def _render_references(self, references: tuple[Reference, ...]) -> str:
        items = "\n".join(
            f"<li>{_md_inline_to_html(self._formatter.format_reference(r))}</li>"
            for r in references
        )
        return (
            f'<section class="references">\n<h2>References</h2>\n<ol>\n{items}\n</ol>\n</section>'
        )


def _render_abstract(doc: ManuscriptDoc) -> str:
    body = _md_to_html(doc.abstract) if doc.abstract else ""
    return f'<section class="abstract">\n<h2>Abstract</h2>\n{body}\n</section>'


def _render_keywords(keywords: tuple[str, ...]) -> str:
    escaped = ", ".join(html.escape(k) for k in keywords)
    return f'<p class="keywords">{escaped}</p>'


def _render_section(section: Section) -> str:
    body = _md_to_html(section.body_md)
    return (
        f'<section id="{html.escape(section.id)}">\n'
        f"<h2>{html.escape(section.title)}</h2>\n"
        f"{body}\n"
        "</section>"
    )


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")


def _md_to_html(text: str) -> str:
    """Convert a Markdown subset (paragraphs, bold, italic) to HTML."""
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{_md_inline_to_html(p)}</p>" for p in paragraphs)


def _md_inline_to_html(text: str) -> str:
    """Escape HTML and replace bold/italic Markdown markers."""
    escaped = html.escape(text)
    escaped = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _ITALIC_RE.sub(r"<em>\1</em>", escaped)
    return escaped
