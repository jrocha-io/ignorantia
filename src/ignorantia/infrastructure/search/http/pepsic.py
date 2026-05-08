"""``PepsicAdapter`` — PePSIC via BVS (no public API).

Tier-1 source for Latin American psychology journals on the BVS
network. Same architectural limitation as LILACS: only HTML search
through ``pesquisa.bvsalud.org``, no JSON/XML endpoint, and DD-6
forbids HTML parsing. Coverage of PePSIC overlaps with PsycInfo +
SciELO, both of which are independently registered.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class PepsicAdapter(_NoApiAdapter):
    """Stub adapter for PePSIC: no programmatic access available."""

    source_id = "pepsic"
    source_tier = Tier.TIER1
