"""``OapenAdapter`` — OAPEN OA book library (DSpace REST).

Tier-1 source for open-access scholarly books. OAPEN exposes a DSpace
REST endpoint at ``library.oapen.org/rest/search``. Responses are flat
JSON arrays of items where each item carries a ``metadata`` list of
``{key, value}`` pairs (Dublin Core schema).
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class OapenAdapter(AdapterPort):
    """Adapter for OAPEN's DSpace ``/rest/search`` endpoint."""

    source_id = "oapen"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://library.oapen.org/rest/search"
    _SITE_BASE: ClassVar[str] = "https://library.oapen.org"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from OAPEN with local year filtering."""
        url = self._build_url(query)
        body = self._http.get(url)
        raw_items = _parse_items(body, self._max_results)
        items: list[FetchedItem] = []
        for raw in raw_items:
            normalised = _normalise(raw, self.source_tier, self._SITE_BASE)
            if _within_year_range(normalised, query):
                items.append(normalised)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=tuple(items),
        )

    def _build_url(self, query: SearchQuery) -> str:
        params: dict[str, str] = {
            "query": query.text,
            "expand": "metadata,bitstreams",
            "limit": str(min(self._max_results, self._PAGE_CAP)),
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_items(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, list):
        return []
    return [it for it in payload[:limit] if isinstance(it, dict)]


def _normalise(item: dict[str, Any], tier: Tier, site_base: str) -> FetchedItem:
    metadata = _index_metadata(item.get("metadata") or [])
    handle = _str_or_none(item.get("handle"))
    pdf_url = _pdf_url(item.get("bitstreams") or [], site_base)
    if pdf_url is None and handle:
        pdf_url = f"{site_base}/handle/{handle}"
    return FetchedItem(
        title=_first(metadata.get("dc.title")),
        source_tier=tier,
        authors=tuple(_authors(metadata))[:10],
        year=_year_from_issued(_first(metadata.get("dc.date.issued"))),
        doi=_first_or_none(metadata.get("dc.identifier.doi")),
        isbn=_first_or_none(metadata.get("dc.identifier.isbn")),
        venue=_first_or_none(metadata.get("dc.publisher")),
        language=_first(metadata.get("dc.language.iso")) or "en",
        is_oa=True,
        url=pdf_url,
        url_for_pdf=pdf_url,
        publication_type="book",
    )


def _index_metadata(raw: list[Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        value = entry.get("value")
        if isinstance(key, str) and isinstance(value, str):
            out.setdefault(key, []).append(value)
    return out


def _authors(metadata: dict[str, list[str]]) -> list[str]:
    return metadata.get("dc.contributor.author") or metadata.get("dc.creator") or []


def _pdf_url(bitstreams: list[Any], site_base: str) -> str | None:
    for bs in bitstreams:
        if not isinstance(bs, dict):
            continue
        if str(bs.get("format") or "").lower() != "pdf":
            continue
        link = _str_or_none(bs.get("retrieveLink"))
        if link is None:
            continue
        return link if link.startswith("http") else f"{site_base}{link}"
    return None


def _first(values: list[str] | None) -> str:
    if values:
        return values[0]
    return ""


def _first_or_none(values: list[str] | None) -> str | None:
    return _first(values) or None


def _year_from_issued(value: str) -> int | None:
    if not value or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _within_year_range(item: FetchedItem, query: SearchQuery) -> bool:
    if item.year is None:
        return query.year_start is None and query.year_end is None
    if query.year_start is not None and item.year < query.year_start:
        return False
    return not (query.year_end is not None and item.year > query.year_end)


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
