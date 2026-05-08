"""``OaResolverPort`` — the contract every tier-0 OA resolver must honour.

A *tier-0 resolver* differs from a text-search :class:`AdapterPort`: it
takes a single identifier (typically a DOI) and returns the best known
OA location, or ``None`` when no OA copy is indexed. Concrete
implementations live in :mod:`ignorantia.infrastructure.search.http`
and include Unpaywall, OaButton, CORE, ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.search.entities import OaLocation


class OaResolverPort(ABC):
    """Abstract base class for any tier-0 OA resolver.

    Subclasses must declare:

    * :attr:`source_id` — stable identifier for the resolver
      (e.g. ``"unpaywall"``).
    * :meth:`resolve` — given a raw DOI string, return an
      :class:`OaLocation` or ``None``.

    Identifier validation (DOI grammar) is the *caller's*
    responsibility; passing a value the resolver cannot understand is a
    contract violation that legitimately raises ``ValueError``. The
    typical caller is the F6 application layer, which wraps the raw
    string in a ``DOI`` value object before calling.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Stable identifier (e.g. ``"unpaywall"``)."""

    @abstractmethod
    def resolve(self, doi: str) -> OaLocation | None:
        """Look up the best OA location for ``doi``.

        Args:
            doi: Bare DOI string, without ``https://doi.org/`` prefix.

        Returns:
            :class:`OaLocation` populated with whatever the resolver
            could find, or ``None`` when the resolver has no entry or
            the item is not OA.
        """
