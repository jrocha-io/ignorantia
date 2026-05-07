"""``citation_formatter_for`` — Factory for citation Strategies.

Maps :class:`CitationStyle` enum values to lazily-instantiated singleton
:class:`CitationFormatterPort` adapters. The render pipeline picks one
strategy per :class:`ManuscriptDoc` and re-uses the same instance for
every reference, so amortising construction over the document is the
correct trade-off here.

The registry is intentionally a plain dict: adding a new style is a
two-step change — extend :class:`CitationStyle` and append the entry
here — both visible in the same review diff.
"""

from __future__ import annotations

from collections.abc import Callable

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
from ignorantia.infrastructure.render.citation.ieee_formatter import (
    IeeeCitationFormatter,
)
from ignorantia.infrastructure.render.citation.vancouver_formatter import (
    VancouverCitationFormatter,
)

_BUILDERS: dict[CitationStyle, Callable[[], CitationFormatterPort]] = {
    CitationStyle.ABNT: AbntCitationFormatter,
    CitationStyle.APA: ApaCitationFormatter,
    CitationStyle.IEEE: IeeeCitationFormatter,
    CitationStyle.VANCOUVER: VancouverCitationFormatter,
}

_INSTANCES: dict[CitationStyle, CitationFormatterPort] = {}


def citation_formatter_for(style: CitationStyle) -> CitationFormatterPort:
    """Return the :class:`CitationFormatterPort` adapter for ``style``.

    The same instance is returned for every call with the same ``style``;
    formatters are stateless Strategies, so sharing instances is safe and
    avoids needless allocation when rendering a large reference list.

    Raises:
        ValueError: ``style`` is not one of the four supported
            :class:`CitationStyle` values.
    """
    cached = _INSTANCES.get(style)
    if cached is not None:
        return cached

    builder = _BUILDERS.get(style)
    if builder is None:
        raise ValueError(f"unsupported citation style: {style!r}")

    instance = builder()
    _INSTANCES[style] = instance
    return instance
