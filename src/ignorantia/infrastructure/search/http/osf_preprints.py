"""``OsfPreprintsAdapter`` — Center for Open Science (OSF) Preprints.

Tier-1 source. OSF hosts multiple themed preprint servers (PsyArXiv,
EdArXiv, SocArXiv, ...) all behind the same JSON:API endpoint. This
adapter accepts an optional ``provider`` parameter to scope the search
to one server. Themed subclasses (e.g. :class:`EdArxivAdapter`) declare
``_PROVIDER`` and inherit everything else.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import quote

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class OsfPreprintsAdapter(AdapterPort):
    """Adapter for OSF Preprints' ``api.osf.io/v2/preprints/`` endpoint."""

    source_id = "osf_preprints"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://api.osf.io/v2/preprints/"
    _PAGE_CAP: ClassVar[int] = 100
    _PROVIDER: ClassVar[str | None] = None

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from OSF (single request)."""
        url = self._build_url(query)
        body = self._http.get(url)
        raw_items = _parse_data(body, self._max_results)
        items = tuple(_normalise(it, self.source_tier) for it in raw_items)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        # OSF uses JSON:API-style ``filter[name]=value`` query parameters,
        # which urllib.parse.urlencode would over-encode. Build manually.
        parts = [f"filter[q]={quote(query.text)}"]
        if self._PROVIDER:
            parts.append(f"filter[provider]={quote(self._PROVIDER)}")
        if query.year_start is not None:
            parts.append(f"filter[date_published][gte]={query.year_start:04d}-01-01")
        if query.year_end is not None:
            parts.append(f"filter[date_published][lte]={query.year_end:04d}-12-31")
        page_size = min(self._max_results, self._PAGE_CAP)
        parts.append(f"page[size]={page_size}")
        return f"{self._API_URL}?{'&'.join(parts)}"


def _parse_data(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("data") or []
    return [it for it in raw[:limit] if isinstance(it, dict)]


def _normalise(item: dict[str, Any], tier: Tier) -> FetchedItem:
    attributes = item.get("attributes")
    attr: dict[str, Any] = attributes if isinstance(attributes, dict) else {}
    relationships = item.get("relationships")
    rels: dict[str, Any] = relationships if isinstance(relationships, dict) else {}
    links = item.get("links")
    links_d: dict[str, Any] = links if isinstance(links, dict) else {}
    provider_id = _provider_id(rels)
    return FetchedItem(
        title=str(attr.get("title") or ""),
        source_tier=tier,
        year=_year_from_iso(attr.get("date_published")),
        doi=_str_or_none(attr.get("doi")),
        venue=provider_id or "osf",
        language="en",
        is_oa=True,
        url=_str_or_none(links_d.get("html")) or _str_or_none(links_d.get("download")),
        url_for_pdf=_str_or_none(links_d.get("download")),
        abstract=str(attr.get("description") or "")[:500],
        publication_type="preprint",
    )


def _provider_id(relationships: dict[str, Any]) -> str | None:
    provider_block = relationships.get("provider")
    if not isinstance(provider_block, dict):
        return None
    data = provider_block.get("data")
    if isinstance(data, dict) and isinstance(data.get("id"), str):
        return str(data["id"])
    return None


def _year_from_iso(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
