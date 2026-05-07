"""Unit tests for :class:`HtmlRenderer`.

The renderer is intentionally minimal — no themes, no JavaScript, no
multi-tab layout (v2's render_v2.py was four-tab; v3 starts fresh
with a clean academic article skeleton). The contract pins the
structural elements every downstream consumer (browser preview,
deposit packagers) can rely on.
"""

from __future__ import annotations

import re

import pytest

from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.value_objects import CitationStyle, OutputFormat
from ignorantia.infrastructure.render.html_renderer import HtmlRenderer


class _StubFormatter(CitationFormatterPort):
    """Deterministic formatter so HTML-shape tests don't depend on a real style."""

    @property
    def style(self) -> CitationStyle:
        return CitationStyle.ABNT

    def format_reference(self, ref: Reference) -> str:
        return f"REF[{ref.title}]"

    def format_inline_citation(
        self,
        ref: Reference,
        *,
        page: str | None = None,
        index: int | None = None,
    ) -> str:
        del page, index
        return f"CITE[{ref.title}]"


@pytest.fixture
def renderer() -> HtmlRenderer:
    return HtmlRenderer(formatter=_StubFormatter())


def _doc(**overrides: object) -> ManuscriptDoc:
    base = {
        "title": "My SLR",
        "abstract": "Abstract text.",
        "sections": (Section(id="intro", title="Introduction", body_md="Hello."),),
        "references": (Reference(type="article", title="Ref A", authors=("X",)),),
    }
    base.update(overrides)
    return ManuscriptDoc(**base)  # type: ignore[arg-type]


class TestOutputFormat:
    def test_output_format_is_html(self, renderer: HtmlRenderer) -> None:
        assert renderer.output_format is OutputFormat.HTML


class TestSkeleton:
    def test_render_returns_bytes(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc())
        assert isinstance(out, bytes)

    def test_starts_with_doctype(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert out.lstrip().startswith("<!DOCTYPE html>")

    def test_html_lang_matches_doc_language(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(language="pt-BR")).decode("utf-8")
        assert '<html lang="pt-BR">' in out

    def test_meta_charset_utf8(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert '<meta charset="utf-8">' in out

    def test_title_in_head(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(title="Hello")).decode("utf-8")
        assert "<title>Hello</title>" in out


class TestBody:
    def test_h1_carries_doc_title(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(title="My SLR")).decode("utf-8")
        assert "<h1>My SLR</h1>" in out

    def test_abstract_section_present(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(abstract="Hello.")).decode("utf-8")
        assert '<section class="abstract">' in out
        assert "<p>Hello.</p>" in out

    def test_section_renders_with_id_and_h2(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(
            _doc(sections=(Section(id="intro", title="Introduction", body_md="Hi."),))
        ).decode("utf-8")
        assert '<section id="intro">' in out
        assert "<h2>Introduction</h2>" in out
        assert "<p>Hi.</p>" in out

    def test_keywords_block_when_present(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(keywords=("review", "prisma"))).decode("utf-8")
        assert '<p class="keywords">' in out
        assert "review" in out
        assert "prisma" in out

    def test_keywords_block_omitted_when_empty(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(keywords=())).decode("utf-8")
        assert "keywords" not in out


class TestReferences:
    def test_references_section_present(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert '<section class="references">' in out
        assert "<h2>References</h2>" in out

    def test_each_reference_emitted_via_formatter(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(
            _doc(
                references=(
                    Reference(type="article", title="A", authors=("X",)),
                    Reference(type="article", title="B", authors=("Y",)),
                )
            )
        ).decode("utf-8")
        assert "REF[A]" in out
        assert "REF[B]" in out

    def test_references_section_omitted_when_empty(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(references=())).decode("utf-8")
        assert '<section class="references">' not in out


class TestEscaping:
    def test_special_chars_in_title_escaped(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(title="A & B <c>")).decode("utf-8")
        assert "<title>A &amp; B &lt;c&gt;</title>" in out
        assert "<h1>A &amp; B &lt;c&gt;</h1>" in out

    def test_section_body_html_unsafe_content_escaped(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(
            _doc(sections=(Section(id="x", title="X", body_md="<script>alert(1)</script>"),))
        ).decode("utf-8")
        assert "<script>" not in out
        assert "&lt;script&gt;" in out


class TestMarkdownConversion:
    def test_paragraphs_split_on_blank_line(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(
            _doc(sections=(Section(id="x", title="X", body_md="Para 1.\n\nPara 2."),))
        ).decode("utf-8")
        assert "<p>Para 1.</p>" in out
        assert "<p>Para 2.</p>" in out

    def test_bold_markers_become_strong(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(
            _doc(sections=(Section(id="x", title="X", body_md="A **bold** word."),))
        ).decode("utf-8")
        assert "<strong>bold</strong>" in out

    def test_italic_markers_become_em(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(
            _doc(sections=(Section(id="x", title="X", body_md="A *italic* word."),))
        ).decode("utf-8")
        assert "<em>italic</em>" in out

    def test_well_formed_no_unclosed_tags(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        # Every opening tag has a closing counterpart for the structural ones
        for tag in ("html", "head", "body", "h1"):
            assert out.count(f"<{tag}") == out.count(f"</{tag}>")
        assert out.count("<section") == out.count("</section>")

    def test_output_is_valid_utf8(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc(title="Análise sistemática"))
        decoded = out.decode("utf-8")
        assert "Análise sistemática" in decoded


class TestStructuralOrdering:
    def test_h1_appears_before_abstract(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        h1_pos = out.find("<h1>")
        abstract_pos = out.find('<section class="abstract">')
        assert h1_pos < abstract_pos

    def test_abstract_appears_before_sections(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        abstract_pos = out.find('<section class="abstract">')
        section_pos = out.find('<section id="intro">')
        assert abstract_pos < section_pos

    def test_sections_appear_before_references(self, renderer: HtmlRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        section_pos = out.find('<section id="intro">')
        ref_pos = out.find('<section class="references">')
        assert section_pos < ref_pos


class TestEmptyDocCorners:
    def test_doc_with_only_required_fields(self, renderer: HtmlRenderer) -> None:
        doc = ManuscriptDoc(title="Minimal", abstract="", sections=(), references=())
        out = renderer.render(doc).decode("utf-8")
        assert "<h1>Minimal</h1>" in out
        assert "</html>" in out
        # No reference section, no keywords, no body sections, but valid HTML
        assert re.search(r"</body>\s*</html>", out)
