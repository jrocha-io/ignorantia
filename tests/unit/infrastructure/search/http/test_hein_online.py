"""Unit tests for :class:`HeinOnlineAdapter` (paywall stub)."""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.hein_online import HeinOnlineAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for HeinOnline stub")


class TestMetadata:
    def test_source_id(self) -> None:
        assert HeinOnlineAdapter(_NoopHttp()).source_id == "hein_online"

    def test_source_tier(self) -> None:
        assert HeinOnlineAdapter(_NoopHttp()).source_tier is Tier.TIER2


class TestFetch:
    def test_no_credentials_returns_real_error_empty(self) -> None:
        result = HeinOnlineAdapter(_NoopHttp()).fetch(SearchQuery(text="due process"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
