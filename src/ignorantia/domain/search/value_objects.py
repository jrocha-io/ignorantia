"""Value objects for the search bounded context.

A value object is identified by its content alone — two ``Tier.TIER1``
instances are interchangeable. The wire formats below are canonical and
must not be silently changed; downstream artefacts
(``orchestration_summary.json``, ``search_result.json``) are validated
against these strings.
"""

from __future__ import annotations

from enum import Enum


class Tier(str, Enum):
    """Open-access classification tier for a bibliographic source.

    Per DD-1 (v2.10.0) the catalogue is organised in a tiered hierarchy.
    All 62 search adapters report a tier value drawn from this canonical
    set, resolving the Liskov violation found in v2.x audit #5 (fix E1)
    where ``source_tier`` was sometimes ``int`` and sometimes ``str``.

    ``Tier`` derives from :class:`str` so JSON serialisation is
    transparent — ``json.dumps(Tier.TIER1) == '"tier1"'``.
    """

    TIER0 = "tier0"
    """Tier-0 resolvers (Unpaywall, OAB, CORE, Periódicos CAPES) used to
    upgrade locked items found in higher tiers."""

    TIER1 = "tier1"
    """Free open access with full text available. Searched first."""

    TIER2 = "tier2"
    """Free metadata only; full text behind a paywall."""

    TIER3 = "tier3"
    """Paywall sources reachable via the legal cascade
    (user credentials, institutional proxy)."""

    def __str__(self) -> str:
        """Return the canonical wire value (e.g. ``"tier1"``).

        Required because Python 3.11 changed the default
        ``str(StrEnum.MEMBER)`` to return ``"Tier.TIER1"`` instead of the
        value, which would silently break legacy callers.
        """
        return self.value


class Method(str, Enum):
    """How an adapter produced its results during a single run.

    Pinned by audit #5 fix E6 (v2.23.0) as the canonical reporting
    vocabulary across the 62 adapters.
    """

    MOCK = "mock"
    """Synthetic fixtures returned without contacting the network."""

    REAL = "real"
    """Live network call succeeded and parsing was complete."""

    REAL_PARTIAL = "real_partial"
    """Live call succeeded but some records failed to parse."""

    REAL_ERROR = "real_error"
    """Live call attempted and failed; no records returned."""

    def __str__(self) -> str:
        """Return the canonical wire value (e.g. ``"tier1"``).

        Required because Python 3.11 changed the default
        ``str(StrEnum.MEMBER)`` to return ``"Tier.TIER1"`` instead of the
        value, which would silently break legacy callers.
        """
        return self.value
