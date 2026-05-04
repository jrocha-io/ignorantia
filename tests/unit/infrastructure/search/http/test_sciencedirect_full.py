"""Unit tests for :class:`ScienceDirectFullAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.sciencedirect_full import (
    ScienceDirectFullAdapter,
)


class _FakeHttpClient:
    def __init__(self, *outcomes: object) -> None:
        self._outcomes: Iterator[object] = iter(outcomes)
        self.urls: list[str] = []
        self.headers: list[dict[str, str] | None] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        self.urls.append(url)
        self.headers.append(headers if isinstance(headers, dict) else None)
        try:
            outcome = next(self._outcomes)
        except StopIteration:
            return _empty()
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, bytes):
            return outcome
        raise RuntimeError(f"unexpected outcome: {outcome!r}")


def _empty() -> bytes:
    return json.dumps({"search-results": {"entry": []}}).encode("utf-8")


def _payload(*entries: dict[str, object]) -> bytes:
    return json.dumps({"search-results": {"entry": list(entries)}}).encode("utf-8")


def _entry(
    *,
    title: str = "Reliability of MEMS",
    creator: str = "Silva, A.",
    cover_date: str = "2024-04-12",
    doi: str = "10.1016/x",
    issn: str = "1234-5678",
    venue: str = "Microelectronics Reliability",
    open_access: bool = False,
    pii: str = "S0026271424001234",
) -> dict[str, object]:
    return {
        "dc:title": title,
        "dc:creator": creator,
        "prism:coverDate": cover_date,
        "prism:doi": doi,
        "prism:issn": issn,
        "prism:publicationName": venue,
        "openaccess": "1" if open_access else "0",
        "pii": pii,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert ScienceDirectFullAdapter(_FakeHttpClient()).source_id == "sciencedirect_full"

    def test_source_tier(self) -> None:
        assert ScienceDirectFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestKeyMode:
    def test_x_els_apikey_header_set(self) -> None:
        client = _FakeHttpClient(_empty())
        ScienceDirectFullAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("X-ELS-APIKey") == "K1"

    def test_no_credentials_yields_real_error(self) -> None:
        result = ScienceDirectFullAdapter(_FakeHttpClient()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR

    def test_successful_fetch_returns_real(self) -> None:
        body = _payload(_entry(title="A study", doi="10.1016/y"))
        adapter = ScienceDirectFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert result.items[0].title == "A study"

    def test_open_access_translated(self) -> None:
        body = _payload(_entry(open_access=True))
        adapter = ScienceDirectFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is True

    def test_pii_becomes_publication_type(self) -> None:
        body = _payload(_entry(pii="S0026271424001234"))
        adapter = ScienceDirectFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].publication_type == "S0026271424001234"


class TestQueryConstruction:
    def test_year_range_uses_date_param(self) -> None:
        client = _FakeHttpClient(_empty())
        ScienceDirectFullAdapter(client, api_key="K", max_results=10).fetch(
            SearchQuery(text="x", year_start=2018, year_end=2024)
        )
        assert "date=2018-2024" in client.urls[0]
