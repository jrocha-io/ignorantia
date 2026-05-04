"""Unit tests for :class:`LaReferenciaAdapter` and :class:`BdtdAdapter`.

Both subclass the private :class:`_VuFindRssAdapter` base which
encapsulates the VuFind RSS parser. The tests exercise the shared
behaviour through the LA Referencia subclass and pin the BDTD-specific
URL via a focused metadata test.
"""

from __future__ import annotations

from collections.abc import Iterator

from ignorantia.domain.search.entities import SearchQuery
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.search.http.bdtd import BdtdAdapter
from ignorantia.infrastructure.search.http.la_referencia import LaReferenciaAdapter


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
    return b"<rss><channel></channel></rss>"


def _rss(*items_xml: str) -> bytes:
    body = (
        '<rss xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<channel>" + "".join(items_xml) + "</channel></rss>"
    )
    return body.encode("utf-8")


def _item_xml(
    *,
    title: str = "Letramento digital de idosos",
    creators: tuple[str, ...] = ("Silva, A.", "Pereira, B."),
    date: str = "2023-04-12",
    link: str = "https://example.org/record/1",
    description: str = "Resumo do artigo.",
    language: str = "por",
) -> str:
    creators_xml = "".join(f"<dc:creator>{c}</dc:creator>" for c in creators)
    return (
        "<item>"
        f"<title>{title}</title>"
        f"<description>{description}</description>"
        f"<link>{link}</link>"
        f"<dc:date>{date}</dc:date>"
        f"<dc:language>{language}</dc:language>"
        f"{creators_xml}"
        "</item>"
    )


class TestMetadata:
    def test_la_referencia_source_id(self) -> None:
        assert LaReferenciaAdapter(_FakeHttpClient()).source_id == "la_referencia"

    def test_la_referencia_source_tier(self) -> None:
        assert LaReferenciaAdapter(_FakeHttpClient()).source_tier is Tier.TIER1

    def test_bdtd_source_id(self) -> None:
        assert BdtdAdapter(_FakeHttpClient()).source_id == "bdtd"

    def test_bdtd_source_tier(self) -> None:
        assert BdtdAdapter(_FakeHttpClient()).source_tier is Tier.TIER1


class TestUrlConstruction:
    def test_la_referencia_calls_la_referencia_search(self) -> None:
        client = _FakeHttpClient(_empty())
        LaReferenciaAdapter(client).fetch(SearchQuery(text="x"))
        assert "lareferencia.info" in client.urls[0]

    def test_bdtd_calls_bdtd_vufind_search(self) -> None:
        client = _FakeHttpClient(_empty())
        BdtdAdapter(client).fetch(SearchQuery(text="x"))
        assert "bdtd.ibict.br" in client.urls[0]

    def test_year_range_is_appended_as_publish_date_filter(self) -> None:
        client = _FakeHttpClient(_empty())
        LaReferenciaAdapter(client).fetch(SearchQuery(text="x", year_start=2020, year_end=2024))
        from urllib.parse import unquote_plus

        decoded = unquote_plus(client.urls[0])
        assert "publishDate:[2020 TO 2024]" in decoded


class TestRssParsing:
    def test_empty_channel_yields_no_items(self) -> None:
        result = LaReferenciaAdapter(_FakeHttpClient(_empty())).fetch(SearchQuery(text="x"))
        assert result.items == ()
        assert result.method is Method.REAL

    def test_single_item_parsed(self) -> None:
        body = _rss(_item_xml(title="A study on digital literacy", date="2023-06-15"))
        adapter = LaReferenciaAdapter(_FakeHttpClient(body))
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.title == "A study on digital literacy"
        assert item.year == 2023

    def test_creators_become_authors(self) -> None:
        body = _rss(_item_xml(creators=("Silva, A.", "Pereira, B.", "Costa, C.")))
        adapter = LaReferenciaAdapter(_FakeHttpClient(body))
        item = adapter.fetch(SearchQuery(text="x")).items[0]
        assert item.authors == ("Silva, A.", "Pereira, B.", "Costa, C.")

    def test_language_codes_normalised(self) -> None:
        body = _rss(_item_xml(language="por"))
        adapter = LaReferenciaAdapter(_FakeHttpClient(body))
        assert adapter.fetch(SearchQuery(text="x")).items[0].language == "pt"

    def test_unknown_language_falls_back_to_und(self) -> None:
        body = _rss(_item_xml(language=""))
        adapter = LaReferenciaAdapter(_FakeHttpClient(body))
        assert adapter.fetch(SearchQuery(text="x")).items[0].language == "und"

    def test_link_becomes_url(self) -> None:
        body = _rss(_item_xml(link="https://example.org/record/42"))
        adapter = LaReferenciaAdapter(_FakeHttpClient(body))
        assert adapter.fetch(SearchQuery(text="x")).items[0].url == "https://example.org/record/42"

    def test_items_marked_as_oa(self) -> None:
        body = _rss(_item_xml())
        adapter = LaReferenciaAdapter(_FakeHttpClient(body))
        assert adapter.fetch(SearchQuery(text="x")).items[0].is_oa is True

    def test_items_without_title_are_skipped(self) -> None:
        body = _rss(
            _item_xml(title="Real one"),
            "<item><description>no title</description></item>",
        )
        adapter = LaReferenciaAdapter(_FakeHttpClient(body))
        assert len(adapter.fetch(SearchQuery(text="x")).items) == 1


class TestMaxResults:
    def test_truncates_to_max_results(self) -> None:
        body = _rss(*[_item_xml(title=f"t{i}") for i in range(8)])
        adapter = LaReferenciaAdapter(_FakeHttpClient(body), max_results=5)
        assert len(adapter.fetch(SearchQuery(text="x")).items) == 5
