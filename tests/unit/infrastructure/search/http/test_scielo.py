"""Unit tests for :class:`ScieloAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.scielo import ScieloAdapter


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
    return json.dumps({"response": {"docs": []}}).encode("utf-8")


def _payload(*docs: dict[str, object]) -> bytes:
    return json.dumps({"response": {"docs": list(docs)}}).encode("utf-8")


def _doc(
    *,
    title: str = "Letramento digital",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1590/x",
    venue: str = "Ciência & Saúde Coletiva",
    language: str = "pt",
    issn: str = "1413-8123",
) -> dict[str, object]:
    return {
        "id": "S0102-311X-x",
        "title": title,
        "abstract": "Resumo do artigo.",
        "author": authors or ["Silva, A.", "Pereira, B."],
        "year": year,
        "source": venue,
        "doi": doi,
        "language": language,
        "url": f"https://scielo.br/{doi}",
        "issn": issn,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert ScieloAdapter(_FakeHttpClient()).source_id == "scielo"

    def test_source_tier(self) -> None:
        assert ScieloAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = ScieloAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_doc_parsed(self) -> None:
        body = _payload(_doc(title="Estudo X", year=2023, doi="10.1590/y"))
        adapter = ScieloAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "Estudo X"
        assert item.year == 2023
        assert item.doi == "10.1590/y"

    def test_authors_parsed_from_list(self) -> None:
        body = _payload(_doc(authors=["Silva, A.", "Pereira, B."]))
        adapter = ScieloAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_venue_extracted(self) -> None:
        body = _payload(_doc(venue="Cadernos de Saúde Pública"))
        adapter = ScieloAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].venue == "Cadernos de Saúde Pública"

    def test_issn_extracted(self) -> None:
        body = _payload(_doc(issn="1234-5678"))
        adapter = ScieloAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].issn == "1234-5678"

    def test_items_marked_as_oa(self) -> None:
        body = _payload(_doc())
        adapter = ScieloAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is True


class TestQueryConstruction:
    def test_year_range_appended_via_in_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        ScieloAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2022)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "in:" in decoded
        assert "2020" in decoded
        assert "2021" in decoded
        assert "2022" in decoded


class TestPagination:
    def test_paginates_until_empty_page(self) -> None:
        body = _payload(*[_doc(title=f"t{i}") for i in range(3)])
        client = _FakeHttpClient(body, _empty())
        adapter = ScieloAdapter(client, max_per_page=3, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 3

    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_doc(title=f"t{i}") for i in range(5)])
        client = _FakeHttpClient(body, body, body)
        adapter = ScieloAdapter(client, max_per_page=5, max_results=8)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 8
