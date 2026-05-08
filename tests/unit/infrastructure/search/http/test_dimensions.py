"""Unit tests for :class:`DimensionsAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.dimensions import DimensionsAdapter


class _FakePostHttp:
    def __init__(self, *bodies: bytes) -> None:
        self._bodies: Iterator[bytes] = iter(bodies)
        self.urls: list[str] = []
        self.bodies: list[bytes] = []
        self.headers: list[dict[str, str] | None] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("Dimensions adapter must use POST")

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
    return json.dumps({"publications": []}).encode("utf-8")


def _payload(*pubs: dict[str, object]) -> bytes:
    return json.dumps({"publications": list(pubs)}).encode("utf-8")


def _pub(
    *,
    pub_id: str = "pub.1234567890",
    title: str = "Bibliometric analysis study",
    authors: list[tuple[str, str]] | None = None,
    year: int = 2024,
    doi: str = "10.1234/dim.42",
    journal: str = "Scientometrics",
) -> dict[str, object]:
    name_list = [
        {"first_name": fn, "last_name": ln} for fn, ln in (authors or [("Andrea", "Silva")])
    ]
    return {
        "id": pub_id,
        "title": title,
        "authors": name_list,
        "year": year,
        "doi": doi,
        "journal": {"title": journal},
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert DimensionsAdapter(_FakePostHttp()).source_id == "dimensions"

    def test_source_tier(self) -> None:
        assert DimensionsAdapter(_FakePostHttp()).source_tier is Tier.TIER2


class TestKeyMode:
    def test_no_credentials_yields_real_error(self) -> None:
        result = DimensionsAdapter(_FakePostHttp()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR

    def test_jwt_authorization_header(self) -> None:
        client = _FakePostHttp(_empty())
        DimensionsAdapter(client, api_key="JWT-abc").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("Authorization") == "JWT JWT-abc"

    def test_content_type_application_json(self) -> None:
        client = _FakePostHttp(_empty())
        DimensionsAdapter(client, api_key="K").fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("Content-Type") == "application/json"

    def test_url_is_dsl_endpoint(self) -> None:
        client = _FakePostHttp(_empty())
        DimensionsAdapter(client, api_key="K").fetch(SearchQuery(text="x"))
        assert client.urls[0] == "https://app.dimensions.ai/api/dsl/v2"

    def test_dsl_query_includes_search_term(self) -> None:
        client = _FakePostHttp(_empty())
        DimensionsAdapter(client, api_key="K").fetch(SearchQuery(text="literacy"))
        body = json.loads(client.bodies[0].decode("utf-8"))
        assert 'search publications for "literacy"' in body["query"]

    def test_dsl_query_year_range(self) -> None:
        client = _FakePostHttp(_empty())
        DimensionsAdapter(client, api_key="K").fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        body = json.loads(client.bodies[0].decode("utf-8"))
        assert "year in [2020:2024]" in body["query"]

    def test_dsl_query_limit_capped(self) -> None:
        client = _FakePostHttp(_empty())
        DimensionsAdapter(client, api_key="K", max_results=500).fetch(SearchQuery(text="x"))
        body = json.loads(client.bodies[0].decode("utf-8"))
        assert "limit 100" in body["query"]


class TestParsing:
    def test_single_publication(self) -> None:
        body = _payload(_pub(title="A study", year=2023, doi="10.1/y"))
        adapter = DimensionsAdapter(_FakePostHttp(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1/y"

    def test_authors_concatenated_first_last(self) -> None:
        body = _payload(_pub(authors=[("Jane", "Smith"), ("John", "Doe")]))
        adapter = DimensionsAdapter(_FakePostHttp(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Jane Smith", "John Doe")

    def test_venue_from_journal_title(self) -> None:
        body = _payload(_pub(journal="Scientometrics"))
        adapter = DimensionsAdapter(_FakePostHttp(body), api_key="K", max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].venue == "Scientometrics"

    def test_url_built_from_pub_id(self) -> None:
        body = _payload(_pub(pub_id="pub.999"))
        adapter = DimensionsAdapter(_FakePostHttp(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://app.dimensions.ai/details/publication/pub.999"

    def test_is_oa_false_paywall(self) -> None:
        body = _payload(_pub())
        adapter = DimensionsAdapter(_FakePostHttp(body), api_key="K", max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is False
