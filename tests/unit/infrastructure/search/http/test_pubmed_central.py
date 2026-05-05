"""Unit tests for :class:`PubMedCentralAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.pubmed_central import PubMedCentralAdapter


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
            return b'{"esearchresult": {"idlist": []}}'


def _esearch_payload(*pmcids: str) -> bytes:
    return json.dumps({"esearchresult": {"idlist": list(pmcids)}}).encode("utf-8")


def _esummary_payload(*records: dict[str, object]) -> bytes:
    by_id: dict[str, object] = {}
    for r in records:
        rid = r.get("uid")
        if isinstance(rid, str):
            by_id[rid] = r
    return json.dumps({"result": by_id}).encode("utf-8")


def _summary_record(
    *,
    pmcid: str = "PMC0123456",
    title: str = "A study",
    authors: list[str] | None = None,
    pubdate: str = "2024 Apr 12",
    doi: str | None = "10.1234/x",
    journal: str = "JMIR",
) -> dict[str, object]:
    article_ids: list[dict[str, str]] = [{"idtype": "pmc", "value": pmcid}]
    if doi:
        article_ids.append({"idtype": "doi", "value": doi})
    return {
        "uid": pmcid,
        "title": title,
        "authors": [{"name": n} for n in (authors or ["Silva A", "Pereira B"])],
        "pubdate": pubdate,
        "articleids": article_ids,
        "fulljournalname": journal,
        "pubtype": ["Journal Article"],
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert PubMedCentralAdapter(_FakeHttpClient()).source_id == "pubmed_central"

    def test_source_tier(self) -> None:
        assert PubMedCentralAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestProtocol:
    def test_db_pmc_in_esearch_url(self) -> None:
        client = _FakeHttpClient(_esearch_payload())
        PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert "db=pmc" in client.urls[0]
        assert "esearch.fcgi" in client.urls[0]

    def test_empty_esearch_skips_esummary(self) -> None:
        client = _FakeHttpClient(_esearch_payload())
        result = PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert len(client.urls) == 1


class TestParsing:
    def test_canonical_url_uses_pmc_full_record_path(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("PMC9876543"),
            _esummary_payload(_summary_record(pmcid="PMC9876543")),
        )
        item = PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9876543/"

    def test_pdf_url_uses_pmc_path(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("PMC42"),
            _esummary_payload(_summary_record(pmcid="PMC42")),
        )
        item = PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC42/"

    def test_items_always_marked_as_oa(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("PMC1"),
            _esummary_payload(_summary_record(pmcid="PMC1")),
        )
        item = PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True

    def test_doi_extracted(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("PMC1"),
            _esummary_payload(_summary_record(pmcid="PMC1", doi="10.1/y")),
        )
        item = PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.doi == "10.1/y"

    def test_year_from_pubdate(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("PMC1"),
            _esummary_payload(_summary_record(pmcid="PMC1", pubdate="2023 Jun 01")),
        )
        item = PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.year == 2023

    def test_method_is_real(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("PMC1"),
            _esummary_payload(_summary_record(pmcid="PMC1")),
        )
        result = PubMedCentralAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL


class TestQueryConstruction:
    def test_year_range_appended_with_pdat(self) -> None:
        client = _FakeHttpClient(_esearch_payload())
        PubMedCentralAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        assert "2020:2024[pdat]" in unquote_plus(client.urls[0])

    def test_api_key_passes_through(self) -> None:
        client = _FakeHttpClient(_esearch_payload())
        PubMedCentralAdapter(client, max_results=10, api_key="K").fetch(SearchQuery(text="x"))
        assert "api_key=K" in client.urls[0]
