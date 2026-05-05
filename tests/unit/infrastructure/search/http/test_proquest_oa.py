"""Unit tests for :class:`ProquestOaAdapter` (no public API stub)."""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.proquest_oa import ProquestOaAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for ProQuest OA stub")


class TestMetadata:
    def test_source_id(self) -> None:
        assert ProquestOaAdapter(_NoopHttp()).source_id == "proquest_oa"

    def test_source_tier(self) -> None:
        assert ProquestOaAdapter(_NoopHttp()).source_tier is Tier.TIER1


class TestFetch:
    def test_fetch_returns_real_error_empty(self) -> None:
        result = ProquestOaAdapter(_NoopHttp()).fetch(SearchQuery(text="thesis"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
