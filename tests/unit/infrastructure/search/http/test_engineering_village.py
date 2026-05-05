"""Unit tests for :class:`EngineeringVillageAdapter`."""

from __future__ import annotations

import pytest

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.engineering_village import (
    EngineeringVillageAdapter,
)


class _RecordingAdapter(AdapterPort):
    """Test double capturing the ``SearchQuery`` it receives."""

    source_id = "stub-delegate"
    source_tier = Tier.TIER0

    def __init__(
        self,
        items: tuple[FetchedItem, ...] = (),
        *,
        method: Method = Method.REAL,
        total_results: int | None = None,
    ) -> None:
        self.received: list[SearchQuery] = []
        self._items = items
        self._method = method
        self._total_results = total_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        self.received.append(query)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=self._method,
            query=query,
            items=self._items,
            total_results=self._total_results,
        )


def _item(title: str = "A study", *, tier: Tier = Tier.TIER0) -> FetchedItem:
    return FetchedItem(title=title, source_tier=tier, doi="10.1/x")


class TestMetadata:
    def test_source_id(self) -> None:
        adapter = EngineeringVillageAdapter(_RecordingAdapter())
        assert adapter.source_id == "engineering_village"

    def test_source_tier(self) -> None:
        adapter = EngineeringVillageAdapter(_RecordingAdapter())
        assert adapter.source_tier is Tier.TIER1


class TestQueryEnrichment:
    def test_default_enriches_with_engineering(self) -> None:
        delegate = _RecordingAdapter()
        EngineeringVillageAdapter(delegate).fetch(SearchQuery(text="resilience"))
        assert delegate.received[0].text == "resilience engineering"

    def test_subdiscipline_replaces_default_term(self) -> None:
        delegate = _RecordingAdapter()
        EngineeringVillageAdapter(delegate, subdiscipline="civil").fetch(
            SearchQuery(text="resilience")
        )
        assert delegate.received[0].text == "resilience civil"

    def test_year_window_passed_through(self) -> None:
        delegate = _RecordingAdapter()
        query = SearchQuery(text="x", year_start=2020, year_end=2024)
        EngineeringVillageAdapter(delegate).fetch(query)
        forwarded = delegate.received[0]
        assert forwarded.year_start == 2020
        assert forwarded.year_end == 2024

    def test_languages_passed_through(self) -> None:
        delegate = _RecordingAdapter()
        query = SearchQuery(text="x", languages=("en", "pt"))
        EngineeringVillageAdapter(delegate).fetch(query)
        assert delegate.received[0].languages == ("en", "pt")

    def test_unknown_subdiscipline_rejected(self) -> None:
        with pytest.raises(ValueError, match="subdiscipline"):
            EngineeringVillageAdapter(_RecordingAdapter(), subdiscipline="nonsense")

    @pytest.mark.parametrize(
        "subdiscipline",
        ["mechanical", "civil", "chemical", "electrical", "materials", "environmental"],
    )
    def test_known_subdisciplines_accepted(self, subdiscipline: str) -> None:
        EngineeringVillageAdapter(_RecordingAdapter(), subdiscipline=subdiscipline)


class TestResultIdentity:
    def test_source_rebranded(self) -> None:
        adapter = EngineeringVillageAdapter(_RecordingAdapter())
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.source == "engineering_village"

    def test_source_tier_is_tier1(self) -> None:
        adapter = EngineeringVillageAdapter(_RecordingAdapter())
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.source_tier is Tier.TIER1

    def test_original_query_preserved_in_result(self) -> None:
        adapter = EngineeringVillageAdapter(_RecordingAdapter())
        original = SearchQuery(text="resilience")
        result = adapter.fetch(original)
        assert result.query is original

    def test_method_preserved_from_delegate(self) -> None:
        delegate = _RecordingAdapter(method=Method.REAL_PARTIAL)
        result = EngineeringVillageAdapter(delegate).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_PARTIAL


class TestItemRetagging:
    def test_items_are_retagged_to_tier1(self) -> None:
        items = (_item(tier=Tier.TIER0), _item(tier=Tier.TIER0))
        delegate = _RecordingAdapter(items=items)
        result = EngineeringVillageAdapter(delegate).fetch(SearchQuery(text="x"))
        assert all(it.source_tier is Tier.TIER1 for it in result.items)

    def test_items_already_tier1_are_unchanged_identity(self) -> None:
        items = (_item(tier=Tier.TIER1),)
        delegate = _RecordingAdapter(items=items)
        result = EngineeringVillageAdapter(delegate).fetch(SearchQuery(text="x"))
        assert result.items[0] is items[0]

    def test_other_item_fields_preserved(self) -> None:
        original = FetchedItem(
            title="A", source_tier=Tier.TIER0, doi="10.1/y", year=2023, is_oa=True
        )
        delegate = _RecordingAdapter(items=(original,))
        result = EngineeringVillageAdapter(delegate).fetch(SearchQuery(text="x"))
        retagged = result.items[0]
        assert retagged.title == original.title
        assert retagged.doi == original.doi
        assert retagged.year == original.year
        assert retagged.is_oa is True
