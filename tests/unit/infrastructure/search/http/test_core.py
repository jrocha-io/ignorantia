"""Unit tests for :class:`CoreAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.core import CoreAdapter


class _FakePostHttp:
    def __init__(self, *bodies: bytes) -> None:
        self._bodies: Iterator[bytes] = iter(bodies)
        self.urls: list[str] = []
        self.bodies: list[bytes] = []
        self.headers: list[dict[str, str] | None] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("CORE adapter must use POST")

    def post(
        self,
        url: str,
        *,
        data: bytes,
        headers: object | None = None,
    ) -> bytes:
        self.urls.append(url)
        self.bodies.append(data)
        self.headers.append(headers if isinstance(headers, dict) else None)
        try:
            return next(self._bodies)
        except StopIteration:
            return _empty()


def _empty() -> bytes:
    return json.dumps({"results": []}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"results": list(items), "totalHits": len(items)}).encode("utf-8")


def _item(
    *,
    title: str = "Open repository study",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1234/core.42",
    publisher: str = "Open Press",
    pdf_url: str | None = "https://core.ac.uk/download/pdf/42.pdf",
    repository: str = "Repo X",
) -> dict[str, object]:
    name_list = [{"name": n} for n in (authors or ["Silva A"])]
    return {
        "title": title,
        "authors": name_list,
        "yearPublished": year,
        "doi": doi,
        "publisher": publisher,
        "downloadUrl": pdf_url,
        "dataProviders": [{"name": repository}],
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert CoreAdapter(_FakePostHttp()).source_id == "core"

    def test_source_tier(self) -> None:
        assert CoreAdapter(_FakePostHttp()).source_tier is Tier.TIER0


class TestParsing:
    def test_empty_response(self) -> None:
        result = CoreAdapter(_FakePostHttp(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_item_parsed(self) -> None:
        body = _payload(_item(title="A study", year=2023, doi="10.1/y"))
        item = (
            CoreAdapter(_FakePostHttp(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1/y"

    def test_authors_extracted(self) -> None:
        body = _payload(_item(authors=["Smith J", "Doe A"]))
        item = (
            CoreAdapter(_FakePostHttp(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.authors == ("Smith J", "Doe A")

    def test_pdf_url_extracted(self) -> None:
        body = _payload(_item(pdf_url="https://core.ac.uk/download/pdf/zz.pdf"))
        item = (
            CoreAdapter(_FakePostHttp(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.url_for_pdf == "https://core.ac.uk/download/pdf/zz.pdf"

    def test_is_oa_true_because_core_indexes_oa_only(self) -> None:
        body = _payload(_item())
        item = (
            CoreAdapter(_FakePostHttp(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.is_oa is True


class TestRequestShape:
    def test_uses_post_to_search_works(self) -> None:
        client = _FakePostHttp(_empty())
        CoreAdapter(client).fetch(SearchQuery(text="x"))
        assert client.urls[0] == "https://api.core.ac.uk/v3/search/works"

    def test_body_includes_query_and_limit(self) -> None:
        client = _FakePostHttp(_empty())
        CoreAdapter(client, max_results=25).fetch(SearchQuery(text="literacy"))
        body = json.loads(client.bodies[0].decode("utf-8"))
        assert body["q"] == "literacy"
        assert body["limit"] == 25

    def test_year_range_added_to_q(self) -> None:
        client = _FakePostHttp(_empty())
        CoreAdapter(client).fetch(SearchQuery(text="x", year_start=2020, year_end=2024))
        body = json.loads(client.bodies[0].decode("utf-8"))
        assert "yearPublished>=2020" in body["q"]
        assert "yearPublished<=2024" in body["q"]

    def test_content_type_is_application_json(self) -> None:
        client = _FakePostHttp(_empty())
        CoreAdapter(client).fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("Content-Type") == "application/json"

    def test_authorization_header_set_when_api_key_provided(self) -> None:
        client = _FakePostHttp(_empty())
        CoreAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("Authorization") == "Bearer K1"

    def test_no_authorization_header_without_key(self) -> None:
        client = _FakePostHttp(_empty())
        CoreAdapter(client).fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert "Authorization" not in client.headers[0]

    def test_limit_capped_at_100(self) -> None:
        client = _FakePostHttp(_empty())
        CoreAdapter(client, max_results=500).fetch(SearchQuery(text="x"))
        body = json.loads(client.bodies[0].decode("utf-8"))
        assert body["limit"] == 100


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_item(title=f"t{n}") for n in range(8)])
        adapter = CoreAdapter(_FakePostHttp(body), max_results=5)
        assert len(adapter.fetch(SearchQuery(text="x")).items) == 5
