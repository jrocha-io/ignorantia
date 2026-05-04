"""``ArxivAdapter`` — concrete :class:`AdapterPort` for arXiv.

Migrated from v2 ``scripts/searches/search_arxiv.py``. The original
script performed its own HTTP and ``urllib.request.urlopen`` calls; the
v3 adapter delegates all I/O to the injected :class:`HttpClient`, in
keeping with the *Single Responsibility Principle* (the adapter only
knows how to talk to arXiv, not how to do HTTP).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class ArxivAdapter(AdapterPort):
    """Adapter for the arXiv preprint repository (Tier 1, OA full text)."""

    source_id = "arxiv"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://export.arxiv.org/api/query"
    _ATOM: ClassVar[dict[str, str]] = {
        "a": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def __init__(
        self,
        http: HttpClient,
        *,
        max_per_page: int = 100,
        max_results: int = 1000,
    ) -> None:
        """Wire the adapter to an HTTP client and configure pagination."""
        if max_per_page <= 0:
            raise ValueError("max_per_page must be > 0")
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_per_page = max_per_page
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from arXiv with paginated GETs."""
        items: list[FetchedItem] = []
        start = 0
        while start < self._max_results:
            url = self._build_url(query, start)
            body = self._http.get(url)
            page_items = list(self._parse(body))
            if not page_items:
                break
            for item in page_items:
                if len(items) >= self._max_results:
                    break
                items.append(item)
            if len(items) >= self._max_results:
                break
            start += self._max_per_page
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=tuple(items),
        )

    def _build_url(self, query: SearchQuery, start: int) -> str:
        params = {
            "search_query": _build_api_query(query),
            "start": str(start),
            "max_results": str(self._max_per_page),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        return f"{self._API_URL}?{urlencode(params)}"

    def _parse(self, body: bytes) -> list[FetchedItem]:
        # ``ET.fromstring`` is safe here because we control the source
        # (export.arxiv.org) and the body is fetched over HTTPS.
        root = ET.fromstring(body)  # noqa: S314
        return [self._parse_entry(e) for e in root.findall("a:entry", self._ATOM)]

    def _parse_entry(self, entry: ET.Element) -> FetchedItem:
        title = _text(entry, "a:title")
        abstract = _text(entry, "a:summary")
        published = _text(entry, "a:published")
        year = _safe_year(published)
        authors = tuple(_text(a, "a:name") for a in entry.findall("a:author", self._ATOM))
        arxiv_id = _text(entry, "a:id").rsplit("/", 1)[-1]
        url, pdf_url = _extract_links(entry, self._ATOM, fallback_id=arxiv_id)
        doi_el = entry.find("arxiv:doi", self._ATOM)
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None
        return FetchedItem(
            title=" ".join(title.split()),
            source_tier=Tier.TIER1,
            authors=authors,
            year=year,
            doi=doi,
            venue="arXiv preprint",
            language="en",
            is_oa=True,
            url=url,
            url_for_pdf=pdf_url or None,
            abstract=" ".join(abstract.split()),
            publication_type="preprint",
        )


def _build_api_query(query: SearchQuery) -> str:
    parts = [query.text]
    if query.year_start is not None and query.year_end is not None:
        start = f"{query.year_start:04d}01010000"
        end = f"{query.year_end:04d}12312359"
        parts.append(f"submittedDate:[{start} TO {end}]")
    return " AND ".join(p for p in parts if p)


def _text(parent: ET.Element, path: str) -> str:
    el = parent.find(path, ArxivAdapter._ATOM)
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def _safe_year(published_iso: str) -> int | None:
    if not published_iso:
        return None
    try:
        return int(published_iso[:4])
    except ValueError:
        return None


def _extract_links(
    entry: ET.Element, namespaces: dict[str, str], *, fallback_id: str
) -> tuple[str, str]:
    pdf = ""
    abs_url = ""
    for link in entry.findall("a:link", namespaces):
        if link.attrib.get("title") == "pdf":
            pdf = link.attrib.get("href", "")
        elif link.attrib.get("rel") == "alternate":
            abs_url = link.attrib.get("href", "")
    if not abs_url and fallback_id:
        abs_url = f"https://arxiv.org/abs/{fallback_id}"
    return abs_url, pdf
