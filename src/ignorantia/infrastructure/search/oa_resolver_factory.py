"""``OaResolverFactory`` — concrete :class:`OaResolverFactoryPort`.

Composition root for tier-0 OA resolvers. ``OaButtonResolver`` is
always available; ``UnpaywallResolver`` requires a polite-pool email
and is therefore only registered when ``unpaywall_email`` is provided
to the factory's constructor. Adding a new resolver in F6 means
extending the per-source branch in :meth:`create` and the tuple
returned by :meth:`known_sources`.
"""

from __future__ import annotations

from ignorantia.domain.search.ports.oa_resolver_factory_port import (
    OaResolverFactoryPort,
)
from ignorantia.domain.search.ports.oa_resolver_port import OaResolverPort
from ignorantia.infrastructure.http_client import HttpClient
from ignorantia.infrastructure.search.http.oa_button import OaButtonResolver
from ignorantia.infrastructure.search.http.unpaywall import UnpaywallResolver


class OaResolverFactory(OaResolverFactoryPort):
    """Build OA resolvers on demand, sharing one :class:`HttpClient`."""

    def __init__(self, http: HttpClient, *, unpaywall_email: str | None = None) -> None:
        """Wire the factory.

        Args:
            http: Shared HTTP client.
            unpaywall_email: Polite-pool email for the Unpaywall API.
                If ``None``, ``"unpaywall"`` is not a known source.
        """
        self._http = http
        self._unpaywall_email = unpaywall_email

    def create(self, source_id: str) -> OaResolverPort:
        """Return a resolver for ``source_id``.

        Raises:
            KeyError: when ``source_id`` is unknown or when its required
                configuration (e.g. Unpaywall's email) is missing.
        """
        if source_id == "oa_button":
            return OaButtonResolver(self._http)
        if source_id == "unpaywall":
            if not self._unpaywall_email:
                raise KeyError(
                    "Resolver 'unpaywall' not registered: requires unpaywall_email "
                    "passed to the factory constructor"
                )
            return UnpaywallResolver(self._http, email=self._unpaywall_email)
        raise KeyError(f"Resolver {source_id!r} is not registered")

    def known_sources(self) -> tuple[str, ...]:
        """Return every resolver identifier the factory can build."""
        sources: list[str] = ["oa_button"]
        if self._unpaywall_email:
            sources.append("unpaywall")
        return tuple(sources)
