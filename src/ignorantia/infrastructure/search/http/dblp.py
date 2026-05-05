"""``DblpAdapter`` — DBLP Computer Science bibliographic API.

DBLP indexes computer science publications and is the gold standard for
CS bibliographic completeness. The API is free, no auth, returns JSON.

Note: DBLP's server-side query has no temporal filter, so the adapter
filters locally on ``year`` after parsing — consistent with the v2
implementation.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class DblpAdapter(AdapterPort):
    """Adapter for DBLP's ``/search/publ/api`` endpoint."""

    source_id = "dblp"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://dblp.org/search/publ/api"
    _PAGE_CAP: ClassVar[int] = 1000

    def __init__(
        self,
        http: HttpClient,
        *,
        max_per_page: int = 1000,
        max_results: int = 1000,
    ) -> None:
        """Wire the adapter and configure pagination."""
        if max_per_page <= 0:
            raise ValueError("max_per_page must be > 0")
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_per_page = min(max_per_page, self._PAGE_CAP)
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from DBLP with paginated GETs and local year filter."""
        items: list[FetchedItem] = []
        first = 0
        while first < self._max_results:
            url = self._build_url(query, first)
            body = self._http.get(url)
            hits = _parse_hits(body)
            if not hits:
                break
            for raw in hits:
                if len(items) >= self._max_results:
                    break
                item = _normalise(raw, self.source_tier)
                if _within_year_range(item, query):
                    items.append(item)
            if len(items) >= self._max_results:
                break
            if len(hits) < self._max_per_page:
                break
            first += self._max_per_page
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=tuple(items),
        )

    def _build_url(self, query: SearchQuery, first: int) -> str:
        params: dict[str, str] = {
            "q": query.text,
            "format": "json",
            "f": str(first),
            "h": str(self._max_per_page),
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_hits(body: bytes) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    hits_block = result.get("hits")
    if not isinstance(hits_block, dict):
        return []
    raw = hits_block.get("hit") or []
    return [h for h in raw if isinstance(h, dict)]


def _normalise(hit: dict[str, Any], tier: Tier) -> FetchedItem:
    info = hit.get("info") or {}
    if not isinstance(info, dict):
        info = {}
    title_raw = str(info.get("title") or "")
    return FetchedItem(
        title=title_raw.rstrip("."),
        source_tier=tier,
        authors=tuple(_authors(info))[:10],
        year=_safe_int(info.get("year")),
        doi=_str_or_none(info.get("doi")),
        venue=_str_or_none(info.get("venue")),
        language="en",
        is_oa=False,
        url=_str_or_none(info.get("url")),
        publication_type=_str_or_none(info.get("type")),
    )


def _authors(info: dict[str, Any]) -> list[str]:
    block = info.get("authors")
    if not isinstance(block, dict):
        return []
    raw = block.get("author")
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for a in raw:
        if isinstance(a, dict) and a.get("text"):
            out.append(str(a["text"]))
        elif isinstance(a, str):
            out.append(a)
    return out


def _within_year_range(item: FetchedItem, query: SearchQuery) -> bool:
    if item.year is None:
        return query.year_start is None and query.year_end is None
    if query.year_start is not None and item.year < query.year_start:
        return False
    return not (query.year_end is not None and item.year > query.year_end)


def _safe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
