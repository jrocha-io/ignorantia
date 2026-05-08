"""Unit tests for :class:`AbntCitationFormatter`.

Pinning the v2 ABNT output exactly is *not* the goal — v2 had legacy
quirks (trailing commas, occasional missing punctuation). These tests
encode the canonical NBR 6023:2018 / NBR 10520:2023 forms the v3
context will adhere to going forward.

Title and venue strings are emitted with Markdown ``**...**`` markers
so renderers can downstream-translate to italic-or-bold per format
(HTML ``<em>``, LaTeX ``\\emph{}``, etc.). This is consistent with v2
and avoids leaking format-specific tagging into the citation Strategy.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.value_objects import CitationStyle
from ignorantia.infrastructure.render.citation.abnt_formatter import (
    AbntCitationFormatter,
)


@pytest.fixture
def fmt() -> AbntCitationFormatter:
    return AbntCitationFormatter()


class TestStyle:
    def test_style_is_abnt(self, fmt: AbntCitationFormatter) -> None:
        assert fmt.style is CitationStyle.ABNT


class TestFormatReferenceArticle:
    def test_single_author_full_metadata(self, fmt: AbntCitationFormatter) -> None:
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
        assert "SILVA, J. P." in out
        assert "Quality of evidence in SLRs" in out
        assert "**Journal of Reviews**" in out
        assert "v. 10" in out
        assert "n. 2" in out
        assert "p. 100-110" in out
        assert "2024" in out
        assert "DOI: 10.1234/jr.2024.10" in out

    def test_two_authors(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A."),
            year=2024,
            venue="J",
        )
        assert "SILVA, J.; PEREIRA, A." in fmt.format_reference(ref)

    def test_three_authors(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M."),
            year=2024,
            venue="J",
        )
        out = fmt.format_reference(ref)
        assert "SILVA, J.; PEREIRA, A.; LIMA, M." in out
        assert "et al." not in out

    def test_four_authors_uses_et_al(self, fmt: AbntCitationFormatter) -> None:
        # NBR 6023:2018 §8.1.1.2 allows either listing all authors or
        # using ``et al.``; v3 follows the v2 convention of listing the
        # first three and appending ``et al.`` for 4+.
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M.", "Costa, B."),
            year=2024,
            venue="J",
        )
        out = fmt.format_reference(ref)
        assert "SILVA, J.; PEREIRA, A.; LIMA, M. et al." in out
        assert "COSTA" not in out

    def test_no_authors_uses_sa(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=(), year=2024, venue="J")
        assert "[s.a.]" in fmt.format_reference(ref)

    def test_url_without_doi_emits_disponivel_em(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.",),
            year=2024,
            venue="J",
            url="https://example.org/x",
            accessed="2026-05-01",
        )
        out = fmt.format_reference(ref)
        assert "Disponível em: https://example.org/x" in out
        assert "Acesso em: 2026-05-01" in out

    def test_doi_takes_precedence_over_url(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.",),
            year=2024,
            venue="J",
            doi="10.1/x",
            url="https://example.org/x",
        )
        out = fmt.format_reference(ref)
        assert "DOI: 10.1/x" in out
        assert "Disponível em" not in out


class TestFormatReferenceBook:
    def test_book_basic(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="book",
            title="Methodology of SLRs",
            authors=("Silva, J.",),
            year=2023,
            location="São Paulo",
            publisher="Editora Acadêmica",
        )
        out = fmt.format_reference(ref)
        assert "SILVA, J." in out
        assert "**Methodology of SLRs**" in out
        assert "São Paulo:" in out
        assert "Editora Acadêmica" in out
        assert "2023" in out


class TestFormatReferenceBookChapter:
    def test_book_chapter_with_editors(self, fmt: AbntCitationFormatter) -> None:
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
        assert "SILVA, J." in out
        assert "Quality Assessment" in out
        assert "In:" in out
        assert "PEREIRA, A. (org.)" in out
        assert "**Handbook of SLRs**" in out
        assert "Rio de Janeiro:" in out
        assert "p. 50-80" in out


class TestFormatReferenceThesisAndDissertation:
    def test_thesis_uses_doutorado_label(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="thesis",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            program="Engenharia de Software",
            institution="Universidade X",
            location="São Paulo",
        )
        out = fmt.format_reference(ref)
        assert "**A study**" in out
        assert "Tese (Doutorado em Engenharia de Software)" in out
        assert "Universidade X" in out
        assert "2022" in out

    def test_dissertation_uses_mestrado_label(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="dissertation",
            title="A study",
            authors=("Silva, J.",),
            year=2022,
            program="Computação",
            institution="Universidade Y",
            location="Recife",
        )
        out = fmt.format_reference(ref)
        assert "Dissertação (Mestrado em Computação)" in out


class TestFormatReferenceConference:
    def test_conference_paper(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="conference",
            title="A paper",
            authors=("Silva, J.",),
            venue="CONGRESSO BRASILEIRO DE SOFTWARE",
            year=2023,
            location="Florianópolis",
            publisher="SBC",
            pages="10-20",
        )
        out = fmt.format_reference(ref)
        assert "In:" in out
        assert "**CONGRESSO BRASILEIRO DE SOFTWARE**" in out
        assert "Florianópolis" in out
        assert "**Anais** [...]" in out
        assert "p. 10-20" in out


class TestFormatReferenceElectronicAndWebsite:
    def test_electronic_with_url(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="electronic",
            title="WHO report",
            authors=(),
            year=2024,
            url="https://who.int/report",
            accessed="2026-05-01",
        )
        out = fmt.format_reference(ref)
        assert "**WHO report**" in out
        assert "Disponível em: https://who.int/report" in out
        assert "Acesso em: 2026-05-01" in out

    def test_website(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="website",
            title="Project home",
            authors=("Silva, J.",),
            url="https://example.org",
        )
        out = fmt.format_reference(ref)
        assert "**Project home**" in out
        assert "Disponível em: https://example.org" in out


class TestFormatReferenceLegislationAndAv:
    def test_legislation(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="legislation",
            title="BRASIL. Lei nº 9.610/1998",
            authors=(),
            year=1998,
            venue="Diário Oficial da União",
        )
        out = fmt.format_reference(ref)
        assert "BRASIL. Lei nº 9.610/1998" in out
        assert "Diário Oficial da União" in out
        assert "1998" in out

    def test_av_resource(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="av_resource",
            title="Documentary X",
            authors=("Direção: Y",),
            year=2020,
            location="Rio de Janeiro",
            publisher="Studio Z",
        )
        out = fmt.format_reference(ref)
        assert "**Documentary X**" in out
        assert "Rio de Janeiro" in out
        assert "Studio Z" in out
        assert "2020" in out


class TestFormatInlineCitation:
    def test_single_author(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, João",), year=2024)
        assert fmt.format_inline_citation(ref) == "(SILVA, 2024)"

    def test_two_authors(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.", "Pereira, A."), year=2024)
        assert fmt.format_inline_citation(ref) == "(SILVA; PEREIRA, 2024)"

    def test_three_authors(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M."),
            year=2024,
        )
        assert fmt.format_inline_citation(ref) == "(SILVA; PEREIRA; LIMA, 2024)"

    def test_four_authors_uses_et_al(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(
            type="article",
            title="t",
            authors=("Silva, J.", "Pereira, A.", "Lima, M.", "Costa, B."),
            year=2024,
        )
        assert fmt.format_inline_citation(ref) == "(SILVA et al., 2024)"

    def test_no_authors_uses_sa(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=(), year=2024)
        assert fmt.format_inline_citation(ref) == "([s.a.], 2024)"

    def test_no_year_uses_sd(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",))
        assert fmt.format_inline_citation(ref) == "(SILVA, [s.d.])"

    def test_with_page(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("Silva, J.",), year=2024)
        assert fmt.format_inline_citation(ref, page="42") == "(SILVA, 2024, p. 42)"

    def test_handles_first_last_name_format(self, fmt: AbntCitationFormatter) -> None:
        ref = Reference(type="article", title="t", authors=("João Silva",), year=2024)
        assert fmt.format_inline_citation(ref) == "(SILVA, 2024)"
