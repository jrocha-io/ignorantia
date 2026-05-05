"""``OaResolverChain`` — Composite of :class:`OaResolverPort`.

Wraps a tuple of resolvers and tries them in priority order; returns
the first :class:`OaLocation` produced. Network errors from one
resolver are swallowed so the chain continues to the next; a
``ValueError`` from a resolver is *not* swallowed because per the
:class:`OaResolverPort` docstring an invalid DOI is a caller-side
contract violation that must surface.

The chain itself implements :class:`OaResolverPort`, so a chain can
be passed wherever a single resolver is expected — e.g. nested
chains, or a chain wired into the F6 application layer.
"""

from __future__ import annotations

from urllib.error import HTTPError, URLError

from ignorantia.domain.search.entities import OaLocation
from ignorantia.domain.search.ports.oa_resolver_port import OaResolverPort

_NETWORK_ERRORS: tuple[type[BaseException], ...] = (HTTPError, URLError, TimeoutError)


class OaResolverChain(OaResolverPort):
    """Try a sequence of resolvers in order; return the first hit."""

    def __init__(self, resolvers: tuple[OaResolverPort, ...]) -> None:
        """Wire the chain to its priority-ordered members."""
        self._resolvers = resolvers

    @property
    def source_id(self) -> str:
        """Stable identifier for telemetry / logging."""
        return "chain"

    def resolve(self, doi: str) -> OaLocation | None:
        """Return the first :class:`OaLocation` any member finds."""
        for resolver in self._resolvers:
            try:
                location = resolver.resolve(doi)
            except _NETWORK_ERRORS:
                continue
            if location is not None:
                return location
        return None
