"""Unit tests for ``_PaywallAdapter`` cascade behaviour.

The cascade is exercised through a minimal stub subclass so the tests
focus on the cascade logic rather than on any real publisher API. The
fallback-markdown generation that v2 wrapped into the cascade lives in a
separate service (introduced in F5); the adapter only signals
``Method.REAL_ERROR`` when neither key nor proxy succeed.
"""

from __future__ import annotations

from urllib.error import HTTPError, URLError

import pytest

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class _StubAdapter(_PaywallAdapter):
    """Concrete subclass parametrised by per-test attempt outcomes."""

    source_id = "stub"
    source_tier = Tier.TIER2

    def __init__(
        self,
        *,
        api_key: str | None = None,
        proxy_host: str | None = None,
        key_outcome: object = "skip",
        proxy_outcome: object = "skip",
    ) -> None:
        super().__init__(
            http=None,  # type: ignore[arg-type]
            api_key=api_key,
            proxy_host=proxy_host,
        )
        self._key_outcome = key_outcome
        self._proxy_outcome = proxy_outcome
        self.calls: list[str] = []

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        self.calls.append("key")
        return _resolve(self._key_outcome)

    def _proxy_search(self, query: SearchQuery) -> tuple[FetchedItem, ...] | None:
        self.calls.append("proxy")
        outcome = self._proxy_outcome
        if outcome == "skip":
            return None
        return _resolve(outcome)


def _resolve(outcome: object) -> tuple[FetchedItem, ...]:
    if isinstance(outcome, BaseException):
        raise outcome
    if isinstance(outcome, tuple):
        return outcome
    raise RuntimeError(f"unexpected outcome: {outcome!r}")


def _item(title: str = "A study") -> FetchedItem:
    return FetchedItem(title=title, source_tier=Tier.TIER2)


class TestNoCredentialsCascade:
    def test_no_key_no_proxy_returns_real_error(self) -> None:
        adapter = _StubAdapter()
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
        assert adapter.calls == []


class TestKeySucceeds:
    def test_key_returns_items_method_is_real(self) -> None:
        adapter = _StubAdapter(api_key="K", key_outcome=(_item("a"),))
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert len(result.items) == 1
        assert adapter.calls == ["key"]

    def test_key_returns_empty_does_not_fall_through(self) -> None:
        adapter = _StubAdapter(api_key="K", key_outcome=(), proxy_host="P")
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert result.items == ()
        assert adapter.calls == ["key"]


class TestKeyFailsCascadesToProxy:
    def test_key_http_error_falls_to_proxy(self) -> None:
        adapter = _StubAdapter(
            api_key="K",
            key_outcome=HTTPError("u", 401, "unauth", hdrs=None, fp=None),  # type: ignore[arg-type]
            proxy_host="P",
            proxy_outcome=(_item("a"),),
        )
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_PARTIAL
        assert adapter.calls == ["key", "proxy"]

    def test_key_url_error_falls_to_proxy(self) -> None:
        adapter = _StubAdapter(
            api_key="K",
            key_outcome=URLError("dns failed"),
            proxy_host="P",
            proxy_outcome=(_item("a"),),
        )
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_PARTIAL


class TestKeyAndProxyBothFail:
    def test_both_failures_yield_real_error(self) -> None:
        adapter = _StubAdapter(
            api_key="K",
            key_outcome=URLError("k boom"),
            proxy_host="P",
            proxy_outcome=URLError("p boom"),
        )
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
        assert adapter.calls == ["key", "proxy"]


class TestNoProxyConfigured:
    def test_key_failure_no_proxy_yields_real_error(self) -> None:
        adapter = _StubAdapter(
            api_key="K",
            key_outcome=URLError("k boom"),
        )
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert adapter.calls == ["key"]

    def test_proxy_returns_none_means_unsupported(self) -> None:
        adapter = _StubAdapter(
            api_key="K",
            key_outcome=URLError("k"),
            proxy_host="P",
            proxy_outcome="skip",
        )
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert adapter.calls == ["key", "proxy"]


class TestNonRetryableExceptionsBubbleUp:
    """Programmer errors in subclasses must not be swallowed by the cascade."""

    def test_generic_exception_in_key_search_propagates(self) -> None:
        adapter = _StubAdapter(api_key="K", key_outcome=ValueError("bug"))
        with pytest.raises(ValueError, match="bug"):
            adapter.fetch(SearchQuery(text="x"))
