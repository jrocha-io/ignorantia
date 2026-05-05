"""``ScieloPreprintsAdapter`` — SciELO Preprints (no usable API).

Tier-1 preprint server for Latin American & Iberian science. Hosted
on OJS; the OAI-PMH endpoint supports only date-range harvesting (no
keyword search), and the public search UI is HTML — both out of scope
under DD-6. Crossref, OpenAlex, and the main SciELO adapter cover
preprints with DOIs registered through them.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class ScieloPreprintsAdapter(_NoApiAdapter):
    """Stub adapter for SciELO Preprints: no programmatic search API."""

    source_id = "scielo_preprints"
    source_tier = Tier.TIER1
