"""``ClacsoAdapter`` — CLACSO repository (no usable API).

Tier-1 source for Latin American social-science research aggregated by
the Consejo Latinoamericano de Ciencias Sociales. The CLACSO
repository is DSpace-based and exposes an OAI-PMH endpoint, but the
endpoint serves bulk-harvest dumps (no full-text query verb), and the
public search interface is HTML-only — both paths are out of scope
under DD-6 "no scraping". OpenAlex and LA Referencia (already
registered) cover most CLACSO-indexed works.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class ClacsoAdapter(_NoApiAdapter):
    """Stub adapter for CLACSO: no programmatic search API."""

    source_id = "clacso"
    source_tier = Tier.TIER1
