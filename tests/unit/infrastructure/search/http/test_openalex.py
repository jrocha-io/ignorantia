"""Unit tests for :class:`OpenAlexAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.openalex import OpenAlexAdapter


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
    return json.dumps({"results": [], "meta": {"count": 0}}).encode("utf-8")


def _payload(*items: dict[str, object], total: int | None = None) -> bytes:
    body: dict[str, object] = {"results": list(items), "meta": {"count": total or len(items)}}
    return json.dumps(body).encode("utf-8")


def _work(
    *,
    title: str = "A title",
    year: int = 2024,
    doi: str | None = "https://doi.org/10.1234/x",
    is_oa: bool = True,
    pdf_url: str | None = "https://example.org/x.pdf",
    journal: str = "PLOS ONE",
    abstract_index: dict[str, list[int]] | None = None,
) -> dict[str, object]:
    return {
        "id": "https://openalex.org/W123",
        "title": title,
        "publication_year": year,
        "doi": doi,
        "language": "en",
        "open_access": {"is_oa": is_oa},
        "best_oa_location": {"pdf_url": pdf_url},
        "primary_location": {"source": {"display_name": journal}},
        "authorships": [
            {"author": {"display_name": "Silva, A."}},
            {"author": {"display_name": "Pereira, B."}},
        ],
        "type": "journal-article",
        "cited_by_count": 5,
        "abstract_inverted_index": abstract_index,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert OpenAlexAdapter(_FakeHttpClient()).source_id == "openalex"

    def test_default_tier_is_tier1(self) -> None:
        assert OpenAlexAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        assert OpenAlexAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x")).items == ()

    def test_doi_url_prefix_is_stripped(self) -> None:
        body = _payload(_work(doi="https://doi.org/10.1234/x"))
        adapter = OpenAlexAdapter(_FakeHttpClient(body), max_results=5)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.doi == "10.1234/x"

    def test_authors_parsed_in_order(self) -> None:
        body = _payload(_work())
        adapter = OpenAlexAdapter(_FakeHttpClient(body), max_results=5)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_pdf_url_extracted(self) -> None:
        body = _payload(_work(pdf_url="https://x.org/y.pdf"))
        adapter = OpenAlexAdapter(_FakeHttpClient(body), max_results=5)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://x.org/y.pdf"

    def test_is_oa_passes_through(self) -> None:
        body = _payload(_work(is_oa=False))
        adapter = OpenAlexAdapter(_FakeHttpClient(body), max_results=5)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is False

    def test_inverted_index_abstract_is_reconstructed(self) -> None:
        # "Hello world" → {"Hello":[0],"world":[1]}
        body = _payload(_work(abstract_index={"Hello": [0], "world": [1]}))
        adapter = OpenAlexAdapter(_FakeHttpClient(body), max_results=5)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.abstract == "Hello world"

    def test_method_is_real(self) -> None:
        body = _payload(_work())
        adapter = OpenAlexAdapter(_FakeHttpClient(body), max_results=5)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL


class TestQueryConstruction:
    def test_filter_uses_title_and_abstract_search(self) -> None:
        client = _FakeHttpClient(_empty())
        OpenAlexAdapter(client, max_results=5).fetch(SearchQuery(text="letramento"))
        assert "title_and_abstract.search" in _decode(client.urls[0])

    def test_year_range_in_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        OpenAlexAdapter(client, max_results=5).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        decoded = _decode(client.urls[0])
        assert "publication_year:2020-2024" in decoded

    def test_oa_only_appends_is_oa_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        OpenAlexAdapter(client, max_results=5, oa_only=True).fetch(SearchQuery(text="x"))
        assert "is_oa:true" in _decode(client.urls[0])

    def test_oa_only_false_does_not_add_is_oa_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        OpenAlexAdapter(client, max_results=5, oa_only=False).fetch(SearchQuery(text="x"))
        assert "is_oa:true" not in _decode(client.urls[0])


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_work(title=f"t{i}") for i in range(8)])
        adapter = OpenAlexAdapter(_FakeHttpClient(body), max_results=3)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 3


def _decode(url: str) -> str:
    from urllib.parse import unquote_plus

    return unquote_plus(url)
