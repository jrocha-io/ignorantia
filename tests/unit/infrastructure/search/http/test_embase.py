"""Unit tests for :class:`EmbaseAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.embase import EmbaseAdapter


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
    return json.dumps({"results": {"article": []}}).encode("utf-8")


def _payload(*entries: dict[str, object]) -> bytes:
    return json.dumps({"results": {"article": list(entries)}}).encode("utf-8")


def _entry(
    *,
    title: str = "Glycemic control in type 2 diabetes",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1016/j.embase.2024.001",
    issn: str = "0140-6736",
    journal: str = "Lancet",
    pub_type: str = "article",
) -> dict[str, object]:
    name_list = [{"name": n} for n in (authors or ["Silva A"])]
    return {
        "titleAndAuthor": {"title": title},
        "authors": name_list,
        "publicationYear": year,
        "doi": doi,
        "source": {"issn": issn, "title": journal},
        "publicationType": pub_type,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert EmbaseAdapter(_FakeHttpClient()).source_id == "embase"

    def test_source_tier(self) -> None:
        assert EmbaseAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestKeyMode:
    def test_no_credentials_yields_real_error(self) -> None:
        result = EmbaseAdapter(_FakeHttpClient()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR

    def test_x_els_apikey_header_set(self) -> None:
        client = _FakeHttpClient(_empty())
        EmbaseAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("X-ELS-APIKey") == "K1"

    def test_successful_fetch(self) -> None:
        body = _payload(_entry(title="A study", year=2023, doi="10.1/y"))
        adapter = EmbaseAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        item = result.items[0]
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1/y"

    def test_authors_extracted(self) -> None:
        body = _payload(_entry(authors=["Smith J", "Doe A"]))
        adapter = EmbaseAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Smith J", "Doe A")

    def test_issn_and_venue_from_source(self) -> None:
        body = _payload(_entry(issn="1111-2222", journal="Lancet"))
        adapter = EmbaseAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.issn == "1111-2222"
        assert item.venue == "Lancet"

    def test_is_oa_false_for_paywall(self) -> None:
        body = _payload(_entry())
        adapter = EmbaseAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is False


class TestQueryConstruction:
    def test_query_passed_in_query_param(self) -> None:
        client = _FakeHttpClient(_empty())
        EmbaseAdapter(client, api_key="K").fetch(SearchQuery(text="diabetes"))
        from urllib.parse import unquote_plus

        assert "query=diabetes" in unquote_plus(client.urls[0])

    def test_year_range_in_emtree_syntax(self) -> None:
        client = _FakeHttpClient(_empty())
        EmbaseAdapter(client, api_key="K").fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        assert "[2020-2024]/py" in unquote_plus(client.urls[0])

    def test_count_param_capped(self) -> None:
        client = _FakeHttpClient(_empty())
        EmbaseAdapter(client, api_key="K", max_results=200).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "count=25" in decoded
