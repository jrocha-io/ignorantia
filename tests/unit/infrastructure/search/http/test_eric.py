"""Unit tests for :class:`EricAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.eric import EricAdapter


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
    eric_id: str = "EJ1234567",
    title: str = "Digital literacy curricula",
    authors: list[str] | None = None,
    year: int = 2024,
    source: str | list[str] = "Adult Education Quarterly",
    peerreviewed: str = "T",
) -> dict[str, object]:
    return {
        "id": eric_id,
        "title": title,
        "author": authors or ["Mock, A.", "Mock, B."],
        "publicationdateyear": str(year),
        "publicationtype": "Journal Articles",
        "description": "Description of the paper.",
        "source": source,
        "peerreviewed": peerreviewed,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert EricAdapter(_FakeHttpClient()).source_id == "eric"

    def test_source_tier(self) -> None:
        assert EricAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = EricAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_doc(self) -> None:
        body = _payload(_doc(eric_id="EJ999", title="A study"))
        item = (
            EricAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.title == "A study"
        assert item.url_for_pdf == "https://files.eric.ed.gov/fulltext/EJ999.pdf"

    def test_authors_from_list(self) -> None:
        body = _payload(_doc(authors=["Smith, A.", "Doe, B."]))
        item = (
            EricAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.authors == ("Smith, A.", "Doe, B.")

    def test_authors_from_string(self) -> None:
        body = _payload(_doc(authors="Single author"))  # type: ignore[arg-type]
        item = (
            EricAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.authors == ("Single author",)

    def test_year_extracted(self) -> None:
        body = _payload(_doc(year=2022))
        item = (
            EricAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.year == 2022

    def test_source_list_first_becomes_venue(self) -> None:
        body = _payload(_doc(source=["Journal X", "Alt"]))
        item = (
            EricAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.venue == "Journal X"

    def test_peerreviewed_t_marks_is_oa(self) -> None:
        body = _payload(_doc(peerreviewed="T"))
        item = (
            EricAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.is_oa is True

    def test_peerreviewed_f_means_not_oa(self) -> None:
        body = _payload(_doc(peerreviewed="F"))
        item = (
            EricAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.is_oa is False


class TestQueryConstruction:
    def test_year_range_in_search_query(self) -> None:
        client = _FakeHttpClient(_empty())
        EricAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "publicationdateyear" in decoded
        assert "2020" in decoded
        assert "2024" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_doc(eric_id=f"EJ{i:04d}") for i in range(8)])
        result = EricAdapter(_FakeHttpClient(body), max_results=5).fetch(SearchQuery(text="x"))
        assert len(result.items) == 5
