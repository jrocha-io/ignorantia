"""Unit tests for :class:`OsfPreprintsAdapter` and :class:`EdArxivAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.edarxiv import EdArxivAdapter
from ignorantia.infrastructure.search.http.osf_preprints import OsfPreprintsAdapter


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
    return json.dumps({"data": []}).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps({"data": list(items)}).encode("utf-8")


def _item(
    *,
    item_id: str = "abc123",
    title: str = "Adult learning research",
    date_published: str = "2024-04-12",
    doi: str | None = "10.31234/osf.io/x",
    description: str = "Abstract goes here.",
    provider_id: str = "edarxiv",
    pdf_url: str | None = "https://osf.io/download/abc123",
) -> dict[str, object]:
    return {
        "id": item_id,
        "attributes": {
            "title": title,
            "date_published": date_published,
            "doi": doi,
            "description": description,
            "tags": ["education", "literacy"],
        },
        "relationships": {
            "provider": {"data": {"id": provider_id}},
        },
        "links": {"download": pdf_url},
    }


class TestOsfPreprintsMetadata:
    def test_source_id(self) -> None:
        assert OsfPreprintsAdapter(_FakeHttpClient()).source_id == "osf_preprints"

    def test_source_tier(self) -> None:
        assert OsfPreprintsAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestEdArxivMetadata:
    def test_source_id(self) -> None:
        assert EdArxivAdapter(_FakeHttpClient()).source_id == "edarxiv"

    def test_source_tier(self) -> None:
        assert EdArxivAdapter(_FakeHttpClient()).source_tier is Tier.TIER1

    def test_edarxiv_url_filters_by_provider(self) -> None:
        client = _FakeHttpClient(_empty())
        EdArxivAdapter(client).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "filter[provider]=edarxiv" in decoded

    def test_osf_without_provider_does_not_set_filter_provider(self) -> None:
        client = _FakeHttpClient(_empty())
        OsfPreprintsAdapter(client).fetch(SearchQuery(text="x"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "filter[provider]" not in decoded


class TestParsing:
    def test_empty_response(self) -> None:
        result = OsfPreprintsAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_item_parsed(self) -> None:
        body = _payload(_item(title="A study", date_published="2023-06-15", doi="10.1/y"))
        adapter = OsfPreprintsAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A study"
        assert item.year == 2023
        assert item.doi == "10.1/y"

    def test_provider_id_becomes_venue(self) -> None:
        body = _payload(_item(provider_id="psyarxiv"))
        adapter = OsfPreprintsAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.venue == "psyarxiv"

    def test_pdf_url_extracted(self) -> None:
        body = _payload(_item(pdf_url="https://osf.io/download/zz"))
        adapter = OsfPreprintsAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.url_for_pdf == "https://osf.io/download/zz"

    def test_items_marked_as_oa(self) -> None:
        body = _payload(_item())
        adapter = OsfPreprintsAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True

    def test_publication_type_is_preprint(self) -> None:
        body = _payload(_item())
        adapter = OsfPreprintsAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.publication_type == "preprint"

    def test_abstract_extracted_and_truncated(self) -> None:
        body = _payload(_item(description="A" * 600))
        adapter = OsfPreprintsAdapter(_FakeHttpClient(body), max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert len(item.abstract) == 500


class TestQueryConstruction:
    def test_text_query_in_filter_q(self) -> None:
        client = _FakeHttpClient(_empty())
        OsfPreprintsAdapter(client).fetch(SearchQuery(text="literacy"))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "filter[q]=literacy" in decoded

    def test_year_range_translates_to_date_filters(self) -> None:
        client = _FakeHttpClient(_empty())
        OsfPreprintsAdapter(client).fetch(SearchQuery(text="x", year_start=2020, year_end=2024))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "filter[date_published][gte]=2020-01-01" in decoded
        assert "filter[date_published][lte]=2024-12-31" in decoded

    def test_page_size_capped(self) -> None:
        client = _FakeHttpClient(_empty())
        OsfPreprintsAdapter(client, max_results=200).fetch(SearchQuery(text="x"))
        # OSF cap is 100 per page
        assert "page[size]=100" in client.urls[0] or "page%5Bsize%5D=100" in client.urls[0]


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_item(item_id=f"i{n}") for n in range(8)])
        result = OsfPreprintsAdapter(_FakeHttpClient(body), max_results=5).fetch(
            SearchQuery(text="x")
        )
        assert len(result.items) == 5
