"""Shared base class for VuFind-backed adapters that consume RSS results.

Multiple Iberoamerican aggregators (LA Referencia, BDTD, ...) expose a
VuFind ``Search/Results`` endpoint that emits an RSS feed when called with
``view=rss``. The feed format is identical across deployments, so the
parsing logic lives here once.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient

_LANGUAGE_MAP = {"por": "pt", "spa": "es", "eng": "en"}
_DC_NAMESPACE = {"dc": "http://purl.org/dc/elements/1.1/"}
_YEAR_RE = re.compile(r"(\d{4})")


class _VuFindRssAdapter(AdapterPort):
    """Abstract base for VuFind ``Search/Results?view=rss`` endpoints."""

    source_tier = Tier.TIER1

    _SEARCH_URL: ClassVar[str]

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and configure the result cap."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Hit the VuFind ``Search/Results`` endpoint and parse its RSS body."""
        url = self._build_url(query)
        body = self._http.get(url)
        items = tuple(_parse_rss(body, self._max_results, self.source_tier))
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        params: dict[str, str | list[str]] = {
            "lookfor": query.text,
            "type": "AllFields",
            "limit": str(self._max_results),
            "view": "rss",
        }
        if query.year_start is not None and query.year_end is not None:
            params["filter[]"] = [f"publishDate:[{query.year_start} TO {query.year_end}]"]
        return f"{self._SEARCH_URL}?{urlencode(params, doseq=True)}"


def _parse_rss(body: bytes, limit: int, tier: Tier) -> list[FetchedItem]:
    try:
        root = ET.fromstring(body)  # noqa: S314
    except ET.ParseError:
        return []
    channel = root.find("channel")
    if channel is None:
        return []
    items: list[FetchedItem] = []
    for raw in channel.findall("item"):
        if len(items) >= limit:
            break
        parsed = _parse_item(raw, tier)
        if parsed is not None:
            items.append(parsed)
    return items


def _parse_item(item: ET.Element, tier: Tier) -> FetchedItem | None:
    title = (item.findtext("title") or "").strip()
    if not title:
        return None
    return FetchedItem(
        title=title,
        source_tier=tier,
        authors=tuple(_authors(item)),
        year=_year(item),
        language=_language(item),
        url=(item.findtext("link") or "").strip() or None,
        is_oa=True,
        abstract=(item.findtext("description") or "").strip()[:400],
    )


def _authors(item: ET.Element) -> list[str]:
    creators = [c.text.strip() for c in item.findall("dc:creator", _DC_NAMESPACE) if c.text]
    if creators:
        return creators
    fallback = item.findtext("author") or ""
    return [fallback.strip()] if fallback.strip() else []


def _year(item: ET.Element) -> int | None:
    candidate = item.findtext("dc:date", default="", namespaces=_DC_NAMESPACE) or ""
    if not candidate:
        candidate = item.findtext("pubDate") or ""
    match = _YEAR_RE.search(candidate)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _language(item: ET.Element) -> str:
    raw = (item.findtext("dc:language", default="", namespaces=_DC_NAMESPACE) or "").strip().lower()
    if not raw:
        return "und"
    return _LANGUAGE_MAP.get(raw, raw)
