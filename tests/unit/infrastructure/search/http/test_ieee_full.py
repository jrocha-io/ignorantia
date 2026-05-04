"""Unit tests for :class:`IeeeFullAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.error import HTTPError

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.ieee_full import IeeeFullAdapter


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
    return json.dumps({"articles": [], "total_records": 0}).encode("utf-8")


def _payload(*articles: dict[str, object]) -> bytes:
    return json.dumps({"articles": list(articles), "total_records": len(articles)}).encode("utf-8")


def _article(
    *,
    title: str = "ML for IoT",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1109/x",
    issn: str = "0018-9219",
    venue: str = "Proc IEEE",
    is_oa: bool = False,
) -> dict[str, object]:
    auth_list = [{"full_name": n} for n in (authors or ["Silva, A.", "Pereira, B."])]
    return {
        "title": title,
        "authors": {"authors": auth_list},
        "publication_year": year,
        "doi": doi,
        "issn": issn,
        "publication_title": venue,
        "access_type": "OPEN_ACCESS" if is_oa else "LOCKED",
        "html_url": f"https://ieeexplore.ieee.org/document/{doi}",
        "pdf_url": f"https://ieeexplore.ieee.org/stamp/{doi}.pdf" if is_oa else None,
        "abstract": "Abstract.",
        "content_type": "Conferences",
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert IeeeFullAdapter(_FakeHttpClient()).source_id == "ieee_full"

    def test_source_tier(self) -> None:
        assert IeeeFullAdapter(_FakeHttpClient()).source_tier is Tier.TIER2


class TestNoCredentials:
    def test_returns_real_error_when_no_key(self) -> None:
        result = IeeeFullAdapter(_FakeHttpClient()).fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR


class TestKeyMode:
    def test_apikey_query_param(self) -> None:
        client = _FakeHttpClient(_empty())
        IeeeFullAdapter(client, api_key="K1").fetch(SearchQuery(text="x"))
        assert "apikey=K1" in client.urls[0]

    def test_successful_fetch(self) -> None:
        body = _payload(_article(title="Cool paper", year=2023, doi="10.1109/y"))
        adapter = IeeeFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL
        assert result.items[0].title == "Cool paper"

    def test_authors_extracted_from_nested(self) -> None:
        body = _payload(_article(authors=["Tan A", "Lee B"]))
        adapter = IeeeFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Tan A", "Lee B")

    def test_open_access_marked_correctly(self) -> None:
        body = _payload(_article(is_oa=True))
        adapter = IeeeFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is True
        assert item.url_for_pdf is not None

    def test_locked_means_not_oa(self) -> None:
        body = _payload(_article(is_oa=False))
        adapter = IeeeFullAdapter(_FakeHttpClient(body), api_key="K", max_results=10)
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.is_oa is False


class TestCascadeOnNetworkErrors:
    def test_unauth_error_yields_real_error(self) -> None:
        err = HTTPError("u", 401, "unauth", hdrs=None, fp=None)  # type: ignore[arg-type]
        adapter = IeeeFullAdapter(_FakeHttpClient(err), api_key="K")
        result = adapter.fetch(SearchQuery(text="x"))
        assert result.method is Method.REAL_ERROR


class TestQueryConstruction:
    def test_year_range_translates_to_start_end_year(self) -> None:
        client = _FakeHttpClient(_empty())
        IeeeFullAdapter(client, api_key="K", max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        assert "start_year=2020" in client.urls[0]
        assert "end_year=2024" in client.urls[0]
