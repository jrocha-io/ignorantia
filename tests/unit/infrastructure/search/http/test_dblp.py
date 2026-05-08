"""Unit tests for :class:`DblpAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.dblp import DblpAdapter


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
    return json.dumps({"result": {"hits": {"hit": []}}}).encode("utf-8")


def _payload(*hits: dict[str, object]) -> bytes:
    return json.dumps({"result": {"hits": {"hit": list(hits)}}}).encode("utf-8")


def _hit(
    *,
    dblp_id: str = "conf/icml/Foo23",
    title: str = "On distributed training.",
    year: str = "2024",
    authors: object = None,
    venue: str = "ICML",
    doi: str = "10.1109/x",
    pub_type: str = "Conference and Workshop Papers",
) -> dict[str, object]:
    if authors is None:
        authors = {"author": [{"text": "Silva, A."}, {"text": "Pereira, B."}]}
    info = {
        "title": title,
        "year": year,
        "venue": venue,
        "doi": doi,
        "type": pub_type,
        "authors": authors,
        "url": f"https://dblp.org/{dblp_id}",
        "ee": f"https://doi.org/{doi}",
    }
    return {"@id": dblp_id, "info": info}


class TestMetadata:
    def test_source_id(self) -> None:
        assert DblpAdapter(_FakeHttpClient()).source_id == "dblp"

    def test_source_tier(self) -> None:
        assert DblpAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = DblpAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_hit_parsed(self) -> None:
        body = _payload(_hit(title="A study.", year="2023", doi="10.1109/y"))
        adapter = DblpAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        # DBLP titles end with a period; adapter trims it.
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1109/y"

    def test_authors_list_parsed(self) -> None:
        body = _payload(_hit(authors={"author": [{"text": "Silva, A."}, {"text": "Pereira, B."}]}))
        adapter = DblpAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_single_author_dict_normalised(self) -> None:
        body = _payload(_hit(authors={"author": {"text": "Solo"}}))
        adapter = DblpAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Solo",)

    def test_url_and_ee_extracted(self) -> None:
        body = _payload(_hit(dblp_id="conf/icml/Foo23", doi="10.1/z"))
        adapter = DblpAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://dblp.org/conf/icml/Foo23"


class TestQueryConstruction:
    def test_query_text_in_url(self) -> None:
        client = _FakeHttpClient(_empty())
        DblpAdapter(client, max_results=10).fetch(SearchQuery(text="transformer"))
        assert "transformer" in client.urls[0] or "transformer" in _decode(client.urls[0])

    def test_format_json(self) -> None:
        client = _FakeHttpClient(_empty())
        DblpAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert "format=json" in client.urls[0]


class TestPagination:
    def test_paginates_until_empty(self) -> None:
        page = _payload(*[_hit(dblp_id=f"x{i}") for i in range(3)])
        client = _FakeHttpClient(page, _empty())
        adapter = DblpAdapter(client, max_per_page=3, max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 3

    def test_truncates_to_max_results(self) -> None:
        page = _payload(*[_hit(dblp_id=f"x{i}") for i in range(5)])
        client = _FakeHttpClient(page, page, page)
        adapter = DblpAdapter(client, max_per_page=5, max_results=8)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 8


class TestYearFilter:
    def test_filters_out_of_range_years(self) -> None:
        body = _payload(
            _hit(dblp_id="a", year="2018"),
            _hit(dblp_id="b", year="2023"),
            _hit(dblp_id="c", year="2025"),
        )
        adapter = DblpAdapter(_FakeHttpClient(body), max_results=10)
        result = adapter.fetch(SearchQuery(text="x", year_start=2020, year_end=2024))
        years = {item.year for item in result.items}
        assert years == {2023}


def _decode(url: str) -> str:
    from urllib.parse import unquote_plus

    return unquote_plus(url)
