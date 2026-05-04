"""``SageFullAdapter`` — Sage Publications via Crossref filter (member:179).

Sage doesn't expose a public search API; its catalogue is, however,
fully indexed by Crossref. This adapter discovers DOIs through
Crossref's ``filter=member:179`` and reports them as TIER-2 records
(metadata only — full text requires Sage / institutional login).
"""

from __future__ import annotations

from typing import ClassVar

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._crossref_member import _CrossrefMemberAdapter


class SageFullAdapter(_CrossrefMemberAdapter):
    """Adapter for Sage Publications via Crossref ``member:179``."""

    source_id = "sage_full"
    source_tier = Tier.TIER2
    _MEMBER_ID: ClassVar[str] = "179"
