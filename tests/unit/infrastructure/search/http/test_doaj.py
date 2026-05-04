"""Unit tests for :class:`DoajAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http.doaj import DoajAdapter


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


def _payload(*items: dict[str, object], total: int | None = None) -> bytes:
    body: dict[str, object] = {"results": list(items)}
    if total is not None:
        body["total"] = total
    return json.dumps(body).encode("utf-8")


def _empty() -> bytes:
    return _payload()


def _doaj_item(
    *,
    title: str = "A title",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1234/x",
    journal_title: str = "Open Journal",
    journal_language: object = "en",
) -> dict[str, object]:
    return {
        "bibjson": {
            "title": title,
            "author": [{"name": n} for n in (authors or ["Silva, A."])],
            "year": year,
            "identifier": [{"type": "doi", "id": doi}],
            "journal": {"title": journal_title, "language": journal_language},
            "link": [{"type": "fulltext", "url": f"https://doaj.org/article/{doi}"}],
        }
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert DoajAdapter(_FakeHttpClient()).source_id == "doaj"

    def test_source_tier(self) -> None:
        assert DoajAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response_yields_no_items(self) -> None:
        adapter = DoajAdapter(_FakeHttpClient(_empty()))
        assert adapter.fetch(SearchQuery(text="x")).items == ()

    def test_single_item_is_parsed(self) -> None:
        body = _payload(_doaj_item(title="Open access study", year=2023, doi="10.1/a"))
        adapter = DoajAdapter(_FakeHttpClient(body), max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 1
        item = result.items[0]
        assert item.title == "Open access study"
        assert item.year == 2023
        assert item.doi == "10.1/a"
        assert item.is_oa is True  # DOAJ items are always OA

    def test_authors_extracted(self) -> None:
        body = _payload(_doaj_item(authors=["Silva, A.", "Pereira, B."]))
        adapter = DoajAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_journal_title_becomes_venue(self) -> None:
        body = _payload(_doaj_item(journal_title="Cool Journal"))
        adapter = DoajAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.venue == "Cool Journal"

    def test_journal_language_string_is_used(self) -> None:
        body = _payload(_doaj_item(journal_language="pt"))
        adapter = DoajAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].language == "pt"

    def test_journal_language_list_first_item_is_used(self) -> None:
        body = _payload(_doaj_item(journal_language=["pt", "en"]))
        adapter = DoajAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].language == "pt"

    def test_fulltext_link_becomes_url(self) -> None:
        body = _payload(_doaj_item(doi="10.1/x"))
        adapter = DoajAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://doaj.org/article/10.1/x"


class TestQueryConstruction:
    def test_query_text_appears_in_url(self) -> None:
        client = _FakeHttpClient(_empty())
        DoajAdapter(client, max_results=10).fetch(SearchQuery(text="letramento"))
        assert "letramento" in client.urls[0] or "letramento" in _decode(client.urls[0])

    def test_year_range_appended_as_lucene_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        DoajAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2018, year_end=2024)
        )
        decoded = _decode(client.urls[0])
        assert "bibjson.year" in decoded
        assert "2018" in decoded
        assert "2024" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_doaj_item(doi=f"10.1/{i}") for i in range(8)])
        adapter = DoajAdapter(_FakeHttpClient(body), max_results=5)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 5


def _decode(url: str) -> str:
    from urllib.parse import unquote

    return unquote(url)
