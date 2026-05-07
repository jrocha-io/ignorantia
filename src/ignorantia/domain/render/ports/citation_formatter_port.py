"""``CitationFormatterPort`` — the seam to a citation Strategy.

Each of the four supported citation styles (ABNT, APA, IEEE,
Vancouver, per issue #5) is a concrete implementation of this port.
The render pipeline picks one strategy per :class:`ManuscriptDoc`
based on the document language and renders both inline citations and
the reference list through it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.value_objects import CitationStyle


class CitationFormatterPort(ABC):
    """Abstract Strategy for rendering :class:`Reference` instances."""

    @property
    @abstractmethod
    def style(self) -> CitationStyle:
        """The canonical :class:`CitationStyle` this formatter implements."""

    @abstractmethod
    def format_reference(self, ref: Reference) -> str:
        """Return the reference-list entry for ``ref`` as a single string."""

    @abstractmethod
    def format_inline_citation(
        self,
        ref: Reference,
        *,
        page: str | None = None,
        index: int | None = None,
    ) -> str:
        """Return the inline citation for ``ref``.

        Args:
            ref: The reference being cited.
            page: Optional page number for direct quotations. Author-date
                styles (ABNT, APA) include it; numeric styles (IEEE,
                Vancouver) typically ignore it.
            index: 1-based position in the manuscript reference list.
                Numeric styles (IEEE, Vancouver) require it; author-date
                styles ignore it.
        """
