"""``SpellAdapter`` — Spell (Brazilian management & accounting) (no public API).

Tier-1 source for Brazilian business, management, and accounting
journals (curated by ANPAD). Spell exposes no REST API; the public
search interface is HTML-only and DD-6 forbids parsing. Most Spell
venues are also indexed in SciELO, which is independently registered.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class SpellAdapter(_NoApiAdapter):
    """Stub adapter for Spell: no programmatic access available."""

    source_id = "spell"
    source_tier = Tier.TIER1
