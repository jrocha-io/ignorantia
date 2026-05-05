"""Unit tests for :class:`RedibAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.redib import RedibAdapter


class _FakeGetHttp:
    def __init__(self, *bodies: bytes) -> None:
        self._bodies: Iterator[bytes] = iter(bodies)
        self.urls: list[str] = []
        self.headers: list[dict[str, str] | None] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        self.urls.append(url)
        self.headers.append(headers if isinstance(headers, dict) else None)
        try:
            return next(self._bodies)
        except StopIteration:
            return _empty()

    def post(self, url: str, *, data: bytes, headers: object | None = None) -> bytes:
        del url, data, headers
        raise AssertionError("RedibAdapter must use GET")


class _UnusedHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called when no api_key")

    def post(self, url: str, *, data: bytes, headers: object | None = None) -> bytes:
        del url, data, headers
        raise AssertionError("HTTP must not be called when no api_key")


def _empty() -> bytes:
    return json.dumps({"results": [], "total": 0}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"results": list(items), "total": len(items)}).encode("utf-8")


def _item(
    *,
    title: str = "Educación digital",
    authors: list[str] | None = None,
    year: int = 2023,
    doi: str = "10.1234/redib.1",
    journal_title: str = "Revista Iberoamericana",
    language: str = "es",
    country: str = "BR",
    url: str | None = "https://redib.org/recurso/X",
    rid: str = "REDIB-001",
) -> dict[str, object]:
    return {
        "title": title,
        "authors": authors or ["Mock A"],
        "year": year,
        "doi": doi,
        "journal_title": journal_title,
        "language": language,
        "country": country,
        "url": url,
        "id": rid,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert RedibAdapter(_UnusedHttp()).source_id == "redib"

    def test_source_tier(self) -> None:
        assert RedibAdapter(_UnusedHttp()).source_tier is Tier.TIER1


class TestNoApiKey:
    def test_fetch_without_key_yields_real_error(self) -> None:
        result = RedibAdapter(_UnusedHttp()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
        assert result.source == "redib"
        assert result.source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = RedibAdapter(_FakeGetHttp(_empty()), api_key="K1").fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_item_parsed(self) -> None:
        body = _payload(_item(title="A study", year=2022, doi="10.1/y"))
        items = (
            RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].title == "A study"
        assert items[0].year == 2022
        assert items[0].doi == "10.1/y"

    def test_authors_extracted(self) -> None:
        body = _payload(_item(authors=["Silva A", "Souza B"]))
        items = (
            RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].authors == ("Silva A", "Souza B")

    def test_venue_from_journal_title(self) -> None:
        body = _payload(_item(journal_title="Revista X"))
        items = (
            RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].venue == "Revista X"

    def test_language_preserved(self) -> None:
        body = _payload(_item(language="pt"))
        items = (
            RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].language == "pt"

    def test_default_language_is_es_when_missing(self) -> None:
        item = _item()
        del item["language"]
        body = _payload(item)
        items = (
            RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].language == "es"

    def test_url_extracted(self) -> None:
        body = _payload(_item(url="https://redib.org/recurso/Y"))
        items = (
            RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].url == "https://redib.org/recurso/Y"

    def test_is_oa_true_because_redib_indexes_oa_only(self) -> None:
        body = _payload(_item())
        items = (
            RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].is_oa is True


class TestRequestShape:
    def test_uses_get_to_search_endpoint(self) -> None:
        client = _FakeGetHttp(_empty())
        RedibAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert client.urls[0].startswith("https://redib.org/api/v1/search?")

    def test_query_and_key_passed_as_params(self) -> None:
        client = _FakeGetHttp(_empty())
        RedibAdapter(client, api_key="SECRET").fetch(SearchQuery(text="literacy"))
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["q"] == ["literacy"]
        assert params["key"] == ["SECRET"]
        assert params["format"] == ["json"]

    def test_year_range_passed_as_params(self) -> None:
        client = _FakeGetHttp(_empty())
        RedibAdapter(client, api_key="K1").fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["yearFrom"] == ["2020"]
        assert params["yearTo"] == ["2024"]

    def test_year_range_omitted_when_unspecified(self) -> None:
        client = _FakeGetHttp(_empty())
        RedibAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert "yearFrom" not in params
        assert "yearTo" not in params

    def test_limit_capped_at_100(self) -> None:
        client = _FakeGetHttp(_empty())
        RedibAdapter(client, api_key="K1", max_results=500).fetch(SearchQuery(text="x"))
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["limit"] == ["100"]

    def test_limit_passes_through_below_cap(self) -> None:
        client = _FakeGetHttp(_empty())
        RedibAdapter(client, api_key="K1", max_results=25).fetch(SearchQuery(text="x"))
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["limit"] == ["25"]

    def test_accept_header_is_application_json(self) -> None:
        client = _FakeGetHttp(_empty())
        RedibAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("Accept") == "application/json"


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_item(title=f"t{n}") for n in range(8)])
        adapter = RedibAdapter(_FakeGetHttp(body), api_key="K1", max_results=5)
        assert len(adapter.fetch(SearchQuery(text="x")).items) == 5
