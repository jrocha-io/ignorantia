"""Unit tests for :class:`OaResolverChain`.

The chain tries resolvers in priority order and returns the first
:class:`OaLocation` it gets back. Network errors from one resolver
are swallowed so the next is tried; ``ValueError`` (invalid DOI) is
NOT swallowed because that's a caller-side contract violation.
"""

from __future__ import annotations

from urllib.error import HTTPError, URLError

import pytest

from ignorantia.domain.search.entities import OaLocation
from ignorantia.domain.search.ports.oa_resolver_port import OaResolverPort
from ignorantia.infrastructure.search.oa_resolver_chain import OaResolverChain


class _FakeResolver(OaResolverPort):
    def __init__(self, source_id: str, outcome: object) -> None:
        self._source_id = source_id
        self._outcome = outcome
        self.calls: list[str] = []

    @property
    def source_id(self) -> str:
        return self._source_id

    def resolve(self, doi: str) -> OaLocation | None:
        self.calls.append(doi)
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        if self._outcome is None:
            return None
        assert isinstance(self._outcome, OaLocation)
        return self._outcome


def _location(resolver: str = "x", url: str = "https://oa.example/x") -> OaLocation:
    return OaLocation(url=url, url_for_pdf=url, resolver=resolver)


class TestPriority:
    def test_first_non_none_wins(self) -> None:
        loc = _location("first")
        first = _FakeResolver("first", loc)
        second = _FakeResolver("second", _location("second"))
        chain = OaResolverChain((first, second))
        assert chain.resolve("10.1/x") is loc
        assert second.calls == []

    def test_falls_through_when_first_returns_none(self) -> None:
        loc = _location("second")
        first = _FakeResolver("first", None)
        second = _FakeResolver("second", loc)
        chain = OaResolverChain((first, second))
        assert chain.resolve("10.1/x") is loc
        assert first.calls == ["10.1/x"]
        assert second.calls == ["10.1/x"]

    def test_all_none_returns_none(self) -> None:
        first = _FakeResolver("first", None)
        second = _FakeResolver("second", None)
        chain = OaResolverChain((first, second))
        assert chain.resolve("10.1/x") is None

    def test_empty_chain_returns_none(self) -> None:
        chain = OaResolverChain(())
        assert chain.resolve("10.1/x") is None


class TestErrorTolerance:
    def _http_error(self) -> HTTPError:
        return HTTPError("https://x/", 503, "boom", hdrs=None, fp=None)  # type: ignore[arg-type]

    def test_http_error_swallowed_chain_continues(self) -> None:
        loc = _location("second")
        first = _FakeResolver("first", self._http_error())
        second = _FakeResolver("second", loc)
        chain = OaResolverChain((first, second))
        assert chain.resolve("10.1/x") is loc

    def test_url_error_swallowed_chain_continues(self) -> None:
        loc = _location("second")
        first = _FakeResolver("first", URLError("dns"))
        second = _FakeResolver("second", loc)
        chain = OaResolverChain((first, second))
        assert chain.resolve("10.1/x") is loc

    def test_timeout_error_swallowed_chain_continues(self) -> None:
        loc = _location("second")
        first = _FakeResolver("first", TimeoutError("slow"))
        second = _FakeResolver("second", loc)
        chain = OaResolverChain((first, second))
        assert chain.resolve("10.1/x") is loc

    def test_value_error_propagates(self) -> None:
        # Invalid DOI is a caller-side contract violation; do not swallow.
        first = _FakeResolver("first", ValueError("invalid doi"))
        second = _FakeResolver("second", _location("second"))
        chain = OaResolverChain((first, second))
        with pytest.raises(ValueError):
            chain.resolve("garbage")
        assert second.calls == []

    def test_all_resolvers_error_returns_none(self) -> None:
        first = _FakeResolver("first", self._http_error())
        second = _FakeResolver("second", URLError("dns"))
        chain = OaResolverChain((first, second))
        assert chain.resolve("10.1/x") is None


class TestSourceId:
    def test_chain_source_id_is_chain(self) -> None:
        chain = OaResolverChain((_FakeResolver("a", None),))
        assert chain.source_id == "chain"
