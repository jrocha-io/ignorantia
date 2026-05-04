"""``AdapterFactory`` — concrete :class:`AdapterFactoryPort` implementation.

This is the *composition root* for the search bounded context. Every
adapter the system can use is registered exactly once in
:attr:`_REGISTRY`; adding a new database in F3 means adding a new entry
here and nothing else (Open/Closed).
"""

from __future__ import annotations

from collections.abc import Callable

from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.infrastructure.http_client import HttpClient
from ignorantia.infrastructure.search.http.arxiv import ArxivAdapter

_AdapterBuilder = Callable[[HttpClient], AdapterPort]


_REGISTRY: dict[str, _AdapterBuilder] = {
    "arxiv": ArxivAdapter,
}


class AdapterFactory(AdapterFactoryPort):
    """Build adapters on demand, sharing a single :class:`HttpClient`."""

    def __init__(self, http: HttpClient) -> None:
        """Wire the factory to the shared HTTP client."""
        self._http = http

    def create(self, source_id: str) -> AdapterPort:
        """Return a fresh adapter for ``source_id``.

        Raises:
            KeyError: when ``source_id`` is not registered.
        """
        try:
            builder = _REGISTRY[source_id]
        except KeyError as exc:
            raise KeyError(f"No adapter registered for source: {source_id!r}") from exc
        return builder(self._http)

    @staticmethod
    def known_sources() -> tuple[str, ...]:
        """Return every registered source identifier in registration order."""
        return tuple(_REGISTRY)
