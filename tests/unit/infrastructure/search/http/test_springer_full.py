"""Unit tests for :class:`SpringerFullAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.springer_full import SpringerFullAdapter


class _FakeHttpClient:
    def __init__(self, *outcomes: object) -> None:
        self._outcomes: Iterator[object] = iter(outcomes)
        self.urls: list[str] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        del headers
        self.urls.append(url)
        try:
            outcome = next(self._outcomes)
        except StopIteration:
            return _empty()
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, bytes):
            return outcome
        raise RuntimeError(f"unexpected outcome: {outcome!r}")


def _empty() -> bytes:
    return json.dumps({"records": []}).encode("utf-8")


def _payload(*records: dict[str, object]) -> bytes:
    return json.dumps({"records": list(records)}).encode("utf-8")


def _record(
    *,
    title: str = "Smart farming",
    creators: list[str] | None = None,
    pub_date: str = "2024-04-12",
    doi: str = "10.1007/x",
    issn: str = "1234-5678",
    venue: str = "Smart Agriculture",
    is_oa: bool = False,
    pdf_url: str | None = "https://link.springer.com/x.pdf",
    landing_url: str = "https://link.springer.com/x",
    language: str = "en",
) -> dict[str, object]:
    urls: list[dict[str, str]] = [{"format": "pdf", "value": pdf_url}] if pdf_url else []
    urls.append({"format": "html", "value": landing_url})
    return {
        "title": title,
        "creators": [{"creator": n} for n in (creators or ["Silva, A."])],
        "publicationDate": pub_date,
        "doi": doi,
        "issn": issn,
        "publicationName": venue,
        "openaccess": "true" if is_oa else "false",
        "url": urls,
        "language": language,
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert SpringerFullAdapter(_FakeHttpClient()).source_id == "springer_full"

    def test_source_tier(self) -> None:
        assert SpringerFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestKeyMode:
    def test_no_credentials_yields_real_error(self) -> None:
        result = SpringerFullAdapter(_FakeHttpClient()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR

    def test_apikey_in_query(self) -> None:
        client = _FakeHttpClient(_empty())
        SpringerFullAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert "api_key=K1" in client.urls[0]

    def test_successful_fetch(self) -> None:
        body = _payload(_record(title="Smart farming review", doi="10.1007/y"))
        adapter = SpringerFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert result.items[0].title == "Smart farming review"
        assert result.items[0].doi == "10.1007/y"

    def test_creators_extracted(self) -> None:
        body = _payload(_record(creators=["Silva, A.", "Pereira, B."]))
        adapter = SpringerFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_pdf_url_extracted_from_url_array(self) -> None:
        body = _payload(_record(pdf_url="https://link.springer.com/y.pdf"))
        adapter = SpringerFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://link.springer.com/y.pdf"

    def test_open_access_translated(self) -> None:
        body = _payload(_record(is_oa=True))
        adapter = SpringerFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is True


class TestQueryConstruction:
    def test_year_range_appended_to_query(self) -> None:
        client = _FakeHttpClient(_empty())
        SpringerFullAdapter(client, api_key="K", max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "onlinedatefrom:2020-01-01" in decoded
        assert "onlinedateto:2024-12-31" in decoded
