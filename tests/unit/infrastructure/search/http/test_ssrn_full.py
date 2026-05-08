"""Unit tests for :class:`SsrnFullAdapter` (OpenAlex-backed)."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.ssrn_full import SsrnFullAdapter


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
    return json.dumps({"results": [], "meta": {"count": 0}}).encode("utf-8")


def _payload(*records: dict[str, object]) -> bytes:
    return json.dumps({"results": list(records), "meta": {"count": len(records)}}).encode("utf-8")


def _record(
    *,
    work_id: str = "W123",
    title: str = "Working paper on monetary policy",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "https://doi.org/10.2139/ssrn.999",
    venue: str = "SSRN Working Paper Series",
    is_oa: bool = True,
    pdf_url: str | None = "https://papers.ssrn.com/paper.pdf",
    pub_type: str = "preprint",
) -> dict[str, object]:
    name_list = [{"author": {"display_name": n}} for n in (authors or ["Silva A"])]
    return {
        "id": f"https://openalex.org/{work_id}",
        "title": title,
        "authorships": name_list,
        "publication_year": year,
        "doi": doi,
        "primary_location": {
            "source": {"display_name": venue, "id": "https://openalex.org/S4306400573"},
            "pdf_url": pdf_url,
        },
        "open_access": {"is_oa": is_oa},
        "language": "en",
        "type": pub_type,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert SsrnFullAdapter(_FakeHttpClient()).source_id == "ssrn_full"

    def test_source_tier(self) -> None:
        assert SsrnFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestParsing:
    def test_empty_response(self) -> None:
        result = SsrnFullAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_record_parsed(self) -> None:
        body = _payload(_record(title="A study", year=2023, doi="https://doi.org/10.2139/ssrn.1"))
        adapter = SsrnFullAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.2139/ssrn.1"

    def test_authors_extracted(self) -> None:
        body = _payload(_record(authors=["Smith J", "Doe A"]))
        adapter = SsrnFullAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Smith J", "Doe A")

    def test_pdf_url_extracted(self) -> None:
        body = _payload(_record(pdf_url="https://papers.ssrn.com/zz.pdf"))
        adapter = SsrnFullAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://papers.ssrn.com/zz.pdf"

    def test_is_oa_propagated(self) -> None:
        body = _payload(_record(is_oa=True))
        adapter = SsrnFullAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is True

    def test_doi_strips_url_prefix(self) -> None:
        body = _payload(_record(doi="https://doi.org/10.2139/ssrn.42"))
        adapter = SsrnFullAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].doi == "10.2139/ssrn.42"


class TestQueryConstruction:
    def test_search_param_has_query_text(self) -> None:
        client = _FakeHttpClient(_empty())
        SsrnFullAdapter(client).fetch(SearchQuery(text="monetary policy"))
        from urllib.parse import unquote_plus

        assert "search=monetary policy" in unquote_plus(client.urls[0])

    def test_filter_pins_ssrn_source(self) -> None:
        client = _FakeHttpClient(_empty())
        SsrnFullAdapter(client).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "primary_location.source.id:S4306400573" in decoded

    def test_year_range_appended_to_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        SsrnFullAdapter(client).fetch(SearchQuery(text="x", year_start=2020, year_end=2024))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "from_publication_date:2020-01-01" in decoded
        assert "to_publication_date:2024-12-31" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_record(work_id=f"W{n}") for n in range(8)])
        adapter = SsrnFullAdapter(_FakeHttpClient(body), max_results=5)
        assert len(adapter.fetch(SearchQuery(text="x")).items) == 5
