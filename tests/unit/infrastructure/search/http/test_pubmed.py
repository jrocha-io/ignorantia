"""Unit tests for :class:`PubMedAdapter`.

PubMed uses NCBI E-utilities: a 2-call protocol (esearch returns IDs,
esummary returns metadata for those IDs).
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http.pubmed import PubMedAdapter


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


def _esearch_payload(*pmids: str) -> bytes:
    return json.dumps({"esearchresult": {"idlist": list(pmids)}}).encode("utf-8")


def _esummary_payload(*records: dict[str, object]) -> bytes:
    by_id: dict[str, object] = {}
    for r in records:
        pmid = r.get("uid")
        if isinstance(pmid, str):
            by_id[pmid] = r
    return json.dumps({"result": by_id}).encode("utf-8")


def _summary_record(
    *,
    pmid: str = "30100001",
    title: str = "A study",
    authors: list[str] | None = None,
    pubdate: str = "2024 Apr 12",
    doi: str | None = "10.1234/x",
    pmcid: str | None = "PMC123",
    journal: str = "BMJ Open",
    pub_types: list[str] | None = None,
) -> dict[str, object]:
    article_ids: list[dict[str, str]] = []
    if doi:
        article_ids.append({"idtype": "doi", "value": doi})
    if pmcid:
        article_ids.append({"idtype": "pmc", "value": pmcid})
    return {
        "uid": pmid,
        "title": title,
        "authors": [{"name": n} for n in (authors or ["Silva A", "Pereira B"])],
        "pubdate": pubdate,
        "articleids": article_ids,
        "fulljournalname": journal,
        "pubtype": pub_types or ["Journal Article"],
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert PubMedAdapter(_FakeHttpClient()).source_id == "pubmed"

    def test_source_tier(self) -> None:
        assert PubMedAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestEsearchEsummaryProtocol:
    def test_empty_esearch_yields_no_items(self) -> None:
        client = _FakeHttpClient(_esearch_payload())
        result = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert result.items == ()
        # Only esearch is called when no PMIDs are returned
        assert len(client.urls) == 1
        assert "esearch.fcgi" in client.urls[0]

    def test_esearch_then_esummary(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("30100001"),
            _esummary_payload(_summary_record(pmid="30100001", title="A study")),
        )
        result = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x"))
        assert len(result.items) == 1
        assert result.items[0].title == "A study"
        assert "esearch.fcgi" in client.urls[0]
        assert "esummary.fcgi" in client.urls[1]


class TestParsing:
    def test_doi_extracted_from_articleids(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("1"),
            _esummary_payload(_summary_record(pmid="1", doi="10.1/a")),
        )
        item = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.doi == "10.1/a"

    def test_pmcid_marks_is_oa(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("1"),
            _esummary_payload(_summary_record(pmid="1", pmcid="PMC42")),
        )
        item = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True

    def test_no_pmcid_means_not_oa(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("1"),
            _esummary_payload(_summary_record(pmid="1", pmcid=None)),
        )
        item = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is False

    def test_year_extracted_from_pubdate(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("1"),
            _esummary_payload(_summary_record(pmid="1", pubdate="2023 Jan")),
        )
        item = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.year == 2023

    def test_authors_extracted(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("1"),
            _esummary_payload(_summary_record(pmid="1", authors=["Smith A", "Doe B"])),
        )
        item = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Smith A", "Doe B")

    def test_canonical_url_built_from_pmid(self) -> None:
        client = _FakeHttpClient(
            _esearch_payload("99"),
            _esummary_payload(_summary_record(pmid="99")),
        )
        item = PubMedAdapter(client, max_results=10).fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://pubmed.ncbi.nlm.nih.gov/99/"


class TestQueryConstruction:
    def test_year_range_appended_with_pdat(self) -> None:
        client = _FakeHttpClient(_esearch_payload())
        PubMedAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        assert "2020:2024[pdat]" in unquote_plus(client.urls[0])

    def test_api_key_passes_through(self) -> None:
        client = _FakeHttpClient(_esearch_payload())
        PubMedAdapter(client, max_results=10, api_key="test-key").fetch(SearchQuery(text="x"))
        assert "api_key=test-key" in client.urls[0]
