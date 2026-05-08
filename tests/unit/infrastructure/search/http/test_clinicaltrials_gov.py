"""Unit tests for :class:`ClinicalTrialsGovAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.clinicaltrials_gov import (
    ClinicalTrialsGovAdapter,
)


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
    return json.dumps({"studies": []}).encode("utf-8")


def _payload(*studies: dict[str, object]) -> bytes:
    return json.dumps({"studies": list(studies), "totalCount": len(studies)}).encode("utf-8")


def _study(
    *,
    nct_id: str = "NCT00000001",
    title: str = "Trial of intervention X",
    start_date: str = "2024-03-15",
    status: str = "Recruiting",
    study_type: str = "Interventional",
) -> dict[str, object]:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": title},
            "statusModule": {
                "overallStatus": status,
                "startDateStruct": {"date": start_date},
            },
            "designModule": {"studyType": study_type},
        }
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert ClinicalTrialsGovAdapter(_FakeHttpClient()).source_id == "clinicaltrials_gov"

    def test_source_tier(self) -> None:
        assert ClinicalTrialsGovAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = ClinicalTrialsGovAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_study_parsed(self) -> None:
        body = _payload(_study(title="A trial", start_date="2023-06-15"))
        adapter = ClinicalTrialsGovAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A trial"
        assert item.year == 2023

    def test_url_built_from_nct_id(self) -> None:
        body = _payload(_study(nct_id="NCT01234567"))
        adapter = ClinicalTrialsGovAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://clinicaltrials.gov/study/NCT01234567"

    def test_publication_type_is_trial_registration(self) -> None:
        body = _payload(_study())
        adapter = ClinicalTrialsGovAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.publication_type == "trial-registration"

    def test_is_oa_true_for_public_registry(self) -> None:
        body = _payload(_study())
        adapter = ClinicalTrialsGovAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is True

    def test_invalid_start_date_yields_no_year(self) -> None:
        body = _payload(_study(start_date=""))
        adapter = ClinicalTrialsGovAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].year is None


class TestQueryConstruction:
    def test_query_term_param(self) -> None:
        client = _FakeHttpClient(_empty())
        ClinicalTrialsGovAdapter(client).fetch(SearchQuery(text="diabetes"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "query.term=diabetes" in decoded

    def test_year_range_translates_to_filter_advanced(self) -> None:
        client = _FakeHttpClient(_empty())
        ClinicalTrialsGovAdapter(client).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "AREA[StartDate]RANGE[2020-01-01,2024-12-31]" in decoded

    def test_page_size_capped(self) -> None:
        client = _FakeHttpClient(_empty())
        ClinicalTrialsGovAdapter(client, max_results=200).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "pageSize=100" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_study(nct_id=f"NCT{n:08d}") for n in range(8)])
        adapter = ClinicalTrialsGovAdapter(_FakeHttpClient(body), max_results=5)
        assert len(adapter.fetch(SearchQuery(text="x")).items) == 5
