"""``AdapterPort`` — the contract every search adapter must honour.

Concrete adapters (one per database) live in
``ignorantia.infrastructure.search.http`` and must subclass this ABC.
The orchestrator and the application layer talk to adapters through this
port and never know the concrete implementation, satisfying the
*Dependency Inversion Principle*.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.search.entities import SearchQuery, SearchResult
from ignorantia.domain.search.value_objects import Tier


class AdapterPort(ABC):
    """Abstract base class for all search adapters.

    Subclasses must expose three things:

    * :attr:`source_id` — a stable, lowercase identifier (e.g. ``"arxiv"``)
      used by the :class:`AdapterFactory` and emitted into manifests.
    * :attr:`source_tier` — the :class:`Tier` classification of the
      underlying database.
    * :meth:`fetch` — the actual call to the source.

    The two metadata attributes are declared as abstract properties; a
    subclass may satisfy them either by overriding the property or simply
    by assigning a class attribute (which Python accepts as a concrete
    override). The returned :class:`SearchResult` *must* have
    ``source == self.source_id`` and ``source_tier == self.source_tier``
    so downstream consumers can rely on consistency.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Stable identifier for this adapter (e.g. ``"arxiv"``)."""

    @property
    @abstractmethod
    def source_tier(self) -> Tier:
        """Tier classification of the underlying source."""

    @abstractmethod
    def fetch(self, query: SearchQuery) -> SearchResult:
        """Execute ``query`` against the adapter's source.

        Args:
            query: Caller-supplied query.

        Returns:
            A :class:`SearchResult` whose ``source`` and ``source_tier``
            match this adapter's metadata.
        """
