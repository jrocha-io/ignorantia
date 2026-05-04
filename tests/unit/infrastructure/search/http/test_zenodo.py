"""Unit tests for :class:`ZenodoAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.zenodo import ZenodoAdapter


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
    return json.dumps({"hits": {"hits": [], "total": 0}}).encode("utf-8")


def _payload(*hits: dict[str, object]) -> bytes:
    return json.dumps({"hits": {"hits": list(hits), "total": len(hits)}}).encode("utf-8")


def _hit(
    *,
    title: str = "A dataset",
    creators: list[str] | None = None,
    pub_date: str = "2024-04-12",
    doi: str = "10.5281/zenodo.123",
    is_open: bool = True,
    self_html: str = "https://zenodo.org/records/123",
    resource_type: str = "dataset",
    language: str = "en",
) -> dict[str, object]:
    return {
        "metadata": {
            "title": title,
            "creators": [{"name": n} for n in (creators or ["Silva, A."])],
            "publication_date": pub_date,
            "doi": doi,
            "access_right": "open" if is_open else "closed",
            "resource_type": {"type": resource_type},
            "language": language,
            "description": "A dataset description.",
            "license": {"id": "CC-BY-4.0"},
        },
        "links": {"self_html": self_html},
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert ZenodoAdapter(_FakeHttpClient()).source_id == "zenodo"

    def test_source_tier(self) -> None:
        assert ZenodoAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = ZenodoAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_hit_parsed(self) -> None:
        body = _payload(_hit(title="Dataset", doi="10.5281/zenodo.42"))
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "Dataset"
        assert item.doi == "10.5281/zenodo.42"
        assert item.venue == "Zenodo"

    def test_creators_parsed_as_authors(self) -> None:
        body = _payload(_hit(creators=["Silva, A.", "Pereira, B."]))
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.")

    def test_year_extracted_from_publication_date(self) -> None:
        body = _payload(_hit(pub_date="2023-09-01"))
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].year == 2023

    def test_open_access_right_marks_is_oa(self) -> None:
        body = _payload(_hit(is_open=True))
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is True

    def test_closed_access_means_not_oa(self) -> None:
        body = _payload(_hit(is_open=False))
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is False

    def test_self_html_link_becomes_url(self) -> None:
        body = _payload(_hit(self_html="https://zenodo.org/records/9999"))
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url == "https://zenodo.org/records/9999"

    def test_resource_type_becomes_publication_type(self) -> None:
        body = _payload(_hit(resource_type="software"))
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=10)
        assert adapter.fetch(SearchQuery(text="x")).items[0].publication_type == "software"


class TestQueryConstruction:
    def test_year_range_appended_with_publication_date(self) -> None:
        client = _FakeHttpClient(_empty())
        ZenodoAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "publication_date" in decoded
        assert "2020-01-01" in decoded
        assert "2024-12-31" in decoded

    def test_resource_types_filter_added(self) -> None:
        client = _FakeHttpClient(_empty())
        ZenodoAdapter(client, max_results=10, resource_types=("publication",)).fetch(
            SearchQuery(text="x")
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "resource_type.type" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_hit(doi=f"10.5281/zenodo.{i}") for i in range(8)])
        adapter = ZenodoAdapter(_FakeHttpClient(body), max_results=5)
        result = adapter.fetch(SearchQuery(text="x"))
        assert len(result.items) == 5
