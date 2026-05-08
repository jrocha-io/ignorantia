"""``CatalogoTesesCapesAdapter`` — CAPES theses catalog (no public API).

Tier-1 source for Brazilian master's and doctoral theses. The CAPES
catalog has no public REST/JSON endpoint; the OAI-PMH endpoint serves
date-range dumps unsuitable for keyword search, and the HTML
interface is out of scope under DD-6. BDTD (already registered) is
the recommended alternative — it federates the same theses through
the Brazilian institutional repository network.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class CatalogoTesesCapesAdapter(_NoApiAdapter):
    """Stub adapter for CAPES theses catalog: no programmatic search API."""

    source_id = "catalogo_teses_capes"
    source_tier = Tier.TIER1
