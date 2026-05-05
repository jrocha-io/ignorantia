"""``_NoApiAdapter`` — base class for sources with no programmatic API.

Several Tier-1 / Tier-2 databases that PRISMA-2020 reviewers must
declare in a manifest expose **no public REST/JSON endpoint**: their
only public interface is HTML, which v3 will not scrape (DD-6 forbids
parser-fragile HTML extraction). The adapter is still registered so
the source identifier is part of the system's vocabulary, but every
``fetch()`` immediately returns ``Method.REAL_ERROR`` with empty items.
Downstream code (the audit context, in F5) is responsible for emitting
a ``citations_to_obtain.md`` listing the items the reviewer must
retrieve manually.

Subclasses only need to set ``source_id`` and ``source_tier`` —
nothing else.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method
from ignorantia.infrastructure.http_client import HttpClient


class _NoApiAdapter(AdapterPort):
    """Abstract base for sources with no programmatic API."""

    def __init__(self, http: HttpClient) -> None:
        """Accept the shared HTTP client for interface uniformity."""
        self._http = http

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Always report ``Method.REAL_ERROR`` — no public API exists."""
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL_ERROR,
            query=query,
            items=(),
        )
