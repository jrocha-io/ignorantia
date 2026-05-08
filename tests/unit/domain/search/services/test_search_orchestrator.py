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
    def test_non_network_exception_propagates(self) -> None:
        # RuntimeError, KeyError, ValueError etc. are programming bugs or
        # contract violations — they must surface, not be swallowed.
        orch = SearchOrchestrator(_StubFactory({"boom": _ExplodingAdapter()}))
        with pytest.raises(RuntimeError, match="boom"):
            orch.run(SearchQuery(text="x"), ("boom",))


class _NetworkFailingAdapter(AdapterPort):
    """Adapter whose ``fetch`` raises a configurable network-class error."""

    def __init__(self, source_id: str, error: BaseException, tier: Tier = Tier.TIER1) -> None:
        self._source_id = source_id
        self._error = error
        self._tier = tier

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def source_tier(self) -> Tier:
        return self._tier

    def fetch(self, query: SearchQuery) -> SearchResult:
        del query
        raise self._error


class TestNetworkErrorResilience:
    def _http_error(self, status: int = 503) -> Exception:
        from urllib.error import HTTPError

        return HTTPError("https://x/", status, "boom", hdrs=None, fp=None)  # type: ignore[arg-type]

    def test_http_error_yields_real_error_result(self) -> None:
        from ignorantia.domain.search.value_objects import Method as _Method

        adapter = _NetworkFailingAdapter("flaky", self._http_error(503), tier=Tier.TIER1)
        orch = SearchOrchestrator(_StubFactory({"flaky": adapter}))
        result = orch.run(SearchQuery(text="x"), ("flaky",))["flaky"]
        assert result.method is _Method.REAL_ERROR
        assert result.items == ()
        assert result.source == "flaky"
        assert result.source_tier is Tier.TIER1

    def test_url_error_yields_real_error_result(self) -> None:
        from urllib.error import URLError

        from ignorantia.domain.search.value_objects import Method as _Method

        adapter = _NetworkFailingAdapter("dns-broken", URLError("nodename nor servname"))
        orch = SearchOrchestrator(_StubFactory({"dns-broken": adapter}))
        result = orch.run(SearchQuery(text="x"), ("dns-broken",))["dns-broken"]
        assert result.method is _Method.REAL_ERROR

    def test_timeout_error_yields_real_error_result(self) -> None:
        from ignorantia.domain.search.value_objects import Method as _Method

        adapter = _NetworkFailingAdapter("slow", TimeoutError("timed out"))
        orch = SearchOrchestrator(_StubFactory({"slow": adapter}))
        result = orch.run(SearchQuery(text="x"), ("slow",))["slow"]
        assert result.method is _Method.REAL_ERROR

    def test_one_failure_does_not_break_other_adapters(self) -> None:
        # The whole point: a single flaky source must not abort the run.
        ok_adapter = _FakeAdapter("arxiv", (_item("A"),))
        flaky = _NetworkFailingAdapter("flaky", self._http_error(429))
        adapters: dict[str, AdapterPort] = {"arxiv": ok_adapter, "flaky": flaky}
        orch = SearchOrchestrator(_StubFactory(adapters))

        results = orch.run(SearchQuery(text="x"), ("arxiv", "flaky"))
        assert set(results) == {"arxiv", "flaky"}
        assert results["arxiv"].items == (_item("A"),)
        assert results["flaky"].items == ()

    def test_query_is_attached_to_error_result(self) -> None:
        adapter = _NetworkFailingAdapter("flaky", self._http_error(500))
        orch = SearchOrchestrator(_StubFactory({"flaky": adapter}))
        query = SearchQuery(text="probe", year_start=2020, year_end=2024)
        result = orch.run(query, ("flaky",))["flaky"]
        assert result.query is query
