"""``JstorFullAdapter`` — full JSTOR archive (paywall stub).

Tier-2 paywall. JSTOR's Constellate API requires per-project review
and approval; there is no general-purpose key for individual users.
The proxy path returns HTML that requires source-specific parsing.
The adapter exposes the paywall contract but always falls through to
``Method.REAL_ERROR`` with empty items, signalling that a manual
``citations_to_obtain.md`` fallback is required.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class JstorFullAdapter(_PaywallAdapter):
    """Stub adapter for JSTOR full: cascade always falls through to FALLBACK."""

    source_id = "jstor_full"
    source_tier = Tier.TIER2

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        del query
        return ()
