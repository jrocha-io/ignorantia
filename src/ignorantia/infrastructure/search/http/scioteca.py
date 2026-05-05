"""``SciotecaAdapter`` — Scioteca (CAF development bank library, no API).

Tier-1 source for Latin American development-economics grey literature
published by CAF (Banco de Desarrollo de América Latina). Scioteca
runs a DSpace instance whose only programmatic interface is OAI-PMH
date-range harvesting (no search verb); the public search UI is HTML.
Per DD-6 the adapter is a stub.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class SciotecaAdapter(_NoApiAdapter):
    """Stub adapter for Scioteca (CAF): no programmatic search API."""

    source_id = "scioteca"
    source_tier = Tier.TIER1
