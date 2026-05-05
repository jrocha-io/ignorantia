"""``CochraneCentralAdapter`` — Cochrane CENTRAL register (no public API).

Tier-1 source per PRISMA-2020 + Cochrane Handbook for SRs of
interventions. Cochrane Library does not expose a public REST API for
CENTRAL; access is only via the institutional Wiley Online Library
contract or the public web search UI (HTML, parser-fragile and out of
scope under DD-6 "no scraping"). Reviewers running PubMed with the
``Randomized Controlled Trial`` publication-type filter cover most of
CENTRAL's overlap.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class CochraneCentralAdapter(_NoApiAdapter):
    """Stub adapter for Cochrane CENTRAL: no programmatic access available."""

    source_id = "cochrane_central"
    source_tier = Tier.TIER1
