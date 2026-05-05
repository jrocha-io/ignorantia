"""Unit tests for :class:`CinahlFullAdapter` (paywall stub)."""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.cinahl_full import CinahlFullAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for CINAHL stub")


class TestMetadata:
    def test_source_id(self) -> None:
        assert CinahlFullAdapter(_NoopHttp()).source_id == "cinahl_full"

    def test_source_tier(self) -> None:
        assert CinahlFullAdapter(_NoopHttp()).source_tier is Tier.TIER2


class TestFetch:
    def test_no_credentials_returns_real_error_empty(self) -> None:
        result = CinahlFullAdapter(_NoopHttp()).fetch(SearchQuery(text="nursing"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
