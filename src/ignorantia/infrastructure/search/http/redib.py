"""``RedibAdapter`` — REDIB (Red Iberoamericana de Innovación y Conocimiento).

Tier-1 source. REDIB indexes ~2M Ibero-American records with curatorial
focus on regional impact journals (overlapping with Redalyc and
LA Referencia but with distinct selection criteria). The public REST
API at ``redib.org/api/v1/search`` requires a free registration key
(``REDIB_API_KEY``); without it the adapter short-circuits to
``Method.REAL_ERROR`` rather than wasting an unauthenticated call that
the API would reject anyway.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class RedibAdapter(AdapterPort):
    """Adapter for REDIB's ``redib.org/api/v1/search`` endpoint."""

    source_id = "redib"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://redib.org/api/v1/search"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(
        self,
        http: HttpClient,
        *,
        api_key: str | None = None,
        max_results: int = 100,
    ) -> None:
        """Wire the adapter; ``api_key`` is required for any real fetch."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._api_key = api_key
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch results from REDIB. Without ``api_key`` returns REAL_ERROR."""
        if not self._api_key:
            return self._build_result(query, Method.REAL_ERROR, ())
        body = self._http.get(self._build_url(query), headers={"Accept": "application/json"})
        items = tuple(
            _normalise(it, self.source_tier) for it in _parse_results(body, self._max_results)
        )
        return self._build_result(query, Method.REAL, items)

    def _build_url(self, query: SearchQuery) -> str:
        params: list[tuple[str, str]] = [
            ("q", query.text),
            ("key", self._api_key or ""),
            ("format", "json"),
            ("limit", str(min(self._max_results, self._PAGE_CAP))),
        ]
        if query.year_start is not None:
            params.append(("yearFrom", str(query.year_start)))
        if query.year_end is not None:
            params.append(("yearTo", str(query.year_end)))
        return f"{self._API_URL}?{urlencode(params)}"

    def _build_result(
        self,
        query: SearchQuery,
        method: Method,
        items: tuple[FetchedItem, ...],
    ) -> SearchResult:
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=method,
            query=query,
            items=items,
        )


def _parse_results(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("results") or []
    return [r for r in raw[:limit] if isinstance(r, dict)]


def _normalise(item: dict[str, Any], tier: Tier) -> FetchedItem:
    return FetchedItem(
        title=str(item.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(item))[:10],
        year=_safe_int(item.get("year")),
        doi=_str_or_none(item.get("doi")),
        venue=_str_or_none(item.get("journal_title")),
        language=_str_or_none(item.get("language")) or "es",
        is_oa=True,
        url=_str_or_none(item.get("url")),
        publication_type="journal-article",
    )


def _authors(item: dict[str, Any]) -> list[str]:
    raw = item.get("authors") or []
    return [str(a) for a in raw if isinstance(a, str) and a]


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
