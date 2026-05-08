"""Unit tests for ``_CrossrefMemberAdapter`` shared base + Sage/ACM concretes."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.acm_full import AcmFullAdapter
from ignorantia.infrastructure.search.http.sage_full import SageFullAdapter
from ignorantia.infrastructure.search.http.wiley_tdm import WileyTdmAdapter


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
    return json.dumps({"message": {"items": [], "total-results": 0}}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"message": {"items": list(items), "total-results": len(items)}}).encode(
        "utf-8"
    )


def _record(
    *,
    title: str = "ACM paper",
    authors: list[dict[str, str]] | None = None,
    year: int = 2024,
    doi: str = "10.1145/x",
    issn: str = "1234-5678",
    venue: str = "ACM Computing Surveys",
    pub_type: str = "journal-article",
) -> dict[str, object]:
    return {
        "title": [title],
        "author": authors or [{"given": "Ana", "family": "Silva"}],
        "issued": {"date-parts": [[year]]},
        "DOI": doi,
        "ISSN": [issn],
        "container-title": [venue],
        "type": pub_type,
        "URL": f"https://doi.org/{doi}",
        "language": "en",
    }


class TestSageMetadata:
    def test_source_id(self) -> None:
        assert SageFullAdapter(_FakeHttpClient()).source_id == "sage_full"

    def test_source_tier(self) -> None:
        assert SageFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestAcmMetadata:
    def test_source_id(self) -> None:
        assert AcmFullAdapter(_FakeHttpClient()).source_id == "acm_full"

    def test_source_tier(self) -> None:
        assert AcmFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestWileyTdmMetadata:
    def test_source_id(self) -> None:
        assert WileyTdmAdapter(_FakeHttpClient()).source_id == "wiley_tdm"

    def test_source_tier(self) -> None:
        assert WileyTdmAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestMemberFilterDiffersByPublisher:
    def test_sage_uses_member_179(self) -> None:
        client = _FakeHttpClient(_empty())
        SageFullAdapter(client, api_key="K", max_results=10).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        assert "member:179" in unquote_plus(client.urls[0])

    def test_acm_uses_member_320(self) -> None:
        client = _FakeHttpClient(_empty())
        AcmFullAdapter(client, api_key="K", max_results=10).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        assert "member:320" in unquote_plus(client.urls[0])

    def test_wiley_uses_member_311(self) -> None:
        client = _FakeHttpClient(_empty())
        WileyTdmAdapter(client, api_key="K", max_results=10).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        assert "member:311" in unquote_plus(client.urls[0])


class TestParsing:
    def test_no_credentials_yields_real_error(self) -> None:
        result = SageFullAdapter(_FakeHttpClient()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR

    def test_successful_fetch_returns_real(self) -> None:
        body = _payload(_record(title="A study", year=2023, doi="10.1145/y"))
        adapter = SageFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert result.items[0].title == "A study"
        assert result.items[0].year == 2023

    def test_authors_combined_family_given(self) -> None:
        body = _payload(
            _record(
                authors=[
                    {"given": "Ana", "family": "Silva"},
                    {"given": "Bruno", "family": "Pereira"},
                ]
            )
        )
        adapter = AcmFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, Ana", "Pereira, Bruno")

    def test_doi_extracted(self) -> None:
        body = _payload(_record(doi="10.1145/abc"))
        adapter = AcmFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.doi == "10.1145/abc"

    def test_issn_first_element(self) -> None:
        body = _payload(_record(issn="0360-0300"))
        adapter = SageFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.issn == "0360-0300"

    def test_publication_type_kept(self) -> None:
        body = _payload(_record(pub_type="proceedings-article"))
        adapter = AcmFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.publication_type == "proceedings-article"

    def test_paywall_items_marked_not_oa(self) -> None:
        body = _payload(_record())
        adapter = AcmFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is False


class TestQueryConstruction:
    def test_year_range_appended_to_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        SageFullAdapter(client, api_key="K", max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "from-pub-date:2020-01-01" in decoded
        assert "until-pub-date:2024-12-31" in decoded
