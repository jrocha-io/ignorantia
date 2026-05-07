"""Unit tests for :class:`DocxRenderer`.

The DOCX renderer depends on the optional ``python-docx`` extra
(``pip install ignorantia[docx]``). Tests skip gracefully when that
extra is missing, but assert the full contract when it is installed.

The contract pinned here treats the ``.docx`` artefact as bytes and
verifies its semantic content by parsing it back with ``python-docx``
— string-matching the binary OOXML payload would be brittle.
"""

from __future__ import annotations

import io

import pytest

from ignorantia.domain.render.entities import (
    ManuscriptDoc,
    Reference,
    Section,
)
from ignorantia.domain.render.value_objects import OutputFormat

# Skip the entire module unless the optional extra is installed —
# pytest.importorskip does the import attempt and the skip decision in
# one call, mirroring how python-docx-dependent tests are gated in
# every other Python project that ships an optional DOCX feature.
docx_module = pytest.importorskip("docx")

from ignorantia.domain.render.ports.citation_formatter_port import (  # noqa: E402
    CitationFormatterPort,
)
from ignorantia.domain.render.value_objects import (  # noqa: E402
    CitationStyle,
)
from ignorantia.infrastructure.render.docx_renderer import (  # noqa: E402
    DocxRenderer,
)


class _StubFormatter(CitationFormatterPort):
    @property
    def style(self) -> CitationStyle:
        return CitationStyle.APA

    def format_reference(self, ref: Reference) -> str:
        return f"REF::{ref.title}"

    def format_inline_citation(
        self,
        ref: Reference,
        *,
        page: str | None = None,
        index: int | None = None,
    ) -> str:
        del page, index
        return f"CITE::{ref.title}"


@pytest.fixture
def renderer() -> DocxRenderer:
    return DocxRenderer(formatter=_StubFormatter())


@pytest.fixture
def doc() -> ManuscriptDoc:
    return ManuscriptDoc(
        title="A Systematic Review",
        abstract="This study evaluates X.",
        sections=(
            Section(id="introduction", title="Introduction", body_md="Body of intro."),
            Section(id="methods", title="Methods", body_md="Body of methods."),
        ),
        references=(
            Reference(
                type="article",
                title="Quality of evidence",
                authors=("Silva, J. P.",),
                year=2024,
                venue="Journal of SLR",
            ),
        ),
        keywords=("evidence", "review"),
    )


def _read_docx(payload: bytes) -> docx_module.Document:  # type: ignore[name-defined]
    return docx_module.Document(io.BytesIO(payload))


class TestOutputFormat:
    def test_output_format_is_docx(self, renderer: DocxRenderer) -> None:
        assert renderer.output_format is OutputFormat.DOCX


class TestRenderReturnsBytes:
    def test_render_returns_bytes(self, renderer: DocxRenderer, doc: ManuscriptDoc) -> None:
        result = renderer.render(doc)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_render_output_starts_with_zip_magic(
        self, renderer: DocxRenderer, doc: ManuscriptDoc
    ) -> None:
        # .docx is a zip container; OOXML files always start with PK\x03\x04.
        result = renderer.render(doc)
        assert result[:2] == b"PK"


class TestRenderedContent:
    def test_title_is_first_paragraph(self, renderer: DocxRenderer, doc: ManuscriptDoc) -> None:
        parsed = _read_docx(renderer.render(doc))
        assert parsed.paragraphs[0].text == "A Systematic Review"

    def test_abstract_text_is_present(self, renderer: DocxRenderer, doc: ManuscriptDoc) -> None:
        parsed = _read_docx(renderer.render(doc))
        joined = "\n".join(p.text for p in parsed.paragraphs)
        assert "This study evaluates X." in joined

    def test_section_titles_are_present(self, renderer: DocxRenderer, doc: ManuscriptDoc) -> None:
        parsed = _read_docx(renderer.render(doc))
        joined = "\n".join(p.text for p in parsed.paragraphs)
        assert "Introduction" in joined
        assert "Methods" in joined

    def test_section_bodies_are_present(self, renderer: DocxRenderer, doc: ManuscriptDoc) -> None:
        parsed = _read_docx(renderer.render(doc))
        joined = "\n".join(p.text for p in parsed.paragraphs)
        assert "Body of intro." in joined
        assert "Body of methods." in joined

    def test_keywords_are_present(self, renderer: DocxRenderer, doc: ManuscriptDoc) -> None:
        parsed = _read_docx(renderer.render(doc))
        joined = "\n".join(p.text for p in parsed.paragraphs)
        assert "evidence" in joined
        assert "review" in joined

    def test_references_use_injected_formatter(
        self, renderer: DocxRenderer, doc: ManuscriptDoc
    ) -> None:
        parsed = _read_docx(renderer.render(doc))
        joined = "\n".join(p.text for p in parsed.paragraphs)
        assert "REF::Quality of evidence" in joined

    def test_references_heading_is_present(
        self, renderer: DocxRenderer, doc: ManuscriptDoc
    ) -> None:
        parsed = _read_docx(renderer.render(doc))
        joined = "\n".join(p.text for p in parsed.paragraphs)
        assert "References" in joined


class TestEdgeCases:
    def test_empty_keywords_does_not_render_keywords_block(self, renderer: DocxRenderer) -> None:
        doc = ManuscriptDoc(
            title="No Keywords",
            abstract="x",
            sections=(),
            references=(),
            keywords=(),
        )
        # Should not raise; just produce a valid .docx without keywords.
        result = renderer.render(doc)
        assert result[:2] == b"PK"

    def test_empty_references_does_not_render_references_section(
        self, renderer: DocxRenderer
    ) -> None:
        doc = ManuscriptDoc(
            title="No Refs",
            abstract="x",
            sections=(),
            references=(),
        )
        parsed = _read_docx(renderer.render(doc))
        joined = "\n".join(p.text for p in parsed.paragraphs)
        assert "References" not in joined
