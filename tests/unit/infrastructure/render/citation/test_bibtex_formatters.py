"""Unit tests for the four BibTeX entry formatters + the factory."""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
    BibTexEntryFormatterPort,
    BibTexStyle,
)
from ignorantia.infrastructure.render.citation.bibtex_abntex2cite import (
    BibTexAbntex2CiteFormatter,
)
from ignorantia.infrastructure.render.citation.bibtex_factory import (
    bibtex_formatter_for,
)
from ignorantia.infrastructure.render.citation.bibtex_ieeetran import (
    BibTexIEEEtranFormatter,
)
from ignorantia.infrastructure.render.citation.bibtex_plain import (
    BibTexPlainFormatter,
)
from ignorantia.infrastructure.render.citation.bibtex_unsrt import (
    BibTexUnsrtFormatter,
)


def _article() -> Reference:
    return Reference(
        type="article",
        title="Quality of evidence in SLRs",
        authors=("Silva, J. P.",),
        year=2024,
        venue="Journal of SLR",
        volume="10",
        issue="2",
        pages="100-110",
        doi="10.1234/jsl.2024.001",
    )


def _book_chapter() -> Reference:
    return Reference(
        type="book_chapter",
        title="Search Strategies",
        chapter_title="Search Strategies",
        authors=("Lima, Carlos",),
        book_editors=("Fernandes, Diana",),
        year=2022,
        publisher="University Press",
        location="Rio de Janeiro",
        pages="33-58",
    )


def _thesis() -> Reference:
    return Reference(
        type="thesis",
        title="A doctoral investigation",
        authors=("Souza, Eduardo",),
        year=2021,
        program="Programa de Pós-Graduação em Engenharia",
        institution="UFRJ",
        location="Rio de Janeiro",
    )


# ----------------------------------------------------------------------
# BibTexStyle enum
# ----------------------------------------------------------------------


class TestBibTexStyleEnum:
    def test_canonical_wire_values(self) -> None:
        assert BibTexStyle.PLAIN.value == "plain"
        assert BibTexStyle.UNSRT.value == "unsrt"
        assert BibTexStyle.ABNTEX2.value == "abntex2-num"
        assert BibTexStyle.IEEETRAN.value == "IEEEtran"

    def test_str_returns_wire_value(self) -> None:
        assert str(BibTexStyle.PLAIN) == "plain"

    def test_is_str_subtype(self) -> None:
        assert isinstance(BibTexStyle.PLAIN, str)


# ----------------------------------------------------------------------
# Plain
# ----------------------------------------------------------------------


class TestBibTexPlainFormatter:
    def test_style_is_plain(self) -> None:
        assert BibTexPlainFormatter().style is BibTexStyle.PLAIN

    def test_article_emits_journal_volume_pages(self) -> None:
        out = BibTexPlainFormatter().format_entry(_article(), key="silva2024quality")
        assert out.startswith("@article{silva2024quality,")
        assert out.endswith("}")
        assert "author = {Silva, J. P.}" in out
        assert "title = {Quality of evidence in SLRs}" in out
        assert "journal = {Journal of SLR}" in out
        assert "volume = {10}" in out
        assert "number = {2}" in out
        assert "pages = {100--110}" in out
        assert "year = {2024}" in out
        assert "doi = {10.1234/jsl.2024.001}" in out

    def test_book_chapter_emits_incollection(self) -> None:
        out = BibTexPlainFormatter().format_entry(_book_chapter(), key="lima2022")
        assert out.startswith("@incollection{lima2022,")
        assert "publisher = {University Press}" in out
        assert "editor = {Fernandes, Diana}" in out

    def test_thesis_emits_phdthesis_with_school(self) -> None:
        out = BibTexPlainFormatter().format_entry(_thesis(), key="souza2021")
        assert out.startswith("@phdthesis{souza2021,")
        assert "school = {UFRJ}" in out

    def test_special_chars_escaped(self) -> None:
        ref = Reference(
            type="article",
            title="Cost & Benefit: 50% off {testing}",
            authors=("Smith, J.",),
            year=2024,
            venue="J. of Things",
        )
        out = BibTexPlainFormatter().format_entry(ref, key="smith2024")
        assert r"\&" in out
        assert r"\%" in out
        assert r"\{" in out and r"\}" in out

    def test_pages_with_double_dash_passes_through(self) -> None:
        ref = Reference(
            type="article",
            title="x",
            authors=(),
            year=2024,
            venue="J",
            pages="100--110",
        )
        out = BibTexPlainFormatter().format_entry(ref, key="x")
        # No double-double-dash:
        assert "----" not in out
        assert "100--110" in out


