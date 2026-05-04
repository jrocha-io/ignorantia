"""Unit tests for search bounded context entities.

These tests pin the contract that the 62 adapters will be migrated to in
F3 (issue #4). ``FetchedItem`` is the canonical bibliographic record
(D4 from audit #5), ``SearchQuery`` describes a query, and
``SearchResult`` aggregates a single adapter run.
"""

from __future__ import annotations

import dataclasses

import pytest

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.value_objects import Method, Tier


def _minimal_item(**overrides: object) -> FetchedItem:
    payload = {"title": "Letramento digital de idosos", "source_tier": Tier.TIER1}
    payload.update(overrides)
    return FetchedItem(**payload)  # type: ignore[arg-type]


class TestFetchedItemConstruction:
    """Required and default fields."""

    def test_minimal_fetched_item_only_requires_title_and_source_tier(self) -> None:
        item = FetchedItem(title="A study", source_tier=Tier.TIER1)
        assert item.title == "A study"
        assert item.source_tier is Tier.TIER1

    def test_authors_default_is_empty_tuple(self) -> None:
        item = _minimal_item()
        assert item.authors == ()

    def test_optional_id_fields_default_to_none(self) -> None:
        item = _minimal_item()
        assert item.doi is None
        assert item.issn is None
        assert item.isbn is None
        assert item.year is None
        assert item.venue is None
        assert item.url is None
        assert item.url_for_pdf is None
        assert item.publication_type is None

    def test_string_fields_have_safe_defaults(self) -> None:
        item = _minimal_item()
        assert item.abstract == ""
        assert item.language == "en"
        assert item.is_oa is False


class TestFetchedItemImmutability:
    """Per DDD, value objects and entities used as values are immutable."""

    def test_authors_is_a_tuple(self) -> None:
        item = _minimal_item(authors=("Silva, A.", "Pereira, B."))
        assert isinstance(item.authors, tuple)

    def test_assignment_to_frozen_field_raises(self) -> None:
        item = _minimal_item()
        with pytest.raises(dataclasses.FrozenInstanceError):
            item.title = "mutated"  # type: ignore[misc]


class TestFetchedItemEquality:
    """Equality is structural — two items with identical fields are equal."""

    def test_equal_items_compare_equal(self) -> None:
        a = _minimal_item(doi="10.1/x", year=2024)
        b = _minimal_item(doi="10.1/x", year=2024)
        assert a == b

    def test_different_titles_compare_unequal(self) -> None:
        a = _minimal_item(title="A")
        b = _minimal_item(title="B")
        assert a != b


class TestSearchQueryConstruction:
    """``SearchQuery`` describes the search a caller wants to run."""

    def test_minimal_query_only_requires_text(self) -> None:
        q = SearchQuery(text="letramento digital")
        assert q.text == "letramento digital"

    def test_year_range_defaults_to_none(self) -> None:
        q = SearchQuery(text="x")
        assert q.year_start is None
        assert q.year_end is None

    def test_languages_default_is_empty_tuple(self) -> None:
        q = SearchQuery(text="x")
        assert q.languages == ()

    def test_year_range_accepts_explicit_window(self) -> None:
        q = SearchQuery(text="x", year_start=2018, year_end=2024)
        assert q.year_start == 2018
        assert q.year_end == 2024

    def test_query_is_immutable(self) -> None:
        q = SearchQuery(text="x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            q.text = "y"  # type: ignore[misc]

    def test_year_end_before_year_start_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="year_end"):
            SearchQuery(text="x", year_start=2024, year_end=2018)


class TestSearchResultConstruction:
    """``SearchResult`` aggregates one adapter's response to one query."""

    def test_minimal_result_requires_source_tier_method_query_and_items(self) -> None:
        q = SearchQuery(text="x")
        result = SearchResult(
            source="arxiv",
            source_tier=Tier.TIER1,
            method=Method.MOCK,
            query=q,
            items=(),
        )
        assert result.source == "arxiv"
        assert result.source_tier is Tier.TIER1
        assert result.method is Method.MOCK
        assert result.query is q
        assert result.items == ()

    def test_total_results_defaults_to_len_items(self) -> None:
        q = SearchQuery(text="x")
        items = (_minimal_item(), _minimal_item(title="B"))
        result = SearchResult(
            source="arxiv",
            source_tier=Tier.TIER1,
            method=Method.REAL,
            query=q,
            items=items,
        )
        assert result.total_results == 2

    def test_total_results_can_exceed_items_when_results_are_truncated(self) -> None:
        q = SearchQuery(text="x")
        items = (_minimal_item(),)
        result = SearchResult(
            source="arxiv",
            source_tier=Tier.TIER1,
            method=Method.REAL,
            query=q,
            items=items,
            total_results=12345,
        )
        assert result.total_results == 12345

    def test_search_result_is_immutable(self) -> None:
        q = SearchQuery(text="x")
        result = SearchResult(
            source="arxiv",
            source_tier=Tier.TIER1,
            method=Method.MOCK,
            query=q,
            items=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.source = "x"  # type: ignore[misc]
