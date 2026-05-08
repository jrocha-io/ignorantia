"""Unit tests for ``AdapterFactoryPort`` and ``OrchestratorPort`` ABCs."""

from __future__ import annotations

import pytest

from ignorantia.domain.search.entities import SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.ports.orchestrator_port import OrchestratorPort
from ignorantia.domain.search.value_objects import Method, Tier


class _StubAdapter(AdapterPort):
    source_id = "stub"
    source_tier = Tier.TIER1

    def fetch(self, query: SearchQuery) -> SearchResult:
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.MOCK,
            query=query,
        )


class TestAdapterFactoryPortIsAbstract:
    def test_cannot_instantiate_base_class(self) -> None:
        with pytest.raises(TypeError):
            AdapterFactoryPort()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        class Concrete(AdapterFactoryPort):
            def create(self, source_id: str) -> AdapterPort:
                return _StubAdapter()

        assert isinstance(Concrete(), AdapterFactoryPort)


class TestOrchestratorPortIsAbstract:
    def test_cannot_instantiate_base_class(self) -> None:
        with pytest.raises(TypeError):
            OrchestratorPort()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        class Concrete(OrchestratorPort):
            def run(
                self, query: SearchQuery, source_ids: tuple[str, ...]
            ) -> dict[str, SearchResult]:
                return {}

        assert isinstance(Concrete(), OrchestratorPort)