# ----------------------------------------------------------------------
# Unsrt — same shape as plain
# ----------------------------------------------------------------------


class TestBibTexUnsrtFormatter:
    def test_style_is_unsrt(self) -> None:
        assert BibTexUnsrtFormatter().style is BibTexStyle.UNSRT

    def test_field_shape_matches_plain(self) -> None:
        unsrt = BibTexUnsrtFormatter().format_entry(_article(), key="x")
        plain = BibTexPlainFormatter().format_entry(_article(), key="x")
        assert unsrt == plain


# ----------------------------------------------------------------------
# abntex2-num
# ----------------------------------------------------------------------


class TestBibTexAbntex2CiteFormatter:
    def test_style_is_abntex2(self) -> None:
        assert BibTexAbntex2CiteFormatter().style is BibTexStyle.ABNTEX2

    def test_uppercase_surname(self) -> None:
        out = BibTexAbntex2CiteFormatter().format_entry(_article(), key="x")
        assert "author = {SILVA, J. P.}" in out

    def test_thesis_uses_phdthesis(self) -> None:
        out = BibTexAbntex2CiteFormatter().format_entry(_thesis(), key="x")
        assert out.startswith("@phdthesis{")

    def test_dissertation_uses_mastersthesis(self) -> None:
        ref = Reference(
            type="dissertation",
            title="t",
            authors=("Mendes, Fernanda",),
            year=2020,
            institution="USP",
        )
        out = BibTexAbntex2CiteFormatter().format_entry(ref, key="x")
        assert out.startswith("@mastersthesis{")

    def test_legislation_emits_howpublished(self) -> None:
        ref = Reference(
            type="legislation",
            title="Lei nº 12.345, de 1 de janeiro de 2024",
            authors=(),
            year=2024,
            venue="Diário Oficial da União",
        )
        out = BibTexAbntex2CiteFormatter().format_entry(ref, key="x")
        assert out.startswith("@misc{")
        assert "howpublished = {Di" in out  # "Diário ..."

    def test_book_chapter_uppercases_editors(self) -> None:
        out = BibTexAbntex2CiteFormatter().format_entry(_book_chapter(), key="x")
        assert "editor = {FERNANDES, Diana}" in out


# ----------------------------------------------------------------------
# IEEEtran
# ----------------------------------------------------------------------


class TestBibTexIEEEtranFormatter:
    def test_style_is_ieeetran(self) -> None:
        assert BibTexIEEEtranFormatter().style is BibTexStyle.IEEETRAN

    def test_author_in_first_last_order(self) -> None:
        out = BibTexIEEEtranFormatter().format_entry(_article(), key="x")
        # Original: "Silva, J. P." → IEEEtran wants "J. P. Silva"
        assert "author = {J. P. Silva}" in out
        # Should NOT contain the comma form:
        assert "{Silva, J. P.}" not in out

    def test_number_only_when_volume_missing(self) -> None:
        ref = Reference(
            type="article",
            title="x",
            authors=(),
            year=2024,
            venue="J",
            issue="2",  # no volume
        )
        out = BibTexIEEEtranFormatter().format_entry(ref, key="x")
        assert "number = {2}" in out

    def test_number_dropped_when_volume_present(self) -> None:
        out = BibTexIEEEtranFormatter().format_entry(_article(), key="x")
        # Article fixture has both volume=10 and issue=2; IEEEtran
        # prefers volume — number should be omitted.
        assert "volume = {10}" in out
        assert "number = {2}" not in out


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


class TestBibTexFactory:
    @pytest.mark.parametrize("style", list(BibTexStyle))
    def test_factory_returns_port_for_each_style(self, style: BibTexStyle) -> None:
        formatter = bibtex_formatter_for(style)
        assert isinstance(formatter, BibTexEntryFormatterPort)
        assert formatter.style is style

    def test_unknown_style_raises(self) -> None:
        from enum import Enum

        class Fake(str, Enum):
            X = "x"

        with pytest.raises(ValueError, match="unsupported"):
            bibtex_formatter_for(Fake.X)  # type: ignore[arg-type]

    def test_lazy_singleton(self) -> None:
        a = bibtex_formatter_for(BibTexStyle.PLAIN)
        b = bibtex_formatter_for(BibTexStyle.PLAIN)
        assert a is b
