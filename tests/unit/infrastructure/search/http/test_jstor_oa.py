"""Unit tests for :class:`JstorOaAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.jstor_oa import JstorOaAdapter


class _FakeHttpClient:
    def __init__(self, *bodies: bytes) -> None:
        self._bodies: Iterator[bytes] = iter(bodies)
        self.urls: list[str] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        del headers
        self.urls.append(url)
        try:
            return next(self._bodies)
        except StopIteration:
            return _empty()


def _empty() -> bytes:
    return json.dumps({"results": []}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"results": list(items)}).encode("utf-8")


def _item(
    *,
    title: str = "Aging societies",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.2307/x",
    jstor_id: str = "i12345",
    venue: str = "American Sociological Review",
    pdf: str = "https://www.jstor.org/stable/x",
    resource_type: str = "journal-article",
) -> dict[str, object]:
    return {
        "title": title,
        "authors": authors or ["Silva, A."],
        "year": year,
        "doi": doi,
        "id": jstor_id,
        "source": venue,
        "url": pdf,
        "type": resource_type,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert JstorOaAdapter(_FakeHttpClient()).source_id == "jstor_oa"

    def test_source_tier(self) -> None:
        assert JstorOaAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = JstorOaAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_item_parsed(self) -> None:
        body = _payload(_item(title="A study", year=2023, doi="10.2307/y"))
        item = (
            JstorOaAdapter(_FakeHttpClient(body), max_results=10)
            .fetch(SearchQuery(text="x"))
            .items[0]
        )
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.2307/y"

    def test_authors_parsed(self) -> None:
        body = _payload(_item(authors=["Silva, A.", "Pereira, B."]))
        item = (
            JstorOaAdapter(_FakeHttpClient(body), max_results=10)
            .fetch(SearchQuery(text="x"))
            .items[0]
        )
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_alternative_creators_field(self) -> None:
        body = _payload({"title": "X", "creators": ["Doe, J."], "year": 2024})
        item = (
            JstorOaAdapter(_FakeHttpClient(body), max_results=10)
            .fetch(SearchQuery(text="x"))
            .items[0]
        )
        assert item.authors == ("Doe, J.",)

    def test_url_extracted(self) -> None:
        body = _payload(_item(pdf="https://www.jstor.org/stable/abc"))
        item = (
            JstorOaAdapter(_FakeHttpClient(body), max_results=10)
            .fetch(SearchQuery(text="x"))
            .items[0]
        )
        assert item.url_for_pdf == "https://www.jstor.org/stable/abc"

    def test_alternate_response_shape_with_hits(self) -> None:
        # Some JSTOR Labs responses use "hits" instead of "results"
        body = json.dumps({"hits": [_item(title="Hit-shaped")]}).encode("utf-8")
        item = (
            JstorOaAdapter(_FakeHttpClient(body), max_results=10)
            .fetch(SearchQuery(text="x"))
            .items[0]
        )
        assert item.title == "Hit-shaped"

    def test_items_marked_as_oa(self) -> None:
        body = _payload(_item())
        item = (
            JstorOaAdapter(_FakeHttpClient(body), max_results=10)
            .fetch(SearchQuery(text="x"))
            .items[0]
        )
        assert item.is_oa is True

    def test_resource_type_kept(self) -> None:
        body = _payload(_item(resource_type="book"))
        item = (
            JstorOaAdapter(_FakeHttpClient(body), max_results=10)
            .fetch(SearchQuery(text="x"))
            .items[0]
        )
        assert item.publication_type == "book"


class TestQueryConstruction:
    def test_filter_open_access(self) -> None:
        client = _FakeHttpClient(_empty())
        JstorOaAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert "filter=open_access" in client.urls[0]

    def test_year_range_appended(self) -> None:
        client = _FakeHttpClient(_empty())
        JstorOaAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        assert "year_from=2020" in client.urls[0]
        assert "year_to=2024" in client.urls[0]


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_item(jstor_id=f"i{n}") for n in range(8)])
        result = JstorOaAdapter(_FakeHttpClient(body), max_results=5).fetch(SearchQuery(text="x"))
        assert len(result.items) == 5
