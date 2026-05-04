"""Unit tests for :class:`WosFullAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.wos_full import WosFullAdapter


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
    return json.dumps({"hits": []}).encode("utf-8")


def _payload(*hits: dict[str, object]) -> bytes:
    return json.dumps({"hits": list(hits), "metadata": {"total": len(hits)}}).encode("utf-8")


def _hit(
    *,
    uid: str = "WOS:000123456789012",
    title: str = "Reliability analysis",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1234/x",
    issn: str = "1234-5678",
    journal: str = "IEEE Trans Reliab",
    doc_type: str = "Article",
) -> dict[str, object]:
    name_list = [{"displayName": n} for n in (authors or ["Silva, A."])]
    identifiers = [
        {"type": "issn", "value": issn},
        {"type": "doi", "value": doi},
    ]
    return {
        "uid": uid,
        "title": {"value": title},
        "names": {"authors": name_list},
        "source": {"publishYear": year, "sourceTitle": journal},
        "identifiers": identifiers,
        "documentTypes": [doc_type],
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert WosFullAdapter(_FakeHttpClient()).source_id == "wos_full"

    def test_source_tier(self) -> None:
        assert WosFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestKeyMode:
    def test_no_credentials_yields_real_error(self) -> None:
        result = WosFullAdapter(_FakeHttpClient()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR

    def test_x_apikey_header_set(self) -> None:
        client = _FakeHttpClient(_empty())
        WosFullAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("X-ApiKey") == "K1"

    def test_successful_fetch(self) -> None:
        body = _payload(_hit(uid="WOS:0001", title="A study", year=2023, doi="10.1/y"))
        adapter = WosFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        item = result.items[0]
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1/y"

    def test_authors_extracted_from_names_authors(self) -> None:
        body = _payload(_hit(authors=["Smith J", "Doe A"]))
        adapter = WosFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Smith J", "Doe A")

    def test_url_built_from_uid(self) -> None:
        body = _payload(_hit(uid="WOS:000999999"))
        adapter = WosFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://www.webofscience.com/wos/woscc/full-record/WOS:000999999"

    def test_first_document_type_becomes_publication_type(self) -> None:
        body = _payload(_hit(doc_type="Review"))
        adapter = WosFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].publication_type == "Review"


class TestQueryConstruction:
    def test_uses_topic_search_syntax(self) -> None:
        client = _FakeHttpClient(_empty())
        WosFullAdapter(client, api_key="K", max_results=10).fetch(SearchQuery(text="reliability"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "TS=(reliability)" in decoded

    def test_year_range_appended_with_py(self) -> None:
        client = _FakeHttpClient(_empty())
        WosFullAdapter(client, api_key="K", max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        assert "PY=2020-2024" in unquote_plus(client.urls[0])
