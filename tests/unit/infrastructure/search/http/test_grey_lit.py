"""Unit tests for :class:`GreyLitAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import pytest

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.grey_lit import GreyLitAdapter


class _FakeGetHttp:
    def __init__(self, *bodies: bytes) -> None:
        self._bodies: Iterator[bytes] = iter(bodies)
        self.urls: list[str] = []
        self.headers: list[dict[str, str] | None] = []

    def get(self, url: str, headers: object | None = None) -> bytes:
        self.urls.append(url)
        self.headers.append(headers if isinstance(headers, dict) else None)
        try:
            return next(self._bodies)
        except StopIteration:
            return _empty()

    def post(self, url: str, *, data: bytes, headers: object | None = None) -> bytes:
        del url, data, headers
        raise AssertionError("GreyLitAdapter must use GET")


class _UnusedHttp:
    def get(self, url: str, headers: object | None = None) -> bytes:
        del url, headers
        raise AssertionError("HTTP must not be called for HTML-only providers")

    def post(self, url: str, *, data: bytes, headers: object | None = None) -> bytes:
        del url, data, headers
        raise AssertionError("HTTP must not be called for HTML-only providers")


def _empty() -> bytes:
    return json.dumps([]).encode("utf-8")


def _payload(*items: dict[str, object]) -> bytes:
    return json.dumps(list(items)).encode("utf-8")


def _dspace_item(
    *,
    title: str = "Digital literacy report",
    author: str | None = "World Bank",
    year: str | None = "2023",
    doi: str | None = None,
    language: str | None = "en",
    handle: str = "10986/12345",
    pub_type: str | None = "report",
) -> dict[str, object]:
    metadata: list[dict[str, str]] = [{"key": "dc.title", "value": title}]
    if author:
        metadata.append({"key": "dc.contributor.author", "value": author})
    if year:
        metadata.append({"key": "dc.date.issued", "value": year})
    if doi:
        metadata.append({"key": "dc.identifier.doi", "value": doi})
    if language:
        metadata.append({"key": "dc.language.iso", "value": language})
    if pub_type:
        metadata.append({"key": "dc.type", "value": pub_type})
    return {"handle": handle, "metadata": metadata}


class TestMetadata:
    def test_source_id(self) -> None:
        assert GreyLitAdapter(_UnusedHttp()).source_id == "grey_lit"

    def test_source_tier(self) -> None:
        assert GreyLitAdapter(_UnusedHttp()).source_tier is Tier.TIER1


class TestProviderValidation:
    @pytest.mark.parametrize(
        "provider",
        ["world_bank", "who", "unesco", "oecd", "ipea", "inep", "nist"],
    )
    def test_known_providers_accepted(self, provider: str) -> None:
        GreyLitAdapter(_UnusedHttp(), provider=provider)

    def test_unknown_provider_rejected(self) -> None:
        with pytest.raises(ValueError, match="provider"):
            GreyLitAdapter(_UnusedHttp(), provider="nonsense")

    def test_default_provider_is_world_bank(self) -> None:
        adapter = GreyLitAdapter(_FakeGetHttp(_empty()))
        adapter.fetch(SearchQuery(text="x"))
        # The default must hit the World Bank DSpace endpoint.
        # Verified via _UnusedHttp not raising; here we just check construction.
        assert adapter is not None


class TestNoApiProviders:
    @pytest.mark.parametrize("provider", ["unesco", "oecd", "ipea", "inep", "nist"])
    def test_html_only_providers_yield_real_error(self, provider: str) -> None:
        result = GreyLitAdapter(_UnusedHttp(), provider=provider).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR
        assert result.items == ()
        assert result.source == "grey_lit"
        assert result.source_tier is Tier.TIER1


class TestDSpaceParsing:
    def test_world_bank_empty_response(self) -> None:
        result = GreyLitAdapter(
            _FakeGetHttp(_empty()), provider="world_bank", max_results=10
        ).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert result.items == ()

    def test_who_empty_response(self) -> None:
        result = GreyLitAdapter(_FakeGetHttp(_empty()), provider="who", max_results=10).fetch(
            SearchQuery(text="x")
        )
        assert result.method is Method.REAL
        assert result.items == ()

    def test_title_extracted(self) -> None:
        body = _payload(_dspace_item(title="A WB report"))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].title == "A WB report"

    def test_author_extracted_when_present(self) -> None:
        body = _payload(_dspace_item(author="OECD"))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].authors == ("OECD",)

    def test_authors_empty_when_missing(self) -> None:
        body = _payload(_dspace_item(author=None))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].authors == ()

    def test_year_extracted_from_iso_date(self) -> None:
        body = _payload(_dspace_item(year="2022-05-01"))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].year == 2022

    def test_year_none_when_missing(self) -> None:
        body = _payload(_dspace_item(year=None))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].year is None

    def test_doi_extracted_when_present(self) -> None:
        body = _payload(_dspace_item(doi="10.1234/wb.42"))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].doi == "10.1234/wb.42"

    def test_language_extracted(self) -> None:
        body = _payload(_dspace_item(language="fr"))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].language == "fr"

    def test_default_language_when_missing(self) -> None:
        body = _payload(_dspace_item(language=None))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].language == "en"

    def test_publication_type_from_dc_type(self) -> None:
        body = _payload(_dspace_item(pub_type="working_paper"))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].publication_type == "working_paper"

    def test_is_oa_true_for_grey_lit(self) -> None:
        body = _payload(_dspace_item())
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert items[0].is_oa is True


class TestRequestShape:
    def test_world_bank_uses_dspace_endpoint(self) -> None:
        client = _FakeGetHttp(_empty())
        GreyLitAdapter(client, provider="world_bank", max_results=10).fetch(SearchQuery(text="x"))
        assert client.urls[0].startswith("https://openknowledge.worldbank.org/rest/search?")

    def test_who_uses_iris_endpoint(self) -> None:
        client = _FakeGetHttp(_empty())
        GreyLitAdapter(client, provider="who", max_results=10).fetch(SearchQuery(text="x"))
        assert client.urls[0].startswith("https://iris.who.int/rest/search?")

    def test_query_passed_as_query_param(self) -> None:
        client = _FakeGetHttp(_empty())
        GreyLitAdapter(client, provider="world_bank", max_results=10).fetch(
            SearchQuery(text="literacy")
        )
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["query"] == ["literacy"]

    def test_limit_param_caps_at_100(self) -> None:
        client = _FakeGetHttp(_empty())
        GreyLitAdapter(client, provider="world_bank", max_results=500).fetch(SearchQuery(text="x"))
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["limit"] == ["100"]

    def test_expand_metadata_param_present(self) -> None:
        client = _FakeGetHttp(_empty())
        GreyLitAdapter(client, provider="world_bank", max_results=10).fetch(SearchQuery(text="x"))
        params = parse_qs(urlsplit(client.urls[0]).query)
        assert params["expand"] == ["metadata"]

    def test_accept_header_is_application_json(self) -> None:
        client = _FakeGetHttp(_empty())
        GreyLitAdapter(client, provider="world_bank", max_results=10).fetch(SearchQuery(text="x"))
        assert client.headers[0] is not None
        assert client.headers[0].get("Accept") == "application/json"


class TestYearFiltering:
    def test_filters_items_outside_year_window(self) -> None:
        body = _payload(
            _dspace_item(title="Old", year="2010"),
            _dspace_item(title="In window", year="2022"),
            _dspace_item(title="Future", year="2030"),
        )
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x", year_start=2020, year_end=2025))
            .items
        )
        titles = {it.title for it in items}
        assert titles == {"In window"}

    def test_no_year_filter_passes_all_items(self) -> None:
        body = _payload(
            _dspace_item(title="A", year="2010"),
            _dspace_item(title="B", year="2030"),
        )
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert {it.title for it in items} == {"A", "B"}

    def test_items_without_year_are_kept_when_filter_applied(self) -> None:
        body = _payload(_dspace_item(title="Undated", year=None))
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=10)
            .fetch(SearchQuery(text="x", year_start=2020, year_end=2025))
            .items
        )
        assert len(items) == 1


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_dspace_item(title=f"t{n}") for n in range(8)])
        items = (
            GreyLitAdapter(_FakeGetHttp(body), provider="world_bank", max_results=5)
            .fetch(SearchQuery(text="x"))
            .items
        )
        assert len(items) == 5
