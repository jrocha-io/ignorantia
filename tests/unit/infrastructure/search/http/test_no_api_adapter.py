"""Unit tests for the :class:`_NoApiAdapter` base class.

The 9 stub adapters that share this base are exercised by the
contract test plus their own per-source identity tests. This file
nails down the behavioural contract of the base itself (HTTP must not
be touched, fetch always returns ``REAL_ERROR`` empty) so a future
refactor cannot silently change it.
"""

from __future__ import annotations

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http._no_api import _NoApiAdapter


class _NoopHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for no-api adapters")

    def post(self, url: str, *, data: bytes, headers: object | None = None) -> bytes:
        del url, data, headers
        raise AssertionError("HTTP must not be called for no-api adapters")


class _Concrete(_NoApiAdapter):
    source_id = "fixture"
    source_tier = Tier.TIER1


class TestBehaviour:
    def test_fetch_returns_real_error(self) -> None:
        result = _Concrete(_NoopHttp()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR

    def test_fetch_returns_empty_items(self) -> None:
        result = _Concrete(_NoopHttp()).fetch(SearchQuery(text="x"))
        assert result.items == ()

    def test_fetch_propagates_query(self) -> None:
        q = SearchQuery(text="probe", year_start=2020, year_end=2024)
        assert _Concrete(_NoopHttp()).fetch(q).query is q

    def test_fetch_propagates_source_metadata(self) -> None:
        result = _Concrete(_NoopHttp()).fetch(SearchQuery(text="x"))
        assert result.source == "fixture"
        assert result.source_tier is Tier.TIER1

    def test_http_client_never_invoked(self) -> None:
        # If fetch() ever calls http.get/post, _NoopHttp asserts.
        _Concrete(_NoopHttp()).fetch(SearchQuery(text="x"))
