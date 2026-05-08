"""``BibTexUnsrtFormatter`` — ``unsrt`` style (citation-order entries)."""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
    BibTexEntryFormatterPort,
    BibTexStyle,
)
from ignorantia.infrastructure.render.citation.bibtex_plain import (
    BibTexPlainFormatter,
)


class BibTexUnsrtFormatter(BibTexEntryFormatterPort):
    r"""``unsrt`` style — entries appear in citation order.

    Field shape is identical to ``plain``; only the
    ``\\bibliographystyle{}`` directive in the LaTeX file changes.
    The formatter delegates to :class:`BibTexPlainFormatter` and
    differs only in the :attr:`style` property.
    """

    def __init__(self) -> None:
        """Wrap a :class:`BibTexPlainFormatter` for field emission."""
        self._inner = BibTexPlainFormatter()

    @property
    def style(self) -> BibTexStyle:
        """Return :class:`BibTexStyle.UNSRT`."""
        return BibTexStyle.UNSRT

    def format_entry(self, ref: Reference, *, key: str) -> str:
        """Return the ``@<type>{<key>, …}`` entry — same shape as plain."""
        return self._inner.format_entry(ref, key=key)
