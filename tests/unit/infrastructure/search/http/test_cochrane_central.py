"""Unit tests for :class:`CochraneCentralAdapter` (no public API stub)."""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.cochrane_central import CochraneCentralAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for Cochrane stub")


class TestMetadata:
    def test_source_id(self) -> None:
        assert CochraneCentralAdapter(_NoopHttp()).source_id == "cochrane_central"

    def test_source_tier(self) -> None:
        assert CochraneCentralAdapter(_NoopHttp()).source_tier is Tier.TIER1


class TestFetch:
    def test_fetch_returns_real_error_empty(self) -> None:
        result = CochraneCentralAdapter(_NoopHttp()).fetch(SearchQuery(text="rct"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
