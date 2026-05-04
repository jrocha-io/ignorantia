"""Unit tests for :class:`ArxivAdapter`.

The adapter is exercised against synthetic Atom feeds served by an
injected ``HttpClient`` test double — no network is contacted.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.arxiv import ArxivAdapter


class _FakeHttpClient:
    """Drop-in replacement for :class:`HttpClient` that serves canned bodies."""

    def __init__(self, *bodies: bytes) -> None:
        self._bodies: Iterator[bytes] = iter(bodies)
        self.urls: list[str] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        del headers
        self.urls.append(url)
        try:
            return next(self._bodies)
        except StopIteration:
            return _empty_feed()


def _entry(arxiv_id: str, title: str, year: int = 2024, doi: str | None = None) -> str:
    doi_block = (
        f'<arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">{doi}</arxiv:doi>' if doi else ""
    )
    return f"""
    <entry>
      <id>http://arxiv.org/abs/{arxiv_id}</id>
      <title>{title}</title>
      <summary>Summary text for {arxiv_id}.</summary>
      <published>{year}-04-12T00:00:00Z</published>
      <author><name>Silva, A.</name></author>
      <author><name>Pereira, B.</name></author>
      <link rel="alternate" href="http://arxiv.org/abs/{arxiv_id}"/>
      <link title="pdf" href="http://arxiv.org/pdf/{arxiv_id}.pdf"/>
      {doi_block}
    </entry>
    """


def _feed(*entries: str) -> bytes:
    body = '<feed xmlns="http://www.w3.org/2005/Atom">' + "".join(entries) + "</feed>"
    return body.encode("utf-8")


def _empty_feed() -> bytes:
    return _feed()


class TestAdapterMetadata:
    def test_source_id_is_arxiv(self) -> None:
        assert ArxivAdapter(_FakeHttpClient()).source_id == "arxiv"

    def test_source_tier_is_tier1(self) -> None:
        assert ArxivAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestFetchEmptyResponse:
    def test_empty_feed_returns_empty_items(self) -> None:
        adapter = ArxivAdapter(_FakeHttpClient(_empty_feed()))
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.source == "arxiv"
        assert result.source_tier is Tier.TIER1
        assert result.method is Method.REAL


class TestFetchParsesAtomEntries:
    def test_single_entry_is_parsed(self) -> None:
        body = _feed(_entry("2401.00001", "A neat paper", year=2024))
        adapter = ArxivAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 1
        item = result.items[0]
        assert item.title == "A neat paper"
        assert item.year == 2024
        assert item.source_tier is Tier.TIER1
        assert item.is_oa is True

    def test_multiple_entries_are_parsed_in_order(self) -> None:
        body = _feed(
            _entry("2401.00001", "First"),
            _entry("2401.00002", "Second"),
            _entry("2401.00003", "Third"),
        )
        adapter = ArxivAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert tuple(item.title for item in result.items) == ("First", "Second", "Third")

    def test_authors_are_extracted(self) -> None:
        body = _feed(_entry("X", "T"))
        adapter = ArxivAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items[0].authors == ("Silva, A.", "Pereira, B.")

    def test_pdf_url_is_extracted(self) -> None:
        body = _feed(_entry("2401.00001", "T"))
        adapter = ArxivAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items[0].url_for_pdf == "http://arxiv.org/pdf/2401.00001.pdf"

    def test_doi_is_extracted_when_present(self) -> None:
        body = _feed(_entry("X", "T", doi="10.1234/x"))
        adapter = ArxivAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items[0].doi == "10.1234/x"


class TestQueryConstruction:
    def test_search_query_text_is_url_encoded(self) -> None:
        client = _FakeHttpClient(_empty_feed())
        ArxivAdapter(client, max_per_page=10, max_results=10).fetch(
            SearchQuery(text="cat:cs.AI AND abs:transformer")
        )
        assert "search_query=" in client.urls[0]
        assert "cs.AI" in client.urls[0] or "cs.AI" in _decode_qs(client.urls[0])

    def test_year_range_is_appended_as_date_filter(self) -> None:
        client = _FakeHttpClient(_empty_feed())
        ArxivAdapter(client, max_per_page=10, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        assert "submittedDate" in _decode_qs(client.urls[0])


class TestPagination:
    def test_paginates_until_empty_response(self) -> None:
        page1 = _feed(*[_entry(f"{i:04d}", f"T{i}") for i in range(3)])
        page2 = _feed(*[_entry(f"99{i:02d}", f"U{i}") for i in range(2)])
        client = _FakeHttpClient(page1, page2, _empty_feed())
        adapter = ArxivAdapter(client, max_per_page=3, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 5

    def test_stops_at_max_results(self) -> None:
        page = _feed(*[_entry(f"{i:04d}", f"T{i}") for i in range(5)])
        client = _FakeHttpClient(page, page, page, page)
        adapter = ArxivAdapter(client, max_per_page=5, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 10  # max_results


def _decode_qs(url: str) -> str:
    """Cheap helper: return query-string portion url-decoded."""
    from urllib.parse import unquote_plus

    qs = url.split("?", 1)[1] if "?" in url else ""
    return unquote_plus(qs)


@pytest.fixture
def adapter_with_empty_feed() -> ArxivAdapter:
    return ArxivAdapter(_FakeHttpClient(_empty_feed()))
