"""``SearchOrchestrator`` — concrete :class:`OrchestratorPort` for the domain.

The orchestrator is a *domain service* (DDD): it coordinates multiple
adapters but holds no I/O or persistence concern. It delegates adapter
construction to an :class:`AdapterFactoryPort` and deduplication to
:class:`DeduplicatorService`.

Resilience policy: per-adapter network errors (``HTTPError``,
``URLError``, ``TimeoutError``) are converted to a ``Method.REAL_ERROR``
result so a single flaky source does not abort an SLR pipeline that
queries dozens of databases. Programming errors and contract
violations (``RuntimeError``, ``KeyError``, ``ValueError``, ...) still
propagate — they are bugs to fix, not transient failures.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.error import HTTPError, URLError

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.ports.orchestrator_port import OrchestratorPort
from ignorantia.domain.search.services.deduplicator import DeduplicatorService
from ignorantia.domain.search.value_objects import Method

_NETWORK_ERRORS: tuple[type[BaseException], ...] = (HTTPError, URLError, TimeoutError)


class SearchOrchestrator(OrchestratorPort):
    """Aggregates adapter responses for a single :class:`SearchQuery`."""

    def __init__(self, factory: AdapterFactoryPort) -> None:
        """Wire the orchestrator to an adapter factory."""
        self._factory = factory

    def run(self, query: SearchQuery, source_ids: tuple[str, ...]) -> dict[str, SearchResult]:
        """Ask each adapter to ``fetch(query)`` and capture network failures."""
        results: dict[str, SearchResult] = {}
        for sid in source_ids:
            adapter = self._factory.create(sid)
            results[sid] = self._fetch_or_capture(adapter, query)
        return results

    @staticmethod
    def deduplicated_items(
        results: dict[str, SearchResult],
    ) -> tuple[FetchedItem, ...]:
        """Return all items across ``results`` with duplicates collapsed."""
        return DeduplicatorService.deduplicate(_chain_items(results.values()))

    @staticmethod
    def _fetch_or_capture(adapter: AdapterPort, query: SearchQuery) -> SearchResult:
        try:
            return adapter.fetch(query)
        except _NETWORK_ERRORS:
            return SearchResult(
                source=adapter.source_id,
                source_tier=adapter.source_tier,
                method=Method.REAL_ERROR,
                query=query,
                items=(),
            )


def _chain_items(results: Iterable[SearchResult]) -> Iterable[FetchedItem]:
    for r in results:
        yield from r.items
