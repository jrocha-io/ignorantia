"""``ZenodoAdapter`` — Zenodo records API.

Tier-1 source for datasets, software and publications archived on
Zenodo. Uses Elasticsearch-style query syntax with optional resource
type filtering.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class ZenodoAdapter(AdapterPort):
    """Adapter for Zenodo's ``/api/records`` endpoint."""

    source_id = "zenodo"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://zenodo.org/api/records"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(
        self,
        http: HttpClient,
        *,
        max_results: int = 100,
        resource_types: tuple[str, ...] = (),
    ) -> None:
        """Wire the adapter and configure result type filters."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results
        self._resource_types = resource_types

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from Zenodo (single request)."""
        url = self._build_url(query)
        body = self._http.get(url)
        hits = _parse_hits(body, self._max_results)
        items = tuple(_normalise(hit, self.source_tier) for hit in hits)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        clauses = [query.text]
        if query.year_start is not None and query.year_end is not None:
            clauses.append(
                f"publication_date:[{query.year_start:04d}-01-01 TO {query.year_end:04d}-12-31]"
            )
        if self._resource_types:
            type_clause = " OR ".join(f'resource_type.type:"{t}"' for t in self._resource_types)
            clauses.append(f"({type_clause})")
        params: dict[str, str] = {
            "q": " AND ".join(f"({c})" for c in clauses if c),
            "size": str(min(self._max_results, self._PAGE_CAP)),
            "sort": "mostrecent",
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_hits(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    hits = payload.get("hits")
    if not isinstance(hits, dict):
        return []
    raw = hits.get("hits") or []
    return [h for h in raw[:limit] if isinstance(h, dict)]


def _normalise(hit: dict[str, Any], tier: Tier) -> FetchedItem:
    metadata = hit.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    links = hit.get("links") or {}
    self_html = links.get("self_html") if isinstance(links, dict) else None
    return FetchedItem(
        title=str(metadata.get("title") or ""),
        source_tier=tier,
        authors=tuple(_creators(metadata)),
        year=_year_from_date(metadata.get("publication_date")),
        doi=_str_or_none(metadata.get("doi")),
        venue="Zenodo",
        language=str(metadata.get("language") or "en"),
        is_oa=metadata.get("access_right") == "open",
        url=_str_or_none(self_html),
        url_for_pdf=_str_or_none(self_html),
        abstract=str(metadata.get("description") or "")[:500],
        publication_type=_resource_type(metadata),
    )


def _creators(metadata: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for c in metadata.get("creators") or []:
        if isinstance(c, dict) and c.get("name"):
            out.append(str(c["name"]))
    return out


def _year_from_date(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _resource_type(metadata: dict[str, Any]) -> str | None:
    rt = metadata.get("resource_type")
    if isinstance(rt, dict) and rt.get("type"):
        return str(rt["type"])
    return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
