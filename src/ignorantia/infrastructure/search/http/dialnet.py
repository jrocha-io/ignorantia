"""``DialnetAdapter`` — Dialnet (Universidad de La Rioja) (no public API).

Tier-1 source for Spanish-language scholarly publications (Spain,
Latin America). Dialnet's REST API requires academic registration with
Universidad de La Rioja; without a key the only access is HTML, which
DD-6 forbids parsing. Coverage of Dialnet is partially reproduced by
OpenAlex (Spanish-language venues are well represented).
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class DialnetAdapter(_NoApiAdapter):
    """Stub adapter for Dialnet: requires institutional API registration."""

    source_id = "dialnet"
    source_tier = Tier.TIER1
