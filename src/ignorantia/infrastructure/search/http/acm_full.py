"""``AcmFullAdapter`` — ACM Digital Library via Crossref filter (member:320).

ACM has no public search API for OpenTOC; its catalogue is fully
indexed by Crossref. This adapter discovers DOIs through Crossref's
``filter=member:320`` and reports them as TIER-2 records.
"""

from __future__ import annotations

from typing import ClassVar

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._crossref_member import _CrossrefMemberAdapter


class AcmFullAdapter(_CrossrefMemberAdapter):
    """Adapter for ACM Digital Library via Crossref ``member:320``."""

    source_id = "acm_full"
    source_tier = Tier.TIER2
    _MEMBER_ID: ClassVar[str] = "320"
