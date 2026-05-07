"""Unit tests for :class:`IeeeCitationFormatter`.

IEEE is a numeric style: inline citations are bracketed numbers tied
to the manuscript reference list order. The renderer is responsible
for assigning each reference an ``index`` and passing it through to
:meth:`CitationFormatterPort.format_inline_citation`.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.value_objects import CitationStyle
from ignorantia.infrastructure.render.citation.ieee_formatter import (
    IeeeCitationFormatter,
)


@pytest.fixture
def fmt() -> IeeeCitationFormatter:
    return IeeeCitationFormatter()


class TestStyle:
    def test_style_is_ieee(self, fmt: IeeeCitationFormatter) -> None:
        assert fmt.style is CitationStyle.IEEE


class TestFormatReferenceArticle:
    def test_single_author_full(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="Quality of evidence in SLRs",
            authors=("Silva, João Paulo",),
            year=2024,
            venue="Journal of Reviews",
            volume="10",
            issue="2",
            pages="100-110",
            doi="10.1234/jr.2024.10",
        )
        out = fmt.format_reference(ref)
        assert "J. P. Silva" in out
        assert '"Quality of evidence in SLRs,"' in out
        assert "*Journal of Reviews*" in out
        assert "vol. 10" in out
        assert "no. 2" in out
        assert "pp. 100-110" in out
        assert "2024" in out
        assert "doi: 10.1234/jr.2024.10" in out

    def test_two_authors_uses_and(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A."),
            year=2024,
            venue="J",
        )
        assert "J. Silva and A. Pereira" in fmt.format_reference(ref)

    def test_three_authors_serial_comma_and(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M."),
            year=2024,
            venue="J",
        )
        assert "J. Silva, A. Pereira, and M. Lima" in fmt.format_reference(ref)

    def test_seven_authors_uses_et_al(self, fmt: IeeeCitationFormatter) -> None:
        names = tuple(f"Author{i}, X." for i in range(1, 8))
        ref = Reference(type="article", title="t", authors=names, year=2024, venue="J")
        out = fmt.format_reference(ref)
        assert "X. Author1 et al." in out
        assert "Author2" not in out

    def test_six_authors_listed(self, fmt: IeeeCitationFormatter) -> None:
        names = tuple(f"Author{i}, X." for i in range(1, 7))
        ref = Reference(type="article", title="t", authors=names, year=2024, venue="J")
        out = fmt.format_reference(ref)
        assert "et al." not in out
        assert "X. Author6" in out


class TestFormatReferenceBookAndChapter:
    def test_book(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="book",
            title="Methodology of SLRs",
            authors=("Silva, J.",),
            year=2023,
            location="São Paulo",
            publisher="Editora Acadêmica",
        )
        out = fmt.format_reference(ref)
        assert "J. Silva" in out
        assert "*Methodology of SLRs*" in out
        assert "São Paulo:" in out
        assert "Editora Acadêmica" in out
        assert "2023" in out

    def test_book_chapter_with_editors(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="book_chapter",
            title="Handbook of SLRs",
            chapter_title="Quality Assessment",
            authors=("Silva, J.",),
            book_editors=("Pereira, A.",),
            year=2023,
            location="Rio de Janeiro",
            publisher="Editora X",
            pages="50-80",
        )
        out = fmt.format_reference(ref)
        assert '"Quality Assessment,"' in out
        assert "in *Handbook of SLRs*" in out
        assert "A. Pereira, Ed." in out
        assert "Rio de Janeiro:" in out
        assert "pp. 50-80" in out


class TestFormatReferenceThesisAndConference:
    def test_thesis(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="thesis",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            institution="Universidade X",
            location="São Paulo",
        )
        out = fmt.format_reference(ref)
        assert '"A study,"' in out
        assert "Ph.D. dissertation" in out
        assert "Universidade X" in out
        assert "São Paulo" in out
        assert "2022" in out

    def test_dissertation(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="dissertation",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            institution="Universidade Y",
        )
        out = fmt.format_reference(ref)
        assert "M.S. thesis" in out

    def test_conference(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="conference",
            title="A paper",
            authors=("Silva, J.",),
            venue="Proc. Brazilian Software Conf.",
            year=2023,
            location="Florianópolis",
            pages="10-20",
        )
        out = fmt.format_reference(ref)
        assert '"A paper,"' in out
        assert "in *Proc. Brazilian Software Conf.*" in out
        assert "Florianópolis" in out
        assert "pp. 10-20" in out


class TestFormatReferenceElectronic:
    def test_electronic(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(
            type="electronic",
            title="WHO report",
            authors=(),
            year=2024,
            url="https://who.int/report",
            accessed="2026-05-01",
        )
        out = fmt.format_reference(ref)
        assert "*WHO report*" in out
        assert "https://who.int/report" in out
        assert "Accessed: 2026-05-01" in out


class TestFormatInlineCitation:
    def test_index_required_returns_bracketed_number(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",), year=2024)
        assert fmt.format_inline_citation(ref, index=1) == "[1]"

    def test_index_arbitrary(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        assert fmt.format_inline_citation(ref, index=42) == "[42]"

    def test_missing_index_uses_placeholder(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        assert fmt.format_inline_citation(ref) == "[?]"

    def test_page_keyword_appends_pp(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        assert fmt.format_inline_citation(ref, index=3, page="42") == "[3, p. 42]"

    def test_zero_or_negative_index_rejected(self, fmt: IeeeCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        with pytest.raises(ValueError):
            fmt.format_inline_citation(ref, index=0)
        with pytest.raises(ValueError):
            fmt.format_inline_citation(ref, index=-1)
