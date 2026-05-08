"""``DabiAdapter`` — DABI (Information Architecture Database) (no public API).

Tier-1 source for Brazilian information science / library science
literature. DABI is hosted on a tidsskrift.dk OJS instance whose
search endpoint returns HTML only; no public REST API exists. Per
DD-6 this adapter is a stub.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class DabiAdapter(_NoApiAdapter):
    """Stub adapter for DABI: no programmatic access available."""

    source_id = "dabi"
    source_tier = Tier.TIER1
