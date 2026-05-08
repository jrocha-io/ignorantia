"""Unit tests for :class:`ApaCitationFormatter` (APA 7th edition).

The pinned forms below match the APA Publication Manual, 7th edition
(2020). The test focus is on the *shape* of the output (presence of
required tokens) so cosmetic punctuation tweaks do not produce noisy
test failures, while structural regressions (wrong author count, wrong
year handling, missing italics) are caught.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.value_objects import CitationStyle
from ignorantia.infrastructure.render.citation.apa_formatter import (
    ApaCitationFormatter,
)


@pytest.fixture
def fmt() -> ApaCitationFormatter:
    return ApaCitationFormatter()


class TestStyle:
    def test_style_is_apa(self, fmt: ApaCitationFormatter) -> None:
        assert fmt.style is CitationStyle.APA


class TestFormatReferenceArticle:
    def test_single_author_full(self, fmt: ApaCitationFormatter) -> None:
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
        assert "Silva, J. P." in out
        assert "(2024)" in out
        assert "Quality of evidence in SLRs" in out
        assert "*Journal of Reviews*" in out
        assert "10(2)" in out
        assert "100-110" in out
        assert "https://doi.org/10.1234/jr.2024.10" in out

    def test_two_authors_uses_ampersand(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A."),
            year=2024,
            venue="J",
        )
        out = fmt.format_reference(ref)
        assert "Silva, J., & Pereira, A." in out

    def test_three_authors_uses_serial_comma_and_ampersand(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M."),
            year=2024,
            venue="J",
        )
        out = fmt.format_reference(ref)
        assert "Silva, J., Pereira, A., & Lima, M." in out

    def test_twenty_one_authors_truncate_with_ellipsis(self, fmt: ApaCitationFormatter) -> None:
        names = tuple(f"Author{i}, X." for i in range(1, 22))
        ref = Reference(type="article", title="t", authors=names, year=2024, venue="J")
        out = fmt.format_reference(ref)
        assert "Author19, X." in out
        assert ", ... Author21, X." in out
        assert "Author20" not in out

    def test_no_year_uses_n_d(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",), venue="J")
        out = fmt.format_reference(ref)
        assert "(n.d.)" in out

    def test_url_without_doi(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.",),
            year=2024,
            venue="J",
            url="https://example.org/x",
        )
        out = fmt.format_reference(ref)
        assert "https://example.org/x" in out


class TestFormatReferenceBookAndChapter:
    def test_book(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="book",
            title="Methodology of SLRs",
            authors=("Silva, J.",),
            year=2023,
            publisher="Editora Acadêmica",
        )
        out = fmt.format_reference(ref)
        assert "Silva, J." in out
        assert "(2023)" in out
        assert "*Methodology of SLRs*" in out
        assert "Editora Acadêmica" in out

    def test_book_chapter_with_editors(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="book_chapter",
            title="Handbook of SLRs",
            chapter_title="Quality Assessment",
            authors=("Silva, J.",),
            book_editors=("Pereira, A.",),
            year=2023,
            publisher="Editora X",
            pages="50-80",
        )
        out = fmt.format_reference(ref)
        assert "Silva, J." in out
        assert "Quality Assessment" in out
        assert "In " in out
        assert "Pereira, A. (Ed.)" in out
        assert "*Handbook of SLRs*" in out
        assert "(pp. 50-80)" in out
        assert "Editora X" in out


class TestFormatReferenceThesis:
    def test_thesis(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="thesis",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            institution="Universidade X",
        )
        out = fmt.format_reference(ref)
        assert "*A study*" in out
        assert "[Doctoral dissertation, Universidade X]" in out

    def test_dissertation(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="dissertation",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            institution="Universidade Y",
        )
        out = fmt.format_reference(ref)
        assert "[Master's thesis, Universidade Y]" in out


class TestFormatReferenceElectronic:
    def test_electronic_with_url(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="electronic",
            title="WHO report",
            authors=(),
            year=2024,
            url="https://who.int/report",
        )
        out = fmt.format_reference(ref)
        assert "*WHO report*" in out
        assert "https://who.int/report" in out


class TestFormatInlineCitation:
    def test_single_author(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, João",), year=2024)
        assert fmt.format_inline_citation(ref) == "(Silva, 2024)"

    def test_two_authors_uses_ampersand(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.", "Pereira, A."), year=2024)
        assert fmt.format_inline_citation(ref) == "(Silva & Pereira, 2024)"

    def test_three_authors_uses_et_al(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M."),
            year=2024,
        )
        assert fmt.format_inline_citation(ref) == "(Silva et al., 2024)"

    def test_no_authors_uses_anonymous(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=(), year=2024)
        assert fmt.format_inline_citation(ref) == "(Anonymous, 2024)"

    def test_no_year_uses_n_d(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        assert fmt.format_inline_citation(ref) == "(Silva, n.d.)"

    def test_with_page(self, fmt: ApaCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",), year=2024)
        assert fmt.format_inline_citation(ref, page="42") == "(Silva, 2024, p. 42)"
