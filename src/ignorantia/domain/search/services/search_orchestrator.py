"""``SearchOrchestrator`` — concrete :class:`OrchestratorPort` for the domain.

The orchestrator is a *domain service* (DDD): it coordinates multiple
adapters but holds no I/O or persistence concern. It delegates adapter
construction to an :class:`AdapterFactoryPort` and deduplication to
:class:`DeduplicatorService`.
"""

from __future__ import annotations

from collections.abc import Iterable

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.orchestrator_port import OrchestratorPort
from ignorantia.domain.search.services.deduplicator import DeduplicatorService


class SearchOrchestrator(OrchestratorPort):
    """Aggregates adapter responses for a single :class:`SearchQuery`."""

    def __init__(self, factory: AdapterFactoryPort) -> None:
        """Wire the orchestrator to an adapter factory."""
        self._factory = factory

    def run(self, query: SearchQuery, source_ids: tuple[str, ...]) -> dict[str, SearchResult]:
        """Ask each adapter to ``fetch(query)``; bubble up errors as-is."""
        return {sid: self._factory.create(sid).fetch(query) for sid in source_ids}

    @staticmethod
    def deduplicated_items(
        results: dict[str, SearchResult],
    ) -> tuple[FetchedItem, ...]:
        """Return all items across ``results`` with duplicates collapsed."""
        return DeduplicatorService.deduplicate(_chain_items(results.values()))


def _chain_items(results: Iterable[SearchResult]) -> Iterable[FetchedItem]:
    for r in results:
        yield from r.items
