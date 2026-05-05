"""``RedalycAdapter`` — Redalyc Iberoamerican OA aggregator (no public API).

Tier-1 source aggregating ~1.5K OA Iberoamerican journals (Mexico,
Spain, Portugal, Latin America). Redalyc's public ``buscar.php``
endpoint returns mixed JSON / HTML depending on the query and breaks
unpredictably; a stable parser cannot be built without scraping
(DD-6 forbids). OpenAlex covers most Redalyc-indexed journals via the
publisher graph.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class RedalycAdapter(_NoApiAdapter):
    """Stub adapter for Redalyc: no stable programmatic access."""

    source_id = "redalyc"
    source_tier = Tier.TIER1
