"""``ProquestOaAdapter`` — ProQuest PQDT Open subset (no public API).

Tier-1 source for theses and dissertations. PQDT Open is a freely
browsable subset of ProQuest's dissertation index, but ProQuest does
not expose a REST API for it; programmatic discovery would require
HTML scraping (out of scope under DD-6). The adapter registers the
source but always reports ``Method.REAL_ERROR`` with empty items,
signalling downstream that a manual ``citations_to_obtain.md``
fallback is required.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class ProquestOaAdapter(AdapterPort):
    """Stub adapter for ProQuest PQDT Open: no programmatic access available."""

    source_id = "proquest_oa"
    source_tier = Tier.TIER1

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
