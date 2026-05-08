"""Unit tests for ``AdapterPort`` — the contract every search adapter must honour.

These tests describe what a *valid* adapter must expose. Concrete adapters
(arxiv, crossref, ...) live in ``ignorantia.infrastructure.search`` and
must satisfy this contract.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier


class _CompleteAdapter(AdapterPort):
    """Minimal complete subclass, used to verify concrete behaviour."""

    source_id = "stub"
    source_tier = Tier.TIER1

    def fetch(self, query: SearchQuery) -> SearchResult:
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.MOCK,
            query=query,
            items=(FetchedItem(title="x", source_tier=self.source_tier),),
        )


class _NoSourceId(AdapterPort):
    """Subclass that forgets ``source_id``."""

    source_tier = Tier.TIER1

    def fetch(self, query: SearchQuery) -> SearchResult:  # pragma: no cover
        raise NotImplementedError


class _NoFetch(AdapterPort):
    """Subclass that forgets to implement ``fetch``."""

    source_id = "stub"
    source_tier = Tier.TIER1


class TestAdapterPortIsAbstract:
    """The base class enforces its abstract surface."""

    def test_cannot_instantiate_base_class(self) -> None:
        with pytest.raises(TypeError):
            AdapterPort()  # type: ignore[abstract]

    def test_cannot_instantiate_subclass_missing_source_id(self) -> None:
        with pytest.raises(TypeError):
            _NoSourceId()  # type: ignore[abstract]

    def test_cannot_instantiate_subclass_missing_fetch(self) -> None:
        with pytest.raises(TypeError):
            _NoFetch()  # type: ignore[abstract]

    def test_complete_subclass_can_be_instantiated(self) -> None:
        adapter = _CompleteAdapter()
        assert isinstance(adapter, AdapterPort)


class TestAdapterPortContract:
    """A complete adapter exposes the expected metadata and ``fetch`` shape."""

    def test_exposes_source_id(self) -> None:
        assert _CompleteAdapter().source_id == "stub"

    def test_exposes_source_tier(self) -> None:
        assert _CompleteAdapter().source_tier is Tier.TIER1

    def test_fetch_returns_search_result(self) -> None:
        result = _CompleteAdapter().fetch(SearchQuery(text="x"))
        assert isinstance(result, SearchResult)

    def test_fetch_result_has_matching_source_id(self) -> None:
        adapter = _CompleteAdapter()
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.source == adapter.source_id

    def test_fetch_result_has_matching_source_tier(self) -> None:
        adapter = _CompleteAdapter()
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.source_tier is adapter.source_tier
