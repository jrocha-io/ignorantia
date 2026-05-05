"""Unit tests for :class:`GoogleScholarSerpApiAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.google_scholar_serpapi import (
    GoogleScholarSerpApiAdapter,
)


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
        raise AssertionError("GoogleScholarSerpApiAdapter must use GET")


class _UnusedHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called when no api_key")

    def post(self, url: str, *, data: bytes, headers: object | None = None) -> bytes:
        del url, data, headers
        raise AssertionError("HTTP must not be called when no api_key")


def _empty() -> bytes:
    return json.dumps({"organic_results": []}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"organic_results": list(items)}).encode("utf-8")


def _organic(
    *,
    title: str = "Digital health interventions",
    link: str = "https://example.org/x",
    snippet: str = "Background. Methods. Results.",
    summary: str = "J Smith, A Doe - Journal of Health, 2023",
    authors: list[str] | None = None,
    pdf_url: str | None = None,
) -> dict[str, object]:
    publication_info: dict[str, object] = {"summary": summary}
    if authors is not None:
        publication_info["authors"] = [{"name": n} for n in authors]
    out: dict[str, object] = {
        "title": title,
        "link": link,
        "snippet": snippet,
        "publication_info": publication_info,
    }
    if pdf_url is not None:
        out["resources"] = [{"file_format": "PDF", "link": pdf_url}]
    return out


class TestMetadata:
    def test_source_id(self) -> None:
        adapter = GoogleScholarSerpApiAdapter(_UnusedHttp())
        assert adapter.source_id == "google_scholar_serpapi"

    def test_source_tier(self) -> None:
        adapter = GoogleScholarSerpApiAdapter(_UnusedHttp())
        assert adapter.source_tier is Tier.TIER2


class TestNoApiKey:
    def test_fetch_without_key_yields_real_error(self) -> None:
        result = GoogleScholarSerpApiAdapter(_UnusedHttp()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
        assert result.source == "google_scholar_serpapi"
        assert result.source_tier is Tier.TIER2


class TestParsing:
    def test_empty_response(self) -> None:
        result = GoogleScholarSerpApiAdapter(
            _FakeGetHttp(_empty()), api_key="K1", max_results=10
        ).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_title_and_url_parsed(self) -> None:
        body = _payload(_organic(title="A study", link="https://example.org/y"))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].title == "A study"
        assert items[0].url == "https://example.org/y"

    def test_authors_extracted(self) -> None:
        body = _payload(_organic(authors=["Smith J", "Doe A"]))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].authors == ("Smith J", "Doe A")

    def test_year_extracted_from_summary(self) -> None:
        body = _payload(_organic(summary="J Smith, A Doe - Journal X, 2021"))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].year == 2021

    def test_year_none_when_summary_has_no_year(self) -> None:
        body = _payload(_organic(summary="J Smith, A Doe - Journal X"))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].year is None

    def test_venue_extracted_from_summary(self) -> None:
        body = _payload(_organic(summary="J Smith, A Doe - Journal of Health, 2023"))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].venue == "Journal of Health, 2023"

    def test_pdf_url_extracted_from_resources(self) -> None:
        body = _payload(_organic(pdf_url="https://example.org/x.pdf"))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].url_for_pdf == "https://example.org/x.pdf"

    def test_is_oa_true_when_pdf_available(self) -> None:
        body = _payload(_organic(pdf_url="https://example.org/x.pdf"))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].is_oa is True

    def test_is_oa_false_when_no_pdf(self) -> None:
        body = _payload(_organic(pdf_url=None))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].is_oa is False

    def test_doi_is_none_because_google_scholar_does_not_expose_dois(self) -> None:
        body = _payload(_organic())
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].doi is None

    def test_abstract_truncated_to_500_chars(self) -> None:
        long_snippet = "x" * 800
        body = _payload(_organic(snippet=long_snippet))
        items = (
            GoogleScholarSerpApiAdapter(_FakeGetHttp(body), api_key="K1", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert len(items[0].abstract) == 500


class TestRequestShape:
    def test_uses_get_to_serpapi_endpoint(self) -> None:
        client = _FakeGetHttp(_empty())
        GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=10).fetch(
            SearchQuery(text="x")
        )
        assert client.urls[0].startswith("https://serpapi.com/search?")

    def test_engine_is_google_scholar(self) -> None:
        client = _FakeGetHttp(_empty())
        GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=10).fetch(
            SearchQuery(text="x")
        )
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["engine"] == ["google_scholar"]

    def test_query_and_key_passed_as_params(self) -> None:
        client = _FakeGetHttp(_empty())
        GoogleScholarSerpApiAdapter(client, api_key="SECRET", max_results=10).fetch(
            SearchQuery(text="literacy")
        )
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["q"] == ["literacy"]
        assert params["api_key"] == ["SECRET"]

    def test_year_range_passed_as_as_ylo_as_yhi(self) -> None:
        client = _FakeGetHttp(_empty())
        GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["as_ylo"] == ["2020"]
        assert params["as_yhi"] == ["2024"]

    def test_year_range_omitted_when_unspecified(self) -> None:
        client = _FakeGetHttp(_empty())
        GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=10).fetch(
            SearchQuery(text="x")
        )
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert "as_ylo" not in params
        assert "as_yhi" not in params

    def test_num_param_is_10(self) -> None:
        client = _FakeGetHttp(_empty())
        GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=10).fetch(
            SearchQuery(text="x")
        )
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["num"] == ["10"]


class TestPagination:
    def test_paginates_until_max_results(self) -> None:
        page1 = _payload(*[_organic(title=f"t{n}") for n in range(10)])
        page2 = _payload(*[_organic(title=f"t{n + 10}") for n in range(5)])
        client = _FakeGetHttp(page1, page2)
        items = (
            GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=15)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert len(items) == 15
        assert len(client.urls) == 2

    def test_stops_when_short_page_indicates_end(self) -> None:
        short_page = _payload(*[_organic(title=f"t{n}") for n in range(3)])
        client = _FakeGetHttp(short_page)
        items = (
            GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=50)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert len(items) == 3
        assert len(client.urls) == 1

    def test_start_param_advances_by_10(self) -> None:
        page1 = _payload(*[_organic(title=f"t{n}") for n in range(10)])
        page2 = _payload(*[_organic(title=f"t{n + 10}") for n in range(10)])
        client = _FakeGetHttp(page1, page2)
        GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=20).fetch(
            SearchQuery(text="x")
        )
        starts = [parse_qs(urlsplit(u).query).get("start", ["?"])[0] for u in client.urls]
        assert starts == ["0", "10"]

    def test_truncates_to_max_results(self) -> None:
        page = _payload(*[_organic(title=f"t{n}") for n in range(10)])
        client = _FakeGetHttp(page)
        items = (
            GoogleScholarSerpApiAdapter(client, api_key="K1", max_results=5)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert len(items) == 5
