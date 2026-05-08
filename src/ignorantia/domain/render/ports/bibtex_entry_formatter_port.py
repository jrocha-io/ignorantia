"""``BibTexEntryFormatterPort`` — Strategy seam for BibTeX entry emission.

The existing :class:`CitationFormatterPort` emits a single string
per :class:`Reference` for human-readable list output (one-line
ABNT/APA/IEEE/Vancouver entries that go inside the manuscript's
references section). BibTeX is a different shape entirely: each
entry is a multi-line structured record with a citation key,
entry type, and named fields::

    @article{silva2024quality,
        author = {Silva, J. P.},
        title  = {Quality of evidence in SLRs},
        journal = {Journal of SLR},
        year   = {2024},
        volume = {10},
        number = {2},
        pages  = {100--110},
        doi    = {10.1234/jsl.2024.001}
    }

A separate port keeps :class:`CitationFormatterPort` focused on
inline / list output (Interface Segregation), and lets the BibTeX
implementations share their own machinery (key generation,
field-name conventions per style — ``plain`` uses ``number``,
``abntex2cite`` uses ``volume``-with-``issue``, etc.) without
polluting the human-text formatters.

Concrete adapters live in
``infrastructure/render/citation/bibtex_*`` (one per equivalent
BibTeX style). The :class:`BibTexStyle` enum below pins the
canonical wire vocabulary; the entry-formatter factory in the
infrastructure layer maps each enum member to its adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from ignorantia.domain.render.entities import Reference


class BibTexStyle(str, Enum):
    r"""Canonical wire vocabulary for BibTeX style identifiers.

    Each value matches the ``\\bibliographystyle{<value>}`` LaTeX
    command — so the LaTeX renderer can emit the right
    bibliographystyle directive without translating the enum.

    ``BibTexStyle`` derives from :class:`str` so JSON serialisation
    of payloads carrying a chosen style is transparent.
    """

    PLAIN = "plain"
    """The default BibTeX style; alphabetical, numeric labels."""

    UNSRT = "unsrt"
    """Unsorted; entries appear in the order they were cited."""

    ABNTEX2 = "abntex2-num"
    """ABNT NBR 6023 / NBR 10520 numeric style. Pairs with the
    abntex2cite package; uppercases author surnames, includes the
    Brazilian portuguese hyphenation conventions."""

    IEEETRAN = "IEEEtran"
    """IEEE Transactions style. Numeric inline citations [N];
    author initials before surname; venue abbreviations."""

    def __str__(self) -> str:
        r"""Return the canonical ``\\bibliographystyle{}`` value."""
        return self.value


class BibTexEntryFormatterPort(ABC):
    """Abstract Strategy emitting one BibTeX entry per :class:`Reference`."""

    @property
    @abstractmethod
    def style(self) -> BibTexStyle:
        """The :class:`BibTexStyle` this formatter emits."""

    @abstractmethod
    def format_entry(self, ref: Reference, *, key: str) -> str:
        r"""Return the BibTeX entry for ``ref`` as a multi-line string.

        Args:
            ref: The reference to render.
            key: The citation key (e.g. ``silva2024quality``).
                Generated externally so callers can deduplicate
                across the entire bibliography before formatting.

        Returns:
            A multi-line string starting with ``@<type>{<key>,`` and
            ending with ``}``. The implementation handles BibTeX
            character escaping (``& % # _ { } \\``) on every field
            value.
        """
