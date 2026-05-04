"""``WileyTdmAdapter`` — Wiley Online Library via Crossref filter (member:311).

Wiley's own search API requires institutional TDM agreement; the public
catalogue is fully indexed by Crossref. Like the Sage and ACM adapters,
this discovers DOIs through Crossref and reports them as TIER-2 records.
Full text retrieval is downstream and requires the user's Wiley TDM key.
"""

from __future__ import annotations

from typing import ClassVar

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._crossref_member import _CrossrefMemberAdapter


class WileyTdmAdapter(_CrossrefMemberAdapter):
    """Adapter for Wiley Online Library via Crossref ``member:311``."""

    source_id = "wiley_tdm"
    source_tier = Tier.TIER2
    _MEMBER_ID: ClassVar[str] = "311"
