"""Unit tests for :class:`SearchForStudiesUseCase`.

The use case is exercised against a real :class:`SearchOrchestrator`
wired with a stub :class:`AdapterFactoryPort` whose adapters return
canned :class:`SearchResult` instances. The orchestrator's resilience
(network errors → ``Method.REAL_ERROR``) is exercised by an adapter
that raises a :class:`URLError`.
"""

from __future__ import annotations

from urllib.error import URLError

import pytest

from ignorantia.application.dtos import (
    FetchedItemDto,
    SearchForStudiesCommand,
    SearchForStudiesResult,
)
from ignorantia.application.use_cases.search_for_studies import (
    SearchForStudiesUseCase,
)
from ignorantia.domain.search.entities import (
    FetchedItem,
    SearchQuery,
    SearchResult,
)
from ignorantia.domain.search.ports.adapter_factory_port import AdapterFactoryPort
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.services.search_orchestrator import (
    SearchOrchestrator,
)
from ignorantia.domain.search.value_objects import Method, Tier

# ----------------------------------------------------------------------
# Stub adapters + factory
# ----------------------------------------------------------------------


class _StubAdapter(AdapterPort):
    def __init__(
        self,
        *,
        source_id: str,
        items: tuple[FetchedItem, ...],
        tier: Tier = Tier.TIER1,
    ) -> None:
        self._source_id = source_id
        self._items = items
        self._tier = tier

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


class _ErroringAdapter(AdapterPort):
    @property
    def source_id(self) -> str:
        return "broken"

    @property
    def source_tier(self) -> Tier:
        return Tier.TIER1

    def fetch(self, query: SearchQuery) -> SearchResult:
        raise URLError("boom")


class _StubFactory(AdapterFactoryPort):
    def __init__(self, adapters: dict[str, AdapterPort]) -> None:
        self._adapters = adapters

    def create(self, source_id: str) -> AdapterPort:
        return self._adapters[source_id]


def _item(title: str, **kwargs: object) -> FetchedItem:
    base: dict[str, object] = {"title": title, "source_tier": Tier.TIER1}
    base.update(kwargs)
    return FetchedItem(**base)  # type: ignore[arg-type]


@pytest.fixture
def factory() -> _StubFactory:
    return _StubFactory(
        {
            "arxiv": _StubAdapter(
                source_id="arxiv",
                items=(_item("Paper A", doi="10.1/a"),),
            ),
            "openalex": _StubAdapter(
                source_id="openalex",
                items=(
                    _item("Paper A", doi="10.1/a"),  # duplicate of arxiv
                    _item("Paper B", doi="10.1/b"),
                ),
            ),
            "broken": _ErroringAdapter(),
        }
    )


@pytest.fixture
def use_case(factory: _StubFactory) -> SearchForStudiesUseCase:
    return SearchForStudiesUseCase(orchestrator=SearchOrchestrator(factory))


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------


class TestSearchForStudiesUseCaseHappyPath:
    def test_execute_returns_search_for_studies_result(
        self, use_case: SearchForStudiesUseCase
    ) -> None:
        result = use_case.execute(SearchForStudiesCommand(text="q", source_ids=("arxiv",)))
        assert isinstance(result, SearchForStudiesResult)

    def test_per_source_in_command_order(self, use_case: SearchForStudiesUseCase) -> None:
        result = use_case.execute(
            SearchForStudiesCommand(text="q", source_ids=("openalex", "arxiv"))
        )
        assert tuple(s.source for s in result.per_source) == (
            "openalex",
            "arxiv",
        )

    def test_per_source_carries_method_and_tier_strings(
        self, use_case: SearchForStudiesUseCase
    ) -> None:
        result = use_case.execute(SearchForStudiesCommand(text="q", source_ids=("arxiv",)))
        assert result.per_source[0].method == "mock"
        assert result.per_source[0].source_tier == "tier1"

    def test_items_are_dtos_not_domain_entities(self, use_case: SearchForStudiesUseCase) -> None:
        result = use_case.execute(SearchForStudiesCommand(text="q", source_ids=("arxiv",)))
        for item in result.per_source[0].items:
            assert isinstance(item, FetchedItemDto)
            assert not isinstance(item, FetchedItem)


# ----------------------------------------------------------------------
# Aggregations
# ----------------------------------------------------------------------


class TestSearchForStudiesUseCaseAggregations:
    def test_n_items_total_sums_across_sources(self, use_case: SearchForStudiesUseCase) -> None:
        result = use_case.execute(
            SearchForStudiesCommand(text="q", source_ids=("arxiv", "openalex"))
        )
        # arxiv yields 1 item, openalex yields 2 → total 3 pre-dedup.
        assert result.n_items_total == 3

    def test_n_items_deduplicated_collapses_duplicates(
        self, use_case: SearchForStudiesUseCase
    ) -> None:
        # arxiv + openalex both return Paper A (DOI 10.1/a) — the
        # deduplicator collapses by DOI, leaving 2 unique items.
        result = use_case.execute(
            SearchForStudiesCommand(text="q", source_ids=("arxiv", "openalex"))
        )
        assert result.n_items_deduplicated == 2
        titles = {i.title for i in result.deduplicated_items}
        assert titles == {"Paper A", "Paper B"}

    def test_deduplicated_items_are_dtos(self, use_case: SearchForStudiesUseCase) -> None:
        result = use_case.execute(
            SearchForStudiesCommand(text="q", source_ids=("arxiv", "openalex"))
        )
        for item in result.deduplicated_items:
            assert isinstance(item, FetchedItemDto)


# ----------------------------------------------------------------------
# Error capture
# ----------------------------------------------------------------------


class TestSearchForStudiesUseCaseResilience:
    def test_network_error_is_captured_as_real_error(
        self, use_case: SearchForStudiesUseCase
    ) -> None:
        result = use_case.execute(SearchForStudiesCommand(text="q", source_ids=("arxiv", "broken")))
        broken = next(s for s in result.per_source if s.source == "broken")
        assert broken.method == "real_error"
        assert broken.items == ()

    def test_aggregate_counts_error_separately(self, use_case: SearchForStudiesUseCase) -> None:
        result = use_case.execute(
            SearchForStudiesCommand(text="q", source_ids=("arxiv", "openalex", "broken"))
        )
        assert result.n_sources_ok == 2
        assert result.n_sources_errored == 1


# ----------------------------------------------------------------------
# Year window + languages
# ----------------------------------------------------------------------


class TestSearchForStudiesUseCaseQueryTranslation:
    def test_year_window_translates_to_search_query(self, factory: _StubFactory) -> None:
        captured: list[SearchQuery] = []

        class _CapturingAdapter(AdapterPort):
            @property
            def source_id(self) -> str:
                return "capture"

            @property
            def source_tier(self) -> Tier:
                return Tier.TIER1

            def fetch(self, query: SearchQuery) -> SearchResult:
                captured.append(query)
                return SearchResult(
                    source="capture",
                    source_tier=Tier.TIER1,
                    method=Method.MOCK,
                    query=query,
                    items=(),
                )

        factory._adapters["capture"] = _CapturingAdapter()
        use_case = SearchForStudiesUseCase(orchestrator=SearchOrchestrator(factory))
        use_case.execute(
            SearchForStudiesCommand(
                text="q",
                source_ids=("capture",),
                year_start=2020,
                year_end=2024,
                languages=("en", "pt"),
            )
        )
        assert captured[0].text == "q"
        assert captured[0].year_start == 2020
        assert captured[0].year_end == 2024
        assert captured[0].languages == ("en", "pt")
