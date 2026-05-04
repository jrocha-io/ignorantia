"""Unit tests for ``SearchOrchestrator``.

Orchestration is the domain logic that asks every requested adapter for
its results and aggregates the responses. The orchestrator is unaware of
how adapters connect to the network — it only sees
:class:`~ignorantia.domain.search.ports.adapter_port.AdapterPort`.
"""

from __future__ import annotations

import pytest

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.services.search_orchestrator import SearchOrchestrator
from ignorantia.domain.search.value_objects import Method, Tier


class _FakeAdapter(AdapterPort):
    """Test double that returns a configurable :class:`SearchResult`."""

    def __init__(
        self, source_id: str, items: tuple[FetchedItem, ...], tier: Tier = Tier.TIER1
    ) -> None:
        self._source_id = source_id
        self._tier = tier
        self._items = items

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def source_tier(self) -> Tier:
        return self._tier

    def fetch(self, query: SearchQuery) -> SearchResult:
        return SearchResult(
            source=self._source_id,
            source_tier=self._tier,
            method=Method.MOCK,
            query=query,
            items=self._items,
        )


class _ExplodingAdapter(AdapterPort):
    """Adapter that raises on ``fetch`` to verify error propagation."""

    source_id = "boom"
    source_tier = Tier.TIER1

    def fetch(self, query: SearchQuery) -> SearchResult:
        raise RuntimeError("boom")


class _StubFactory(AdapterFactoryPort):
    """Test double mapping ``source_id`` to a pre-built adapter."""

    def __init__(self, adapters: dict[str, AdapterPort]) -> None:
        self._adapters = adapters

    def create(self, source_id: str) -> AdapterPort:
        return self._adapters[source_id]


def _item(title: str, doi: str | None = None) -> FetchedItem:
    return FetchedItem(title=title, source_tier=Tier.TIER1, doi=doi)


class TestRunReturnsResultsByAdapterId:
    def test_empty_source_list_returns_empty_dict(self) -> None:
        orch = SearchOrchestrator(_StubFactory({}))
        assert orch.run(SearchQuery(text="x"), ()) == {}

    def test_single_source_returns_one_entry(self) -> None:
        adapter = _FakeAdapter("arxiv", (_item("A"),))
        orch = SearchOrchestrator(_StubFactory({"arxiv": adapter}))

        results = orch.run(SearchQuery(text="x"), ("arxiv",))
        assert set(results) == {"arxiv"}
        assert results["arxiv"].items == (_item("A"),)

    def test_multiple_sources_each_get_own_entry(self) -> None:
        adapters = {
            "arxiv": _FakeAdapter("arxiv", (_item("A", "10.1234/a"),)),
            "doaj": _FakeAdapter("doaj", (_item("B", "10.1234/b"),)),
        }
        orch = SearchOrchestrator(_StubFactory(adapters))

        results = orch.run(SearchQuery(text="x"), ("arxiv", "doaj"))
        assert set(results) == {"arxiv", "doaj"}


class TestDeduplicatedItems:
    def test_deduplicated_items_collapses_duplicates_across_sources(self) -> None:
        a_arxiv = _item("Same paper", doi="10.1234/x")
        a_doaj = _item("Same paper", doi="10.1234/x")
        adapters = {
            "arxiv": _FakeAdapter("arxiv", (a_arxiv,)),
            "doaj": _FakeAdapter("doaj", (a_doaj,)),
        }
        orch = SearchOrchestrator(_StubFactory(adapters))

        results = orch.run(SearchQuery(text="x"), ("arxiv", "doaj"))
        deduped = orch.deduplicated_items(results)
        assert deduped == (a_arxiv,)

    def test_deduplicated_items_preserves_distinct_records(self) -> None:
        a = _item("A", doi="10.1234/a")
        b = _item("B", doi="10.1234/b")
        adapters = {
            "arxiv": _FakeAdapter("arxiv", (a,)),
            "doaj": _FakeAdapter("doaj", (b,)),
        }
        orch = SearchOrchestrator(_StubFactory(adapters))

        results = orch.run(SearchQuery(text="x"), ("arxiv", "doaj"))
        deduped = orch.deduplicated_items(results)
        assert set(deduped) == {a, b}


class TestErrorPropagation:
    def test_adapter_exception_propagates_by_default(self) -> None:
        orch = SearchOrchestrator(_StubFactory({"boom": _ExplodingAdapter()}))
        with pytest.raises(RuntimeError, match="boom"):
            orch.run(SearchQuery(text="x"), ("boom",))
