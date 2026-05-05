"""``OaResolverFactoryPort`` — composes OA resolvers by ``source_id``.

The application layer (F6 use cases) depends on this abstract factory.
Concrete factories live in :mod:`ignorantia.infrastructure.search` and
decide which resolver class to instantiate for each source identifier
(``"unpaywall"``, ``"oa_button"``, ...). Resolvers that need extra
configuration (e.g. Unpaywall's polite-pool email) are wired through
the concrete factory's constructor, not through ``create()``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.search.ports.oa_resolver_port import OaResolverPort


class OaResolverFactoryPort(ABC):
    """Abstract factory for :class:`OaResolverPort` instances."""

    @abstractmethod
    def create(self, source_id: str) -> OaResolverPort:
        """Return a resolver for ``source_id`` or raise :class:`KeyError`."""
