"""``ProquestFullAdapter`` — full ProQuest (paywall stub).

Tier-2 paywall. ProQuest's full content is gated behind institutional
subscription with no public API; the proxy path returns HTML that
requires source-specific parsing. The adapter exposes the paywall
contract but always falls through to ``Method.REAL_ERROR`` with empty
items, signalling that a manual ``citations_to_obtain.md`` fallback
is required.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class ProquestFullAdapter(_PaywallAdapter):
    """Stub adapter for ProQuest full: cascade always falls through to FALLBACK."""

    source_id = "proquest_full"
    source_tier = Tier.TIER2

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        del query
        return ()
