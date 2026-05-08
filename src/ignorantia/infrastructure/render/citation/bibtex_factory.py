"""Factory mapping :class:`BibTexStyle` → :class:`BibTexEntryFormatterPort`.

Mirrors the pattern in :mod:`citation_formatter_for` (PR #53):
lazy-singleton registry over the four BibTeX adapters merged in
this PR.
"""

from __future__ import annotations

from collections.abc import Callable

from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
    BibTexEntryFormatterPort,
    BibTexStyle,
)
from ignorantia.infrastructure.render.citation.bibtex_abntex2cite import (
    BibTexAbntex2CiteFormatter,
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

_BUILDERS: dict[BibTexStyle, Callable[[], BibTexEntryFormatterPort]] = {
    BibTexStyle.PLAIN: BibTexPlainFormatter,
    BibTexStyle.UNSRT: BibTexUnsrtFormatter,
    BibTexStyle.ABNTEX2: BibTexAbntex2CiteFormatter,
    BibTexStyle.IEEETRAN: BibTexIEEEtranFormatter,
}

_INSTANCES: dict[BibTexStyle, BibTexEntryFormatterPort] = {}


def bibtex_formatter_for(style: BibTexStyle) -> BibTexEntryFormatterPort:
    """Return the :class:`BibTexEntryFormatterPort` adapter for ``style``.

    Returns the same instance for every call with the same ``style``;
    formatters are stateless Strategies, so sharing instances avoids
    needless allocation when the bib file lists hundreds of entries.

    Raises:
        ValueError: ``style`` is not a registered enum value.
    """
    cached = _INSTANCES.get(style)
    if cached is not None:
        return cached
    builder = _BUILDERS.get(style)
    if builder is None:
        raise ValueError(f"unsupported BibTeX style: {style!r}")
    instance = builder()
    _INSTANCES[style] = instance
    return instance
