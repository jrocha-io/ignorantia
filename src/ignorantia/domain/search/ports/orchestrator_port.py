"""``OrchestratorPort`` — the interface the application layer uses to run searches.

A separate port (rather than depending on the concrete service directly)
keeps F6 (``application/use_cases/search_for_studies``) decoupled from
the orchestration implementation: a future replacement (parallel,
asynchronous, distributed) can swap in without touching use cases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.search.entities import SearchQuery, SearchResult


class OrchestratorPort(ABC):
    """Abstract orchestrator that asks adapters to fetch a query."""

    @abstractmethod
    def run(self, query: SearchQuery, source_ids: tuple[str, ...]) -> dict[str, SearchResult]:
        """Run ``query`` against every source in ``source_ids``.

        Returns:
            A mapping from each ``source_id`` to its :class:`SearchResult`.
        """
