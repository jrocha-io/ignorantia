"""Unit tests for :class:`EuropePmcAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.europepmc import EuropePmcAdapter


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
    return json.dumps({"resultList": {"result": []}, "hitCount": 0}).encode("utf-8")


def _payload(*items: dict[str, object], hit_count: int | None = None) -> bytes:
    body: dict[str, object] = {
        "resultList": {"result": list(items)},
        "hitCount": hit_count if hit_count is not None else len(items),
    }
    return json.dumps(body).encode("utf-8")


def _record(
    *,
    title: str = "A title",
    authors: str = "Silva, A., Pereira, B.",
    year: int = 2024,
    doi: str = "10.1234/x",
    pmcid: str | None = "PMC123",
    pmid: str = "30100001",
    is_oa: str = "Y",
    journal: str = "BMJ Open",
) -> dict[str, object]:
    return {
        "title": title,
        "authorString": authors,
        "pubYear": str(year),
        "doi": doi,
        "pmcid": pmcid,
        "pmid": pmid,
        "isOpenAccess": is_oa,
        "journalTitle": journal,
        "abstractText": "Abstract.",
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert EuropePmcAdapter(_FakeHttpClient()).source_id == "europepmc"

    def test_source_tier(self) -> None:
        assert EuropePmcAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = EuropePmcAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_record_parsed(self) -> None:
        body = _payload(_record(title="A study", year=2023, doi="10.1/a"))
        adapter = EuropePmcAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1/a"

    def test_authors_split_by_comma(self) -> None:
        body = _payload(_record(authors="Silva, A., Pereira, B., Costa, C."))
        adapter = EuropePmcAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert "Silva" in item.authors[0]

    def test_pmcid_yields_pmc_url(self) -> None:
        body = _payload(_record(pmcid="PMC9876", pmid="999"))
        adapter = EuropePmcAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://europepmc.org/article/PMC/PMC9876"

    def test_no_pmcid_falls_back_to_pmid_url(self) -> None:
        body = _payload(_record(pmcid=None, pmid="30100001"))
        adapter = EuropePmcAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://europepmc.org/article/MED/30100001"

    def test_open_access_flag_translated(self) -> None:
        body = _payload(_record(is_oa="N"))
        adapter = EuropePmcAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is False

    def test_journal_becomes_venue(self) -> None:
        body = _payload(_record(journal="Lancet"))
        adapter = EuropePmcAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].venue == "Lancet"


class TestQueryConstruction:
    def test_text_in_query(self) -> None:
        client = _FakeHttpClient(_empty())
        EuropePmcAdapter(client, max_results=10).fetch(SearchQuery(text="letramento"))
        assert "query=" in client.urls[0]

    def test_year_range_appended_as_pub_year_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        EuropePmcAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "PUB_YEAR:[2020 TO 2024]" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_record(doi=f"10.1/{i}") for i in range(8)])
        adapter = EuropePmcAdapter(_FakeHttpClient(body), max_results=5)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 5
