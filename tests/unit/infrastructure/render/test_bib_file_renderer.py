"""Unit tests for :class:`BibFileRenderer` + ``generate_citation_keys``."""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import ManuscriptDoc, Reference
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import BibTexStyle
from ignorantia.infrastructure.render.bib_file_renderer import (
    BibFileRenderer,
    generate_citation_keys,
)
from ignorantia.infrastructure.render.citation.bibtex_factory import (
    bibtex_formatter_for,
)


def _doc(*refs: Reference) -> ManuscriptDoc:
    return ManuscriptDoc(
        title="Test Manuscript",
        abstract="x",
        sections=(),
        references=refs,
    )


def _ref(
    title: str,
    *,
    authors: tuple[str, ...] = (),
    year: int | None = None,
    type: str = "article",
) -> Reference:
    return Reference(
        type=type,
        title=title,
        authors=authors,
        year=year,
        venue="J",
    )


class TestKeyGeneration:
    def test_simple_key_recipe(self) -> None:
        ref = _ref("Quality of evidence", authors=("Silva, J. P.",), year=2024)
        keys = generate_citation_keys((ref,))
        assert keys == ("silva2024quality",)

    def test_collision_appends_suffix(self) -> None:
        a = _ref("Quality of evidence", authors=("Silva, J.",), year=2024)
        b = _ref("Quality of evidence", authors=("Silva, J.",), year=2024)
        c = _ref("Quality of evidence", authors=("Silva, J.",), year=2024)
        keys = generate_citation_keys((a, b, c))
        assert keys == ("silva2024quality", "silva2024qualitya", "silva2024qualityb")

    def test_no_authors_uses_anon(self) -> None:
        ref = _ref("Anonymous statute", year=2024)
        keys = generate_citation_keys((ref,))
        assert keys == ("anon2024anonymous",)

    def test_no_year_uses_nd(self) -> None:
        ref = _ref("Year-less", authors=("Mendes, F.",))
        keys = generate_citation_keys((ref,))
        assert keys == ("mendesndyear",)  # "year-less" → first significant word "year"

    def test_unicode_surnames_normalised(self) -> None:
        ref = _ref("Análise sistemática", authors=("Açúcar, M.",), year=2024)
        keys = generate_citation_keys((ref,))
        # Diacritics stripped; ASCII-lower.
        assert keys == ("acucar2024analise",)

    def test_stopwords_skipped(self) -> None:
        # English: "The Method of X" → first significant word is "method"
        ref = _ref("The Method of X", authors=("Ng, A.",), year=2025)
        keys = generate_citation_keys((ref,))
        assert keys == ("ng2025method",)

    def test_portuguese_stopwords_skipped(self) -> None:
        # "A análise da educação" → "A" is stopword; "análise" first
        # significant word; diacritics strip → "analise".
        ref = _ref("A análise da educação", authors=("Costa, P.",), year=2026)
        keys = generate_citation_keys((ref,))
        assert keys == ("costa2026analise",)


class TestBibFileRenderer:
    def test_empty_references_returns_only_header(self) -> None:
        formatter = bibtex_formatter_for(BibTexStyle.PLAIN)
        renderer = BibFileRenderer(formatter=formatter)
        body = renderer.render(_doc()).decode("utf-8")
        assert "% bibliography.bib" in body
        assert "% style: plain" in body
        assert "@" not in body  # no entries

    def test_single_entry_renders(self) -> None:
        formatter = bibtex_formatter_for(BibTexStyle.PLAIN)
        renderer = BibFileRenderer(formatter=formatter)
        ref = _ref("Quality of evidence", authors=("Silva, J. P.",), year=2024)
        body = renderer.render(_doc(ref)).decode("utf-8")
        assert "@article{silva2024quality," in body
        assert "Silva, J. P." in body

    def test_multiple_entries_separated_by_blank_line(self) -> None:
        formatter = bibtex_formatter_for(BibTexStyle.PLAIN)
        renderer = BibFileRenderer(formatter=formatter)
        a = _ref("First", authors=("Alpha, A.",), year=2024)
        b = _ref("Second", authors=("Beta, B.",), year=2024)
        body = renderer.render(_doc(a, b)).decode("utf-8")
        # Each entry block separated by blank line
        assert body.count("@article{") == 2

    def test_style_property_forwards(self) -> None:
        formatter = bibtex_formatter_for(BibTexStyle.IEEETRAN)
        renderer = BibFileRenderer(formatter=formatter)
        assert renderer.style is BibTexStyle.IEEETRAN

    def test_byte_stable_across_runs(self) -> None:
        formatter = bibtex_formatter_for(BibTexStyle.PLAIN)
        renderer = BibFileRenderer(formatter=formatter)
        refs = (
            _ref("First", authors=("Alpha, A.",), year=2024),
            _ref("Second", authors=("Beta, B.",), year=2024),
        )
        a = renderer.render(_doc(*refs))
        b = renderer.render(_doc(*refs))
        assert a == b


class TestStylePropagation:
    @pytest.mark.parametrize("style", list(BibTexStyle))
    def test_header_carries_style(self, style: BibTexStyle) -> None:
        renderer = BibFileRenderer(formatter=bibtex_formatter_for(style))
        body = renderer.render(_doc()).decode("utf-8")
        assert f"% style: {style.value}" in body
