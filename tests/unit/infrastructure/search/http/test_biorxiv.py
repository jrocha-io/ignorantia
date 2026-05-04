"""Unit tests for :class:`BioRxivAdapter` and :class:`MedRxivAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.biorxiv import BioRxivAdapter, MedRxivAdapter


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
    return json.dumps({"collection": []}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"collection": list(items), "messages": [{}]}).encode("utf-8")


def _preprint(
    *,
    doi: str = "10.1101/2024.01.02.345",
    title: str = "Digital health intervention",
    abstract: str = "We study digital health.",
    authors: str = "Silva, A.; Pereira, B.",
    date: str = "2024-04-12",
) -> dict[str, object]:
    return {
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "date": date,
    }


class TestBioRxivMetadata:
    def test_source_id(self) -> None:
        assert BioRxivAdapter(_FakeHttpClient()).source_id == "biorxiv"

    def test_source_tier(self) -> None:
        assert BioRxivAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestMedRxivMetadata:
    def test_source_id(self) -> None:
        assert MedRxivAdapter(_FakeHttpClient()).source_id == "medrxiv"

    def test_source_tier(self) -> None:
        assert MedRxivAdapter(_FakeHttpClient()).source_tier is Tier.TIER1

    def test_medrxiv_url_uses_medrxiv_server(self) -> None:
        client = _FakeHttpClient(_empty())
        MedRxivAdapter(client, max_pages=1).fetch(
            SearchQuery(text="x", year_start=2023, year_end=2024)
        )
        assert "/medrxiv/" in client.urls[0]


class TestParsing:
    def test_empty_response(self) -> None:
        adapter = BioRxivAdapter(_FakeHttpClient(_empty()), max_pages=1)
        result = adapter.fetch(SearchQuery(text="x", year_start=2023, year_end=2024))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_filters_by_query_in_title_or_abstract(self) -> None:
        body = _payload(
            _preprint(title="Digital health intervention", abstract="..."),
            _preprint(title="Quantum chromodynamics", abstract="Unrelated"),
        )
        adapter = BioRxivAdapter(_FakeHttpClient(body, _empty()), max_pages=2)
        result = adapter.fetch(SearchQuery(text="digital", year_start=2024, year_end=2024))
        assert len(result.items) == 1
        assert "digital" in result.items[0].title.lower()

    def test_authors_split_by_semicolon(self) -> None:
        body = _payload(_preprint(authors="Silva, A.; Pereira, B.; Costa, C."))
        adapter = BioRxivAdapter(_FakeHttpClient(body, _empty()), max_pages=2)
        result = adapter.fetch(SearchQuery(text="digital", year_start=2024, year_end=2024))
        assert result.items[0].authors == ("Silva, A.", "Pereira, B.", "Costa, C.")

    def test_year_extracted_from_date(self) -> None:
        body = _payload(_preprint(date="2023-04-12"))
        adapter = BioRxivAdapter(_FakeHttpClient(body, _empty()), max_pages=2)
        result = adapter.fetch(SearchQuery(text="digital", year_start=2023, year_end=2024))
        assert result.items[0].year == 2023

    def test_pdf_url_built_from_doi(self) -> None:
        body = _payload(_preprint(doi="10.1101/2024.05.06.789"))
        adapter = BioRxivAdapter(_FakeHttpClient(body, _empty()), max_pages=2)
        result = adapter.fetch(SearchQuery(text="digital", year_start=2024, year_end=2024))
        url = result.items[0].url_for_pdf
        assert url is not None
        assert "10.1101/2024.05.06.789" in url

    def test_items_marked_as_oa(self) -> None:
        body = _payload(_preprint())
        adapter = BioRxivAdapter(_FakeHttpClient(body, _empty()), max_pages=2)
        result = adapter.fetch(SearchQuery(text="digital", year_start=2024, year_end=2024))
        assert result.items[0].is_oa is True


class TestUrlConstruction:
    def test_url_includes_date_range(self) -> None:
        client = _FakeHttpClient(_empty())
        BioRxivAdapter(client, max_pages=1).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2022)
        )
        assert "/biorxiv/2020-01-01/2022-12-31/" in client.urls[0]


class TestPagination:
    def test_paginates_via_cursor(self) -> None:
        page1 = _payload(_preprint(doi="10.1101/a", title="Match"))
        page2 = _payload(_preprint(doi="10.1101/b", title="Match again"))
        client = _FakeHttpClient(page1, page2, _empty())
        adapter = BioRxivAdapter(client, max_pages=3)
        result = adapter.fetch(SearchQuery(text="match", year_start=2024, year_end=2024))
        assert len(result.items) == 2

    def test_stops_when_collection_empty(self) -> None:
        client = _FakeHttpClient(_empty())
        adapter = BioRxivAdapter(client, max_pages=5)
        adapter.fetch(SearchQuery(text="x", year_start=2024, year_end=2024))
        assert len(client.urls) == 1
