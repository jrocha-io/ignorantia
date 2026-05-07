"""Unit tests for :class:`VancouverCitationFormatter` (ICMJE style).

Vancouver is the numeric style adopted by most biomedical journals
(ICMJE Recommendations, NLM Citing Medicine). Authors render as
surname + initials with no comma or period (``Silva JP``); titles
carry no emphasis; references end with a period after the year and
locator block.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.value_objects import CitationStyle
from ignorantia.infrastructure.render.citation.vancouver_formatter import (
    VancouverCitationFormatter,
)


@pytest.fixture
def fmt() -> VancouverCitationFormatter:
    return VancouverCitationFormatter()


class TestStyle:
    def test_style_is_vancouver(self, fmt: VancouverCitationFormatter) -> None:
        assert fmt.style is CitationStyle.VANCOUVER


class TestFormatReferenceArticle:
    def test_single_author_full(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="Quality of evidence in SLRs",
            authors=("Silva, João Paulo",),
            year=2024,
            venue="J Reviews",
            volume="10",
            issue="2",
            pages="100-10",
            doi="10.1234/jr.2024.10",
        )
        out = fmt.format_reference(ref)
        assert "Silva JP" in out
        assert "Quality of evidence in SLRs." in out
        assert "J Reviews." in out
        assert "2024;10(2):100-10" in out
        assert "doi: 10.1234/jr.2024.10" in out

    def test_three_authors_listed_with_commas(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M."),
            year=2024,
            venue="J",
        )
        out = fmt.format_reference(ref)
        assert "Silva J, Pereira A, Lima M." in out

    def test_seven_authors_uses_et_al(self, fmt: VancouverCitationFormatter) -> None:
        names = tuple(f"Author{i}, X." for i in range(1, 8))
        ref = Reference(type="article", title="t", authors=names, year=2024, venue="J")
        out = fmt.format_reference(ref)
        assert "Author1 X, Author2 X, Author3 X, Author4 X, Author5 X, Author6 X, et al." in out
        assert "Author7" not in out

    def test_six_authors_listed(self, fmt: VancouverCitationFormatter) -> None:
        names = tuple(f"Author{i}, X." for i in range(1, 7))
        ref = Reference(type="article", title="t", authors=names, year=2024, venue="J")
        out = fmt.format_reference(ref)
        assert "et al." not in out
        assert "Author6 X" in out

    def test_no_authors_uses_anonymous(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=(), year=2024, venue="J")
        out = fmt.format_reference(ref)
        assert "[Anonymous]" in out


class TestFormatReferenceBookAndChapter:
    def test_book(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(
            type="book",
            title="Methodology of SLRs",
            authors=("Silva, J.",),
            year=2023,
            location="São Paulo",
            publisher="Editora Acadêmica",
        )
        out = fmt.format_reference(ref)
        assert "Silva J." in out
        assert "Methodology of SLRs." in out
        assert "São Paulo: Editora Acadêmica; 2023" in out

    def test_book_chapter_with_editors(self, fmt: VancouverCitationFormatter) -> None:
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
        assert "Silva J." in out
        assert "Quality Assessment." in out
        assert "In: Pereira A, editor." in out
        assert "Handbook of SLRs." in out
        assert "Rio de Janeiro: Editora X; 2023" in out
        assert "p. 50-80" in out


class TestFormatReferenceThesisAndConference:
    def test_thesis(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(
            type="thesis",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            institution="Universidade X",
            location="São Paulo",
        )
        out = fmt.format_reference(ref)
        assert "Silva J." in out
        assert "A study [dissertation]." in out
        assert "São Paulo: Universidade X; 2022" in out

    def test_dissertation(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(
            type="dissertation",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            institution="Universidade Y",
        )
        out = fmt.format_reference(ref)
        assert "[master's thesis]" in out

    def test_conference(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(
            type="conference",
            title="A paper",
            authors=("Silva, J.",),
            venue="Brazilian Software Conf",
            year=2023,
            location="Florianópolis",
            pages="10-20",
        )
        out = fmt.format_reference(ref)
        assert "A paper." in out
        assert "In: Brazilian Software Conf;" in out
        assert "Florianópolis" in out
        assert "p. 10-20" in out


class TestFormatReferenceElectronic:
    def test_electronic_with_url(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(
            type="electronic",
            title="WHO report",
            authors=(),
            year=2024,
            url="https://who.int/report",
            accessed="2026-05-01",
        )
        out = fmt.format_reference(ref)
        assert "WHO report" in out
        assert "[Internet]" in out
        assert "Available from: https://who.int/report" in out
        assert "[cited 2026-05-01]" in out


class TestFormatInlineCitation:
    def test_index_returns_bracketed(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",), year=2024)
        assert fmt.format_inline_citation(ref, index=1) == "(1)"

    def test_missing_index_uses_placeholder(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        assert fmt.format_inline_citation(ref) == "(?)"

    def test_page_kw_appends(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        assert fmt.format_inline_citation(ref, index=3, page="42") == "(3, p. 42)"

    def test_zero_or_negative_index_rejected(self, fmt: VancouverCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        with pytest.raises(ValueError):
            fmt.format_inline_citation(ref, index=0)
