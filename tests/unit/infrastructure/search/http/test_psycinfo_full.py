"""Unit tests for :class:`PsycInfoFullAdapter` (paywall stub)."""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.psycinfo_full import PsycInfoFullAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for PsycInfo stub")


class TestMetadata:
    def test_source_id(self) -> None:
        assert PsycInfoFullAdapter(_NoopHttp()).source_id == "psycinfo_full"

    def test_source_tier(self) -> None:
        assert PsycInfoFullAdapter(_NoopHttp()).source_tier is Tier.TIER2


class TestFetch:
    def test_no_credentials_returns_real_error_empty(self) -> None:
        result = PsycInfoFullAdapter(_NoopHttp()).fetch(SearchQuery(text="anxiety"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
