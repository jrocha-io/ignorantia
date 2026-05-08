"""``PhilArchiveAdapter`` — PhilArchive (philosophy OA archive).

Tier-1 source for philosophy publications via the PhilPapers/PhilArchive
JSON export. ``is_oa`` is derived from the presence of an
``archive_url`` (philarchive.org hosts the full-text PDF).
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class PhilArchiveAdapter(AdapterPort):
    """Adapter for ``philpapers.org/s/all`` JSON export."""

    source_id = "philarchive"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://philpapers.org/s/all"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from PhilArchive (single request)."""
        url = self._build_url(query)
        body = self._http.get(url)
        raw_items = _parse_items(body, self._max_results)
        items = tuple(_normalise(it, self.source_tier) for it in raw_items)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        params: dict[str, str] = {
            "q": query.text,
            "export": "json",
            "limit": str(min(self._max_results, self._PAGE_CAP)),
        }
        if query.year_start is not None:
            params["start_year"] = str(query.year_start)
        if query.year_end is not None:
            params["end_year"] = str(query.year_end)
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_items(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("results") or []
    return [it for it in raw[:limit] if isinstance(it, dict)]


def _normalise(item: dict[str, Any], tier: Tier) -> FetchedItem:
    archive_url = _str_or_none(item.get("archive_url"))
    return FetchedItem(
        title=str(item.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(item)),
        year=_safe_int(item.get("year")),
        doi=_str_or_none(item.get("doi")),
        venue=_str_or_none(item.get("publication")) or _str_or_none(item.get("source")),
        language=str(item.get("language") or "en"),
        is_oa=archive_url is not None,
        url=archive_url,
        url_for_pdf=archive_url,
        publication_type=_str_or_none(item.get("category")),
    )


def _authors(item: dict[str, Any]) -> list[str]:
    raw = item.get("authors")
    if isinstance(raw, list):
        return [str(a) for a in raw if a]
    if isinstance(raw, str) and raw:
        return [raw]
    return []


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
