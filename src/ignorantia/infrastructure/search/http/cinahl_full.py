"""``CinahlFullAdapter`` — CINAHL via EBSCOhost (paywall stub).

CINAHL has no individual API key — access requires institutional EBSCO
credentials. There is no usable programmatic endpoint for non-IES
users, and the proxy path returns HTML that requires source-specific
parsing not yet implemented. The adapter therefore exposes the paywall
contract but always falls through to ``Method.REAL_ERROR`` with empty
items, signalling to downstream code that a manual ``citations_to_obtain.md``
fallback is required.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class CinahlFullAdapter(_PaywallAdapter):
    """Stub adapter for CINAHL: cascade always falls through to FALLBACK."""

    source_id = "cinahl_full"
    source_tier = Tier.TIER2

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        del query
        return ()
