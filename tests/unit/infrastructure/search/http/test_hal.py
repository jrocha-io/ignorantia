"""Unit tests for :class:`HalAdapter`."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.hal import HalAdapter


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
    return json.dumps({"response": {"docs": []}}).encode("utf-8")


def _payload(*docs: dict[str, object]) -> bytes:
    return json.dumps({"response": {"docs": list(docs)}}).encode("utf-8")


def _doc(
    *,
    title: str | list[str] = "Littératie numérique",
    authors: list[str] | None = None,
    year: int = 2024,
    doi: str = "10.1234/x",
    pdf_url: str | None = "https://hal.science/hal-001/document",
    journal: str | list[str] = "Revue X",
    languages: list[str] | None = None,
) -> dict[str, object]:
    return {
        "title_s": title,
        "authFullName_s": authors or ["Silva, A.", "Pereira, B."],
        "producedDateY_i": year,
        "doiId_s": doi,
        "halId_s": "hal-001",
        "uri_s": "https://hal.science/hal-001",
        "fileMain_s": pdf_url,
        "journalTitle_s": journal,
        "docType_s": "ART",
        "abstract_s": ["A short abstract."],
        "language_s": languages or ["fr"],
    }


class TestMetadata:
    def test_source_id(self) -> None:
        assert HalAdapter(_FakeHttpClient()).source_id == "hal"

    def test_source_tier(self) -> None:
        assert HalAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestParsing:
    def test_empty_response(self) -> None:
        result = HalAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_doc_parsed(self) -> None:
        body = _payload(_doc(title="Étude numérique", year=2023, doi="10.1/y"))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.title == "Étude numérique"
        assert item.year == 2023
        assert item.doi == "10.1/y"

    def test_title_list_first_element_is_used(self) -> None:
        body = _payload(_doc(title=["Premier titre", "Alt"]))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.title == "Premier titre"

    def test_authors_list_kept_as_is(self) -> None:
        body = _payload(_doc(authors=["Dupont, A.", "Martin, B."]))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.authors == ("Dupont, A.", "Martin, B.")

    def test_pdf_url_extracted(self) -> None:
        body = _payload(_doc(pdf_url="https://hal.science/hal-002/document"))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.url_for_pdf == "https://hal.science/hal-002/document"

    def test_pdf_marks_is_oa(self) -> None:
        body = _payload(_doc(pdf_url="https://hal.science/hal-002/document"))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.is_oa is True

    def test_no_pdf_means_not_oa(self) -> None:
        body = _payload(_doc(pdf_url=None))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.is_oa is False

    def test_journal_first_element_becomes_venue(self) -> None:
        body = _payload(_doc(journal=["Revue Européenne", "Alt"]))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.venue == "Revue Européenne"

    def test_first_language_is_used(self) -> None:
        body = _payload(_doc(languages=["en", "fr"]))
        item = (
            HalAdapter(_FakeHttpClient(body), max_results=10).fetch(SearchQuery(text="x")).items[0]
        )
        assert item.language == "en"


class TestQueryConstruction:
    def test_year_range_appended_via_produced_date(self) -> None:
        client = _FakeHttpClient(_empty())
        HalAdapter(client, max_results=10).fetch(
            SearchQuery(text="x", year_start=2020, year_end=2024)
        )
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "producedDateY_i:[2020 TO 2024]" in decoded


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _payload(*[_doc(title=f"Étude {i}") for i in range(8)])
        result = HalAdapter(_FakeHttpClient(body), max_results=5).fetch(SearchQuery(text="x"))
        assert len(result.items) == 5
