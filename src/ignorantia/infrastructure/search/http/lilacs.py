"""``LilacsAdapter`` — LILACS via BVS (no public API).

Tier-1 source for Latin American & Caribbean health science literature
(BVS / VHL Pan-American Health Organization). The BVS portal exposes
no JSON/XML search endpoint; access is HTML-only via
``pesquisa.bvsalud.org``, which DD-6 forbids parsing. A LILACS
fraction is also reachable through PubMed (the NLM imports a subset
of LILACS records), so SR reviewers should run a parallel PubMed
query as the primary discovery path.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class LilacsAdapter(_NoApiAdapter):
    """Stub adapter for LILACS: no programmatic access available."""

    source_id = "lilacs"
    source_tier = Tier.TIER1
