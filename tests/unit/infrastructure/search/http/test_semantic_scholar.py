"""Unit tests for :class:`SemanticScholarAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.semantic_scholar import (
    SemanticScholarAdapter,
)


class _FakeHttpClient:
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


def _empty() -> bytes:
    return json.dumps({"data": []}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"data": list(items)}).encode("utf-8")


def _paper(
    *,
    paper_id: str = "abc123",
    title: str = "A title",
    year: int = 2024,
    doi: str | None = "10.1234/x",
    pdf: str | None = None,
    venue: str = "Some Venue",
) -> dict[str, object]:
    return {
        "paperId": paper_id,
        "title": title,
        "year": year,
        "venue": venue,
        "abstract": "Abstract.",
        "authors": [{"name": "Silva, A."}, {"name": "Pereira, B."}],
        "externalIds": {"DOI": doi} if doi else {},
        "openAccessPdf": {"url": pdf} if pdf else None,
        "publicationTypes": ["JournalArticle"],
        "fieldsOfStudy": ["Computer Science"],
        "citationCount": 9,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert SemanticScholarAdapter(_FakeHttpClient()).source_id == "semantic_scholar"

    def test_source_tier(self) -> None:
        assert SemanticScholarAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestParsing:
    def test_empty_response(self) -> None:
        assert (
            SemanticScholarAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x")).items
            == ()
        )

    def test_single_paper_parsed(self) -> None:
        body = _payload(_paper(title="Cool paper", year=2023, doi="10.1/a"))
        adapter = SemanticScholarAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "Cool paper"
        assert item.year == 2023
        assert item.doi == "10.1/a"

    def test_authors_parsed(self) -> None:
        body = _payload(_paper())
        adapter = SemanticScholarAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_pdf_url_marks_is_oa(self) -> None:
        body = _payload(_paper(pdf="https://x.org/y.pdf"))
        adapter = SemanticScholarAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True
        assert item.url_for_pdf == "https://x.org/y.pdf"

    def test_no_pdf_means_not_oa(self) -> None:
        body = _payload(_paper(pdf=None))
        adapter = SemanticScholarAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is False
        assert item.url_for_pdf is None

    def test_method_is_real(self) -> None:
        body = _payload(_paper())
        adapter = SemanticScholarAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).method is Method.REAL


class TestQueryConstruction:
    def test_query_text_in_url(self) -> None:
        client = _FakeHttpClient(_empty())
        SemanticScholarAdapter(client, max_results=10).fetch(SearchQuery(text="letramento"))
        assert "letramento" in client.urls[0] or "letramento" in _decode(client.urls[0])

    def test_year_range_appended(self) -> None:
        client = _FakeHttpClient(_empty())
        SemanticScholarAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        assert "year=2020-2024" in _decode(client.urls[0])


class TestApiKeyHeader:
    def test_api_key_passed_as_header(self) -> None:
        client = _FakeHttpClient(_empty())
        SemanticScholarAdapter(client, max_results=10, api_key="secret-key").fetch(
            SearchQuery(text="x")
        )
        assert client.headers[0] == {"x-api-key": "secret-key"}

    def test_no_api_key_means_no_extra_headers(self) -> None:
        client = _FakeHttpClient(_empty())
        SemanticScholarAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert client.headers[0] is None


class TestPagination:
    def test_paginates_until_empty(self) -> None:
        page = _payload(*[_paper(paper_id=f"id-{i}") for i in range(3)])
        client = _FakeHttpClient(page, _empty())
        adapter = SemanticScholarAdapter(client, max_per_page=3, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 3

    def test_truncates_to_max_results(self) -> None:
        page = _payload(*[_paper(paper_id=f"id-{i}") for i in range(5)])
        client = _FakeHttpClient(page, page, page)
        adapter = SemanticScholarAdapter(client, max_per_page=5, max_results=8)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 8


def _decode(url: str) -> str:
    from urllib.parse import unquote_plus

    return unquote_plus(url)
