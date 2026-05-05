"""Unit tests for :class:`OapenAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.oapen import OapenAdapter


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
    return b"[]"


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps(list(items)).encode("utf-8")


def _item(
    *,
    title: str = "Digital literacy in aging societies",
    authors: list[str] | None = None,
    issued: str = "2024-04-12",
    doi: str = "10.1234/x",
    isbn: str = "978-0-000000-01-1",
    publisher: str = "Routledge",
    language: str = "en",
    handle: str = "20.500.12657/123",
    pdf_link: str | None = "/bitstream/handle/20.500.12657/123/file.pdf",
) -> dict[str, object]:
    metadata: list[dict[str, str]] = [
        {"key": "dc.title", "value": title},
        {"key": "dc.date.issued", "value": issued},
        {"key": "dc.identifier.doi", "value": doi},
        {"key": "dc.identifier.isbn", "value": isbn},
        {"key": "dc.publisher", "value": publisher},
        {"key": "dc.language.iso", "value": language},
    ]
    for author in authors or ["Silva, A.", "Pereira, B."]:
        metadata.append({"key": "dc.contributor.author", "value": author})
    bitstreams: list[dict[str, str | None]] = []
    if pdf_link:
        bitstreams.append({"format": "PDF", "retrieveLink": pdf_link})
    return {
        "uuid": "abc-123",
        "handle": handle,
        "metadata": metadata,
        "bitstreams": bitstreams,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert OapenAdapter(_FakeHttpClient()).source_id == "oapen"

    def test_source_tier(self) -> None:
        assert OapenAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = OapenAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_non_list_response_yields_empty(self) -> None:
        body = json.dumps({"error": "unexpected"}).encode("utf-8")
        result = OapenAdapter(_FakeHttpClient(body)).fetch(SearchQuery(text="x"))
        assert result.items == ()

    def test_single_item_parsed(self) -> None:
        body = _payload(_item(title="A book", doi="10.1/y"))
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A book"
        assert item.year == 2024
        assert item.doi == "10.1/y"

    def test_multiple_authors_extracted(self) -> None:
        body = _payload(_item(authors=["Silva, A.", "Pereira, B.", "Costa, C."]))
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.", "Costa, C.")

    def test_pdf_url_resolves_bitstream_to_absolute_url(self) -> None:
        body = _payload(_item(pdf_link="/bitstream/handle/X/file.pdf"))
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://library.oapen.org/bitstream/handle/X/file.pdf"

    def test_no_bitstream_falls_back_to_handle(self) -> None:
        body = _payload(_item(pdf_link=None, handle="20.500.12657/999"))
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://library.oapen.org/handle/20.500.12657/999"

    def test_isbn_extracted(self) -> None:
        body = _payload(_item(isbn="978-0-000000-99-9"))
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.isbn == "978-0-000000-99-9"

    def test_publisher_becomes_venue(self) -> None:
        body = _payload(_item(publisher="Editora UFMG"))
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.venue == "Editora UFMG"

    def test_items_marked_as_oa(self) -> None:
        body = _payload(_item())
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True

    def test_publication_type_is_book(self) -> None:
        body = _payload(_item())
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.publication_type == "book"


class TestYearFilter:
    def test_filters_out_of_range_years(self) -> None:
        body = _payload(
            _item(issued="2018-01-01"),
            _item(issued="2023-06-15"),
            _item(issued="2025-12-01"),
        )
        adapter = OapenAdapter(_FakeHttpClient(body), max_results=10)
        result = adapter.fetch(SearchQuery(text="x", year_start=2020, year_end=2024))
        years = {item.year for item in result.items}
        assert years == {2023}


class TestQueryConstruction:
    def test_query_in_url(self) -> None:
        client = _FakeHttpClient(_empty())
        OapenAdapter(client, max_results=10).fetch(SearchQuery(text="literacy"))
        assert "query=literacy" in client.urls[0]

    def test_expand_metadata_and_bitstreams(self) -> None:
        client = _FakeHttpClient(_empty())
        OapenAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "expand=metadata,bitstreams" in decoded
