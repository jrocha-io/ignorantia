"""Cross-style contract tests for :class:`CitationFormatterPort`.

The four formatters (ABNT, APA, IEEE, Vancouver) are merged via PRs
#46-#49. PR #53 adds the registry. This module pins the invariants
*every* formatter must satisfy regardless of style — so a future
fifth style cannot silently break the renderer pipeline.

Invariants pinned here:

* ``style`` matches the registry key used to resolve the formatter;
* ``format_reference`` returns a non-empty string for every reference
  type in the canonical vocabulary and never raises;
* ``format_inline_citation`` returns a non-empty string for every
  style — numeric styles get an ``index=`` kwarg, author-date styles
  ignore it;
* references with missing year / missing author still render
  *something* — formatters substitute documented placeholders rather
  than letting ``None`` leak into the output.

Style-specific output is *not* asserted here: each formatter has its
own dedicated test module pinning the exact strings.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.citation_formatter_port import (
    CitationFormatterPort,
)
from ignorantia.domain.render.value_objects import CitationStyle
from ignorantia.infrastructure.render.citation.factory import (
    citation_formatter_for,
)

_NUMERIC_STYLES: frozenset[CitationStyle] = frozenset({CitationStyle.IEEE, CitationStyle.VANCOUVER})

_REFERENCE_FIXTURES: dict[str, Reference] = {
    "article": Reference(
        type="article",
        title="Quality of evidence in SLRs",
        authors=("Silva, João Paulo",),
        year=2024,
        venue="Journal of SLR",
        volume="10",
        issue="2",
        pages="100-110",
        doi="10.1234/jsl.2024.001",
    ),
    "book": Reference(
        type="book",
        title="Systematic Reviews",
        authors=("Pereira, Ana", "Costa, Bruno"),
        year=2023,
        publisher="Academic Press",
        location="São Paulo",
    ),
    "book_chapter": Reference(
        type="book_chapter",
        title="Edited Volume",
        chapter_title="Search Strategies",
        authors=("Lima, Carlos",),
        book_editors=("Fernandes, Diana",),
        year=2022,
        publisher="University Press",
        location="Rio de Janeiro",
        pages="33-58",
    ),
    "thesis": Reference(
        type="thesis",
        title="A doctoral investigation",
        authors=("Souza, Eduardo",),
        year=2021,
        program="Programa de Pós-Graduação em Engenharia",
        institution="UFRJ",
        location="Rio de Janeiro",
    ),
    "dissertation": Reference(
        type="dissertation",
        title="A master's investigation",
        authors=("Mendes, Fernanda",),
        year=2020,
        program="Mestrado em Computação",
        institution="USP",
        location="São Paulo",
    ),
    "conference": Reference(
        type="conference",
        title="On scalable indexing",
        authors=("Ribeiro, Gabriel",),
        year=2024,
        venue="International Conference on Indexing",
        location="Curitiba",
        pages="200-205",
    ),
    "electronic": Reference(
        type="electronic",
        title="An online resource",
        authors=("Almeida, Henrique",),
        year=2024,
        url="https://example.org/resource",
        accessed="2026-05-07",
    ),
    "website": Reference(
        type="website",
        title="A website",
        authors=("Institucional",),
        year=2024,
        url="https://example.org/site",
        accessed="2026-05-07",
    ),
    "legislation": Reference(
        type="legislation",
        title="Lei nº 12.345, de 1 de janeiro de 2024",
        authors=(),
        year=2024,
        venue="Diário Oficial da União",
    ),
    "av_resource": Reference(
        type="av_resource",
        title="An audiovisual work",
        authors=("Rocha, Igor",),
        year=2023,
        venue="YouTube",
        url="https://example.org/video",
    ),
}


@pytest.fixture(params=list(CitationStyle), ids=lambda s: s.value)
def style(request: pytest.FixtureRequest) -> CitationStyle:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture
def formatter(style: CitationStyle) -> CitationFormatterPort:
    return citation_formatter_for(style)


class TestStyleMatchesRegistry:
    def test_formatter_reports_requested_style(
        self, style: CitationStyle, formatter: CitationFormatterPort
    ) -> None:
        assert formatter.style is style


class TestFormatReferenceContract:
    @pytest.mark.parametrize(
        "ref",
        list(_REFERENCE_FIXTURES.values()),
        ids=list(_REFERENCE_FIXTURES.keys()),
    )
    def test_returns_non_empty_string(
        self, formatter: CitationFormatterPort, ref: Reference
    ) -> None:
        result = formatter.format_reference(ref)
        assert isinstance(result, str)
        assert result.strip()

    @pytest.mark.parametrize(
        "ref",
        list(_REFERENCE_FIXTURES.values()),
        ids=list(_REFERENCE_FIXTURES.keys()),
    )
    def test_includes_title(self, formatter: CitationFormatterPort, ref: Reference) -> None:
        # Every style — author-date or numeric — must surface the work
        # title. Formatters wrap titles in Markdown emphasis markers, so
        # we substring-match the bare title text.
        result = formatter.format_reference(ref)
        assert ref.title in result


class TestInlineCitationContract:
    def test_returns_non_empty_string_with_year_and_authors(
        self, style: CitationStyle, formatter: CitationFormatterPort
    ) -> None:
        ref = _REFERENCE_FIXTURES["article"]
        kwargs: dict[str, object] = {}
        if style in _NUMERIC_STYLES:
            kwargs["index"] = 1
        result = formatter.format_inline_citation(ref, **kwargs)  # type: ignore[arg-type]
        assert isinstance(result, str)
        assert result.strip()

    def test_handles_missing_year(
        self, style: CitationStyle, formatter: CitationFormatterPort
    ) -> None:
        ref = Reference(
            type="article",
            title="Year-less article",
            authors=("Silva, João",),
        )
        kwargs: dict[str, object] = {}
        if style in _NUMERIC_STYLES:
            kwargs["index"] = 1
        result = formatter.format_inline_citation(ref, **kwargs)  # type: ignore[arg-type]
        assert isinstance(result, str)
        assert result.strip()


class TestReferenceWithMissingFields:
    def test_format_reference_handles_no_authors(self, formatter: CitationFormatterPort) -> None:
        ref = Reference(
            type="legislation",
            title="Anonymous statute",
            authors=(),
            year=2024,
        )
        result = formatter.format_reference(ref)
        assert isinstance(result, str)
        assert result.strip()

    def test_format_reference_handles_no_year(self, formatter: CitationFormatterPort) -> None:
        ref = Reference(
            type="article",
            title="Year-less article",
            authors=("Silva, João",),
            venue="Journal of SLR",
        )
        result = formatter.format_reference(ref)
        assert isinstance(result, str)
        assert result.strip()
