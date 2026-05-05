"""``PeriodicosCapesAdapter`` — Portal CAPES (institutional only).

Tier-1 source aggregating thousands of paywall journals available to
Brazilian researchers via federated authentication through CAPES.
The portal has no public API; access requires institutional Single
Sign-On from a Brazilian higher-education or research institution.
The adapter is registered so the source identifier is part of the
manifest vocabulary, but downstream code must surface the manual
CAPES route in ``citations_to_obtain.md``.
"""

from __future__ import annotations

from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class PeriodicosCapesAdapter(_NoApiAdapter):
    """Stub adapter for Portal CAPES: institutional SSO only."""

    source_id = "periodicos_capes"
    source_tier = Tier.TIER1
