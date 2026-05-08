"""Unit tests for ``DeduplicatorService``.

The deduplicator is a stateless domain service that collapses identical
records returned by different adapters. The contract is deliberately
narrow: identity is decided by DOI when present, otherwise by a
normalised title.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import FetchedItem
from ignorantia.domain.search.services.deduplicator import DeduplicatorService
from ignorantia.domain.search.value_objects import Tier


def _item(title: str, doi: str | None = None) -> FetchedItem:
    return FetchedItem(title=title, source_tier=Tier.TIER1, doi=doi)


class TestEmptyAndTrivialInputs:
    def test_empty_input_returns_empty_tuple(self) -> None:
        assert DeduplicatorService.deduplicate(()) == ()

    def test_single_item_is_passed_through(self) -> None:
        item = _item("A")
        assert DeduplicatorService.deduplicate([item]) == (item,)

    def test_distinct_items_are_all_kept(self) -> None:
        a, b = _item("A", doi="10.1234/a"), _item("B", doi="10.1234/b")
        assert DeduplicatorService.deduplicate([a, b]) == (a, b)


class TestDoiBasedDeduplication:
    def test_same_doi_is_deduplicated_keeping_first(self) -> None:
        a = _item("Title 1", doi="10.1234/x")
        b = _item("Title 2", doi="10.1234/x")
        assert DeduplicatorService.deduplicate([a, b]) == (a,)

    def test_doi_match_is_case_insensitive(self) -> None:
        a = _item("A", doi="10.1234/X")
        b = _item("B", doi="10.1234/x")
        assert DeduplicatorService.deduplicate([a, b]) == (a,)

    def test_different_dois_with_same_title_are_both_kept(self) -> None:
        a = _item("Same title", doi="10.1234/a")
        b = _item("Same title", doi="10.1234/b")
        assert DeduplicatorService.deduplicate([a, b]) == (a, b)


class TestTitleBasedDeduplication:
    def test_no_doi_same_title_is_deduplicated(self) -> None:
        a = _item("Letramento digital de idosos")
        b = _item("Letramento digital de idosos")
        assert DeduplicatorService.deduplicate([a, b]) == (a,)

    def test_title_normalisation_is_case_and_whitespace_insensitive(self) -> None:
        a = _item("Letramento Digital de Idosos")
        b = _item("  letramento  digital  de  idosos  ")
        assert DeduplicatorService.deduplicate([a, b]) == (a,)

    def test_doi_item_blocks_no_doi_item_with_same_title(self) -> None:
        with_doi = _item("Foo", doi="10.1234/x")
        without_doi = _item("Foo")
        assert DeduplicatorService.deduplicate([with_doi, without_doi]) == (with_doi,)

    def test_no_doi_item_blocks_doi_item_with_same_title(self) -> None:
        without_doi = _item("Foo")
        with_doi = _item("Foo", doi="10.1234/x")
        assert DeduplicatorService.deduplicate([without_doi, with_doi]) == (without_doi,)


class TestOrderPreservation:
    def test_first_seen_order_is_preserved(self) -> None:
        a = _item("A", doi="10.1234/a")
        b = _item("B", doi="10.1234/b")
        c = _item("C", doi="10.1234/c")
        assert DeduplicatorService.deduplicate([c, a, b, a]) == (c, a, b)
