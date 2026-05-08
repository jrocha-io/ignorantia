"""Unit tests for :class:`PhilArchiveAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.philarchive import PhilArchiveAdapter


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
    return json.dumps({"results": list(items), "total": len(items)}).encode("utf-8")


def _item(
    *,
    title: str = "Phenomenology of code",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1234/x",
    publication: str = "Synthese",
    archive_url: str | None = "https://philarchive.org/archive/X1",
    category: str = "Phenomenology",
    language: str = "en",
) -> dict[str, object]:
    return {
        "title": title,
        "authors": authors or ["Silva, A."],
        "year": year,
        "doi": doi,
        "publication": publication,
        "archive_url": archive_url,
        "category": category,
        "language": language,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert PhilArchiveAdapter(_FakeHttpClient()).source_id == "philarchive"

    def test_source_tier(self) -> None:
        assert PhilArchiveAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = PhilArchiveAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_item_parsed(self) -> None:
        body = _payload(_item(title="A study", year=2023, doi="10.1/y"))
        adapter = PhilArchiveAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1/y"

    def test_authors_list_kept(self) -> None:
        body = _payload(_item(authors=["Silva, A.", "Pereira, B."]))
        adapter = PhilArchiveAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_publication_becomes_venue(self) -> None:
        body = _payload(_item(publication="Mind"))
        adapter = PhilArchiveAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].venue == "Mind"

    def test_archive_url_marks_is_oa(self) -> None:
        body = _payload(_item(archive_url="https://philarchive.org/archive/X2"))
        adapter = PhilArchiveAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True
        assert item.url_for_pdf == "https://philarchive.org/archive/X2"

    def test_no_archive_url_means_not_oa(self) -> None:
        body = _payload(_item(archive_url=None))
        adapter = PhilArchiveAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is False

    def test_language_passed_through(self) -> None:
        body = _payload(_item(language="pt"))
        adapter = PhilArchiveAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].language == "pt"


class TestQueryConstruction:
    def test_text_in_query(self) -> None:
        client = _FakeHttpClient(_empty())
        PhilArchiveAdapter(client, max_results=10).fetch(SearchQuery(text="phenomenology"))
        assert "phenomenology" in client.urls[0] or "phenomenology" in _decode(client.urls[0])

    def test_export_json(self) -> None:
        client = _FakeHttpClient(_empty())
        PhilArchiveAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert "export=json" in client.urls[0]

    def test_year_range_appended(self) -> None:
        client = _FakeHttpClient(_empty())
        PhilArchiveAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2018, year_end=2024)
        )
        decoded = _decode(client.urls[0])
        assert "start_year=2018" in decoded
        assert "end_year=2024" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_item(doi=f"10.1/{i}") for i in range(8)])
        adapter = PhilArchiveAdapter(_FakeHttpClient(body), max_results=5)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 5


def _decode(url: str) -> str:
    from urllib.parse import unquote_plus

    return unquote_plus(url)
