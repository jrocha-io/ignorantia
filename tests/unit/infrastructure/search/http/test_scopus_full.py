"""Unit tests for :class:`ScopusFullAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.error import HTTPError

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.scopus_full import ScopusFullAdapter


class _FakeHttpClient:
    def __init__(self, *outcomes: object) -> None:
        self._outcomes: Iterator[object] = iter(outcomes)
        self.urls: list[str] = []
        self.headers: list[dict[str, str] | None] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        self.urls.append(url)
        self.headers.append(headers if isinstance(headers, dict) else None)
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
    return json.dumps({"search-results": {"entry": []}}).encode("utf-8")


def _payload(*entries: dict[str, object]) -> bytes:
    return json.dumps(
        {"search-results": {"entry": list(entries), "opensearch:totalResults": len(entries)}}
    ).encode("utf-8")


def _entry(
    *,
    title: str = "Predictive maintenance",
    creator: str = "Silva, A.",
    cover_date: str = "2024-04-12",
    doi: str = "10.1234/x",
    issn: str = "1234-5678",
    venue: str = "Some Journal",
    open_access: bool = False,
) -> dict[str, object]:
    return {
        "dc:title": title,
        "dc:creator": creator,
        "prism:coverDate": cover_date,
        "prism:doi": doi,
        "prism:issn": issn,
        "prism:publicationName": venue,
        "subtype": "ar",
        "openaccess": "1" if open_access else "0",
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert ScopusFullAdapter(_FakeHttpClient()).source_id == "scopus_full"

    def test_source_tier(self) -> None:
        assert ScopusFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestNoCredentials:
    def test_returns_real_error_when_no_key(self) -> None:
        adapter = ScopusFullAdapter(_FakeHttpClient())
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()


class TestKeyMode:
    def test_api_key_passed_in_x_els_header(self) -> None:
        client = _FakeHttpClient(_empty())
        ScopusFullAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("X-ELS-APIKey") == "K1"

    def test_successful_fetch_returns_real(self) -> None:
        body = _payload(_entry(title="A study", doi="10.1/a"))
        adapter = ScopusFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert len(result.items) == 1
        assert result.items[0].title == "A study"

    def test_open_access_flag_translated(self) -> None:
        body = _payload(_entry(open_access=True))
        adapter = ScopusFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True

    def test_year_extracted_from_cover_date(self) -> None:
        body = _payload(_entry(cover_date="2023-06-15"))
        adapter = ScopusFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.year == 2023


class TestCascadeOnNetworkErrors:
    def test_unauthorised_falls_to_proxy_unsupported_then_error(self) -> None:
        err = HTTPError("u", 401, "unauth", hdrs=None, fp=None)  # type: ignore[arg-type]
        adapter = ScopusFullAdapter(_FakeHttpClient(err), api_key="K", proxy_host="P")
        result = adapter.fetch(SearchQuery(text="x"))
        # Scopus has no proxy implementation → falls through to REAL_ERROR
        assert result.method is Method.REAL_ERROR


class TestQueryConstruction:
    def test_year_range_appended_with_pubyear(self) -> None:
        client = _FakeHttpClient(_empty())
        ScopusFullAdapter(client, api_key="K", max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "PUBYEAR > 2019" in decoded
        assert "PUBYEAR < 2025" in decoded
