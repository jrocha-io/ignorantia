"""``CochraneCentralAdapter`` — Cochrane CENTRAL register (no public API).

Tier-1 source per PRISMA-2020 + Cochrane Handbook for SRs of
interventions. Cochrane Library does not expose a public REST API for
CENTRAL; access is only via the institutional Wiley Online Library
contract or the public web search UI (HTML, parser-fragile and out of
scope under DD-6 "no scraping"). The adapter therefore registers the
source identifier but always reports ``Method.REAL_ERROR`` with empty
items, signalling downstream that a manual ``citations_to_obtain.md``
fallback is required. Reviewers running PubMed with the
``Randomized Controlled Trial`` publication-type filter cover most of
CENTRAL's overlap.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class CochraneCentralAdapter(AdapterPort):
    """Stub adapter for Cochrane CENTRAL: no programmatic access available."""

    source_id = "cochrane_central"
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
