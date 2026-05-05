"""``HeinOnlineAdapter`` — HeinOnline legal repository (paywall stub).

HeinOnline does not expose a public REST search API. Access is
exclusively via institutional subscription; programmatic search is
unsupported. The adapter exposes the paywall contract but always falls
through to ``Method.REAL_ERROR`` with empty items, signalling that a
manual ``citations_to_obtain.md`` fallback is required.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class HeinOnlineAdapter(_PaywallAdapter):
    """Stub adapter for HeinOnline: cascade always falls through to FALLBACK."""

    source_id = "hein_online"
    source_tier = Tier.TIER2

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        del query
        return ()
