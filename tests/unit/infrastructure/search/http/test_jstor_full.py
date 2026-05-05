"""Unit tests for :class:`JstorFullAdapter` (paywall stub)."""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.jstor_full import JstorFullAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for JSTOR full stub")


class TestMetadata:
    def test_source_id(self) -> None:
        assert JstorFullAdapter(_NoopHttp()).source_id == "jstor_full"

    def test_source_tier(self) -> None:
        assert JstorFullAdapter(_NoopHttp()).source_tier is Tier.TIER2


class TestFetch:
    def test_no_credentials_returns_real_error_empty(self) -> None:
        result = JstorFullAdapter(_NoopHttp()).fetch(SearchQuery(text="anthropology"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
