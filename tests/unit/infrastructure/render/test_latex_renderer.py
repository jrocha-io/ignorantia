"""Unit tests for :class:`LatexRenderer`.

The renderer produces a self-contained ``article``-class LaTeX
document with UTF-8 input, ``hyperref`` for inline URLs and a
``thebibliography`` block driven by an injected
:class:`CitationFormatterPort`.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import ManuscriptDoc, Reference, Section
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.value_objects import CitationStyle, OutputFormat
from ignorantia.infrastructure.render.latex_renderer import LatexRenderer


class _StubFormatter(CitationFormatterPort):
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
def renderer() -> LatexRenderer:
    return LatexRenderer(formatter=_StubFormatter())


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
    def test_output_format_is_latex(self, renderer: LatexRenderer) -> None:
        assert renderer.output_format is OutputFormat.LATEX


class TestPreamble:
    def test_documentclass_article(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\documentclass{article}" in out

    def test_inputenc_utf8(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\usepackage[utf8]{inputenc}" in out

    def test_hyperref_loaded(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\usepackage{hyperref}" in out

    def test_title_and_maketitle(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc(title="My SLR")).decode("utf-8")
        assert r"\title{My SLR}" in out
        assert r"\maketitle" in out


class TestBody:
    def test_begin_and_end_document(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\begin{document}" in out
        assert r"\end{document}" in out

    def test_abstract_uses_abstract_environment(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc(abstract="Hello.")).decode("utf-8")
        assert r"\begin{abstract}" in out
        assert r"\end{abstract}" in out
        assert "Hello." in out

    def test_section_command(self, renderer: LatexRenderer) -> None:
        out = renderer.render(
            _doc(sections=(Section(id="intro", title="Introduction", body_md="Hi."),))
        ).decode("utf-8")
        assert r"\section{Introduction}" in out
        assert "Hi." in out

    def test_keywords_block_when_present(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc(keywords=("review", "prisma"))).decode("utf-8")
        assert "review" in out
        assert "prisma" in out
        assert r"\textbf{Keywords:}" in out

    def test_keywords_block_omitted_when_empty(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc(keywords=())).decode("utf-8")
        assert "Keywords" not in out


class TestReferences:
    def test_thebibliography_block(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\begin{thebibliography}" in out
        assert r"\end{thebibliography}" in out

    def test_each_reference_emitted_via_formatter(self, renderer: LatexRenderer) -> None:
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
        # Each reference should be a \bibitem entry.
        assert out.count(r"\bibitem") == 2

    def test_thebibliography_omitted_when_empty(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc(references=())).decode("utf-8")
        assert "thebibliography" not in out


class TestEscaping:
    def test_special_chars_in_title_escaped(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc(title="A & B")).decode("utf-8")
        assert r"\title{A \& B}" in out

    def test_section_body_special_chars_escaped(self, renderer: LatexRenderer) -> None:
        out = renderer.render(
            _doc(sections=(Section(id="x", title="X", body_md="100% & cost $5"),))
        ).decode("utf-8")
        assert r"100\%" in out
        assert r"\&" in out
        assert r"\$5" in out


class TestStructuralOrdering:
    def test_preamble_before_begin_document(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert out.find(r"\documentclass") < out.find(r"\begin{document}")

    def test_maketitle_before_abstract(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert out.find(r"\maketitle") < out.find(r"\begin{abstract}")

    def test_abstract_before_first_section(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert out.find(r"\end{abstract}") < out.find(r"\section{Introduction}")

    def test_sections_before_thebibliography(self, renderer: LatexRenderer) -> None:
        out = renderer.render(_doc()).decode("utf-8")
        assert out.find(r"\section{Introduction}") < out.find(r"\begin{thebibliography}")


class TestExternalBibtexMode:
    """LatexRenderer with bib_file + bibliography_style configured."""

    def test_emits_bibliography_command(self) -> None:
        from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
            BibTexStyle,
        )

        renderer = LatexRenderer(
            formatter=_StubFormatter(),
            bib_file="bibliography",
            bibliography_style=BibTexStyle.PLAIN,
        )
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\bibliography{bibliography}" in out
        assert r"\bibliographystyle{plain}" in out

    def test_emits_nocite_star(self) -> None:
        from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
            BibTexStyle,
        )

        renderer = LatexRenderer(
            formatter=_StubFormatter(),
            bib_file="bibliography",
            bibliography_style=BibTexStyle.PLAIN,
        )
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\nocite{*}" in out

    def test_does_not_emit_inline_thebibliography(self) -> None:
        from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
            BibTexStyle,
        )

        renderer = LatexRenderer(
            formatter=_StubFormatter(),
            bib_file="bibliography",
            bibliography_style=BibTexStyle.PLAIN,
        )
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\begin{thebibliography}" not in out
        assert r"\bibitem" not in out

    def test_style_appears_in_directive(self) -> None:
        from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
            BibTexStyle,
        )

        renderer = LatexRenderer(
            formatter=_StubFormatter(),
            bib_file="bibliography",
            bibliography_style=BibTexStyle.IEEETRAN,
        )
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\bibliographystyle{IEEEtran}" in out

    def test_custom_bib_filename(self) -> None:
        from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
            BibTexStyle,
        )

        renderer = LatexRenderer(
            formatter=_StubFormatter(),
            bib_file="refs",
            bibliography_style=BibTexStyle.PLAIN,
        )
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\bibliography{refs}" in out
        assert r"\bibliography{bibliography}" not in out


class TestConstructorValidation:
    def test_bib_file_without_style_rejected(self) -> None:
        with pytest.raises(ValueError, match="together"):
            LatexRenderer(
                formatter=_StubFormatter(),
                bib_file="bibliography",
                bibliography_style=None,
            )

    def test_style_without_bib_file_rejected(self) -> None:
        from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
            BibTexStyle,
        )

        with pytest.raises(ValueError, match="together"):
            LatexRenderer(
                formatter=_StubFormatter(),
                bib_file=None,
                bibliography_style=BibTexStyle.PLAIN,
            )

    def test_neither_keeps_legacy_inline_mode(self) -> None:
        # Default constructor — both None — uses the legacy inline
        # \thebibliography path.
        renderer = LatexRenderer(formatter=_StubFormatter())
        out = renderer.render(_doc()).decode("utf-8")
        assert r"\begin{thebibliography}" in out
        assert r"\bibliography{" not in out
