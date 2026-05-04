"""Unit tests for :class:`CrossrefAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.crossref import CrossrefAdapter


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
            return _empty_payload()


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"message": {"items": list(items)}}).encode("utf-8")


def _empty_payload() -> bytes:
    return _payload()


def _crossref_item(
    *,
    doi: str = "10.1234/x",
    title: str = "A title",
    year: int = 2024,
    authors: list[dict[str, str]] | None = None,
    container: str = "Some Journal",
    is_oa_license: bool = False,
) -> dict[str, object]:
    licenses = [{"URL": "https://creativecommons.org/licenses/by/4.0/"}] if is_oa_license else []
    return {
        "DOI": doi,
        "title": [title],
        "container-title": [container],
        "author": authors or [{"given": "Ana", "family": "Silva"}],
        "issued": {"date-parts": [[year]]},
        "language": "en",
        "license": licenses,
        "type": "journal-article",
        "URL": f"https://doi.org/{doi}",
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert CrossrefAdapter(_FakeHttpClient()).source_id == "crossref"

    def test_source_tier(self) -> None:
        assert CrossrefAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestEmptyResponse:
    def test_returns_empty_search_result(self) -> None:
        adapter = CrossrefAdapter(_FakeHttpClient(_empty_payload()))
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL


class TestParsing:
    def test_parses_a_single_item(self) -> None:
        body = _payload(_crossref_item(doi="10.1/a", title="A neat paper", year=2024))
        adapter = CrossrefAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 1
        item = result.items[0]
        assert item.title == "A neat paper"
        assert item.year == 2024
        assert item.doi == "10.1/a"
        assert item.venue == "Some Journal"

    def test_extracts_authors(self) -> None:
        authors = [
            {"given": "Ana", "family": "Silva"},
            {"given": "Bruno", "family": "Pereira"},
        ]
        body = _payload(_crossref_item(authors=authors))
        adapter = CrossrefAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items[0].authors == ("Ana Silva", "Bruno Pereira")

    def test_creative_commons_license_marks_is_oa(self) -> None:
        body = _payload(_crossref_item(is_oa_license=True))
        adapter = CrossrefAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items[0].is_oa is True

    def test_no_license_means_not_oa(self) -> None:
        body = _payload(_crossref_item(is_oa_license=False))
        adapter = CrossrefAdapter(_FakeHttpClient(body), max_per_page=10, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.items[0].is_oa is False


class TestQueryConstruction:
    def test_text_query_appears_in_url(self) -> None:
        client = _FakeHttpClient(_empty_payload())
        adapter = CrossrefAdapter(client, max_per_page=10, max_results=10)
        adapter.fetch(SearchQuery(text="letramento digital"))
        assert "query" in client.urls[0]
        assert "letramento" in client.urls[0] or "letramento" in _decode(client.urls[0])

    def test_year_range_translates_to_filter(self) -> None:
        client = _FakeHttpClient(_empty_payload())
        adapter = CrossrefAdapter(client, max_per_page=10, max_results=10)
        adapter.fetch(SearchQuery(text="x", year_start=2018, year_end=2024))
        decoded = _decode(client.urls[0])
        assert "from-pub-date:2018-01-01" in decoded
        assert "until-pub-date:2024-12-31" in decoded


class TestPagination:
    def test_paginates_until_empty_response(self) -> None:
        page1 = _payload(*[_crossref_item(doi=f"10.1/{i}", title=f"t{i}") for i in range(3)])
        client = _FakeHttpClient(page1, _empty_payload())
        adapter = CrossrefAdapter(client, max_per_page=3, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 3

    def test_stops_at_max_results(self) -> None:
        page = _payload(*[_crossref_item(doi=f"10.1/{i}", title=f"t{i}") for i in range(5)])
        client = _FakeHttpClient(page, page, page)
        adapter = CrossrefAdapter(client, max_per_page=5, max_results=8)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 8


def _decode(url: str) -> str:
    from urllib.parse import unquote_plus

    return unquote_plus(url.split("?", 1)[1] if "?" in url else "")
