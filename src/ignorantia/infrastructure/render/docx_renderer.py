"""``DocxRenderer`` — concrete :class:`RendererPort` for ``.docx`` output.

Behind the optional ``[docx]`` extra (``pip install ignorantia[docx]``)
because ``python-docx`` is a heavyweight dependency that not every
deployment needs. Importing this module is always safe; the
``python-docx`` import only fires when :class:`DocxRenderer` is
instantiated, and missing-extra installations get a precise
``ImportError`` pointing at the extra to install.

The renderer mirrors :class:`HtmlRenderer` and :class:`LatexRenderer`:
it accepts a :class:`CitationFormatterPort` Strategy, walks the
:class:`ManuscriptDoc`, and emits the artefact as ``bytes`` so the
application layer can persist or stream it without further
format-specific knowledge.

Section bodies are interpreted as a small Markdown subset (paragraphs
separated by blank lines). Inline ``**...**`` and ``*...*`` markers
are stripped — Word's run/format model is heavier than our other
backends, and the citation formatters never emit emphasis inside a
single reference, so plain-text output keeps the renderer focused on
structure.
"""

from __future__ import annotations

import io
import re
from typing import TYPE_CHECKING, Any

from ignorantia.domain.render.entities import (
    ManuscriptDoc,
    Reference,
    Section,
)
from ignorantia.domain.render.ports.citation_formatter_port import (
    CitationFormatterPort,
)
from ignorantia.domain.render.ports.renderer_port import RendererPort
from ignorantia.domain.render.value_objects import OutputFormat

if TYPE_CHECKING:
    from docx.document import Document as _DocxDocument


def _load_docx_module() -> Any:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise ImportError(
            "DocxRenderer requires the optional 'docx' extra. "
            "Install it with: pip install 'ignorantia[docx]'"
        ) from exc
    return docx


class DocxRenderer(RendererPort):
    """Render :class:`ManuscriptDoc` as an Office Open XML ``.docx``."""

    def __init__(self, *, formatter: CitationFormatterPort) -> None:
        """Wire the renderer to a citation formatter (Strategy).

        The ``python-docx`` import is resolved here so a deployment
        without the optional extra fails loudly at construction rather
        than at module import time.
        """
        self._docx = _load_docx_module()
        self._formatter = formatter

    @property
    def output_format(self) -> OutputFormat:
        """Return :class:`OutputFormat.DOCX`."""
        return OutputFormat.DOCX

    def render(self, doc: ManuscriptDoc) -> bytes:
        """Render ``doc`` and return the ``.docx`` artefact as bytes."""
        document: _DocxDocument = self._docx.Document()
        document.add_heading(doc.title, level=0)

        if doc.abstract:
            document.add_heading("Abstract", level=1)
            for paragraph in _split_paragraphs(doc.abstract):
                document.add_paragraph(_strip_emphasis(paragraph))

        if doc.keywords:
            document.add_paragraph("Keywords: " + ", ".join(doc.keywords))

        for section in doc.sections:
            _render_section(document, section)

        if doc.references:
            self._render_references(document, doc.references)

        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def _render_references(
        self,
        document: _DocxDocument,
        references: tuple[Reference, ...],
    ) -> None:
        document.add_heading("References", level=1)
        for ref in references:
            text = _strip_emphasis(self._formatter.format_reference(ref))
            document.add_paragraph(text)


def _render_section(document: _DocxDocument, section: Section) -> None:
    document.add_heading(section.title, level=1)
    for paragraph in _split_paragraphs(section.body_md):
        document.add_paragraph(_strip_emphasis(paragraph))


def _split_paragraphs(text: str) -> list[str]:
    if not text:
        return []
    return [p.strip() for p in text.split("\n\n") if p.strip()]


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")


def _strip_emphasis(text: str) -> str:
    """Drop Markdown bold/italic markers, keeping the inner text."""
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    return text
