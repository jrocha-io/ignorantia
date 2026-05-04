"""``AdapterFactoryPort`` — composes adapters by their ``source_id``.

The application layer (use cases) and the orchestrator depend on this
abstract factory. Concrete factories live in
``ignorantia.infrastructure.search`` and decide which class to instantiate
for each source identifier.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ignorantia.domain.search.ports.adapter_port import AdapterPort


class AdapterFactoryPort(ABC):
    """Abstract factory for :class:`AdapterPort` instances."""

    @abstractmethod
    def create(self, source_id: str) -> AdapterPort:
        """Return an adapter for ``source_id`` or raise :class:`KeyError`."""
