"""``ProquestOaAdapter`` — ProQuest PQDT Open subset (no public API).

Tier-1 source for theses and dissertations. PQDT Open is a freely
browsable subset of ProQuest's dissertation index, but ProQuest does
not expose a REST API for it; programmatic discovery would require
HTML scraping (out of scope under DD-6).
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class ProquestOaAdapter(_NoApiAdapter):
    """Stub adapter for ProQuest PQDT Open: no programmatic access available."""

    source_id = "proquest_oa"
    source_tier = Tier.TIER1
