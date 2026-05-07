"""Unit tests for :func:`citation_formatter_for`.

The factory maps :class:`CitationStyle` enum values to concrete
:class:`CitationFormatterPort` implementations (the F4b-F4e Strategy
adapters). Tests pin:

* one mapping per supported style;
* the returned object is a :class:`CitationFormatterPort` whose
  ``style`` property matches the requested style — guarding against
  miswired registry entries;
* repeated calls return the same instance (lazy singleton, so the
  pipeline does not pay re-construction cost per reference);
* an unsupported style raises ``ValueError`` with a helpful message.
"""

from __future__ import annotations

from enum import Enum

import pytest

from ignorantia.domain.render.ports.citation_formatter_port import (
    CitationFormatterPort,
)
from ignorantia.domain.render.value_objects import CitationStyle
from ignorantia.infrastructure.render.citation.abnt_formatter import (
    AbntCitationFormatter,
)
from ignorantia.infrastructure.render.citation.apa_formatter import (
    ApaCitationFormatter,
)
from ignorantia.infrastructure.render.citation.factory import (
    citation_formatter_for,
)
from ignorantia.infrastructure.render.citation.ieee_formatter import (
    IeeeCitationFormatter,
)
from ignorantia.infrastructure.render.citation.vancouver_formatter import (
    VancouverCitationFormatter,
)


class TestStyleMapping:
    def test_abnt_returns_abnt_formatter(self) -> None:
        formatter = citation_formatter_for(CitationStyle.ABNT)
        assert isinstance(formatter, AbntCitationFormatter)

    def test_apa_returns_apa_formatter(self) -> None:
        formatter = citation_formatter_for(CitationStyle.APA)
        assert isinstance(formatter, ApaCitationFormatter)

    def test_ieee_returns_ieee_formatter(self) -> None:
        formatter = citation_formatter_for(CitationStyle.IEEE)
        assert isinstance(formatter, IeeeCitationFormatter)

    def test_vancouver_returns_vancouver_formatter(self) -> None:
        formatter = citation_formatter_for(CitationStyle.VANCOUVER)
        assert isinstance(formatter, VancouverCitationFormatter)


class TestPortContract:
    @pytest.mark.parametrize("style", list(CitationStyle))
    def test_returned_value_is_a_citation_formatter_port(self, style: CitationStyle) -> None:
        formatter = citation_formatter_for(style)
        assert isinstance(formatter, CitationFormatterPort)

    @pytest.mark.parametrize("style", list(CitationStyle))
    def test_returned_formatter_reports_matching_style(self, style: CitationStyle) -> None:
        formatter = citation_formatter_for(style)
        assert formatter.style is style


class TestSingletonBehaviour:
    @pytest.mark.parametrize("style", list(CitationStyle))
    def test_same_style_returns_same_instance(self, style: CitationStyle) -> None:
        first = citation_formatter_for(style)
        second = citation_formatter_for(style)
        assert first is second

    def test_distinct_styles_return_distinct_instances(self) -> None:
        abnt = citation_formatter_for(CitationStyle.ABNT)
        apa = citation_formatter_for(CitationStyle.APA)
        assert abnt is not apa


class TestUnsupportedStyle:
    def test_unknown_style_value_raises_value_error(self) -> None:
        class FakeStyle(str, Enum):
            CHICAGO = "chicago"

        with pytest.raises(ValueError, match="chicago"):
            citation_formatter_for(FakeStyle.CHICAGO)  # type: ignore[arg-type]
