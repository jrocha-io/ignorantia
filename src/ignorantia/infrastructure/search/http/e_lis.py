"""``ELisAdapter`` — E-LIS (E-Prints in Library and Information Science).

Tier-1 source for OA library and information science research. E-LIS
runs an EPrints instance with an OAI-PMH endpoint suitable only for
bulk harvesting (no keyword-search verb), and its public search UI is
HTML-only — both out of scope under DD-6. Coverage of E-LIS overlaps
with CORE and OpenAlex, both already registered.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class ELisAdapter(_NoApiAdapter):
    """Stub adapter for E-LIS: no programmatic search API."""

    source_id = "e_lis"
    source_tier = Tier.TIER1
