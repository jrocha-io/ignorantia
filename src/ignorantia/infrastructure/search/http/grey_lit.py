"""``GreyLitAdapter`` — multi-provider grey literature aggregator (Tier 1).

Grey literature (UNESCO, OECD, World Bank, IPEA, INEP, NIST, WHO ...) is
substantive evidence for realist reviews, white papers, and position
papers. v2 routed each provider through bespoke logic; v3 unifies them
under one adapter that switches behaviour by ``provider``.

Two providers expose DSpace-style REST JSON and are fully implemented:

* ``world_bank`` — World Bank Open Knowledge Repository
  (``openknowledge.worldbank.org/rest/search``)
* ``who`` — WHO IRIS (``iris.who.int/rest/search``)

The remaining v2 providers (``unesco``, ``oecd``, ``ipea``, ``inep``,
``nist``) only expose HTML in v2. Decision DD-6 forbids HTML scraping in
v3, so they are accepted as valid providers but always emit
``Method.REAL_ERROR`` until a structured API path is found (e.g. an
OAI-PMH endpoint, which is out of scope here).
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient

_DSPACE_ENDPOINTS: dict[str, str] = {
    "world_bank": "https://openknowledge.worldbank.org/rest/search",
    "who": "https://iris.who.int/rest/search",
}

_DSPACE_LANG_DEFAULTS: dict[str, str] = {
    "world_bank": "en",
    "who": "en",
}

_NO_API_PROVIDERS: frozenset[str] = frozenset({"unesco", "oecd", "ipea", "inep", "nist"})

_VALID_PROVIDERS: frozenset[str] = frozenset(_DSPACE_ENDPOINTS) | _NO_API_PROVIDERS


class GreyLitAdapter(AdapterPort):
    """Adapter for grey-literature providers (DSpace REST + DD-6 stubs)."""

    source_id = "grey_lit"
    source_tier = Tier.TIER1

    _PAGE_CAP: ClassVar[int] = 100

    def __init__(
        self,
        http: HttpClient,
        *,
        provider: str = "world_bank",
        max_results: int = 100,
    ) -> None:
        """Wire to ``provider``; HTML-only providers always emit REAL_ERROR."""
        if provider not in _VALID_PROVIDERS:
            raise ValueError(
                f"unknown provider: {provider!r}; valid options are {sorted(_VALID_PROVIDERS)}"
            )
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._provider = provider
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Query the provider; year filtering is applied locally."""
        if self._provider in _NO_API_PROVIDERS:
            return self._build_result(query, Method.REAL_ERROR, ())
        body = self._http.get(self._build_url(query), headers={"Accept": "application/json"})
        lang_default = _DSPACE_LANG_DEFAULTS[self._provider]
        items = tuple(
            it
            for it in (
                _normalise_dspace(raw, self.source_tier, lang_default)
                for raw in _parse_dspace(body, self._max_results)
            )
            if _within_year(it, query)
        )
        return self._build_result(query, Method.REAL, items)

    def _build_url(self, query: SearchQuery) -> str:
        params: list[tuple[str, str]] = [
            ("query", query.text),
            ("expand", "metadata"),
            ("limit", str(min(self._max_results, self._PAGE_CAP))),
        ]
        return f"{_DSPACE_ENDPOINTS[self._provider]}?{urlencode(params)}"

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


def _parse_dspace(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, list):
        return []
    return [r for r in payload[:limit] if isinstance(r, dict)]


def _normalise_dspace(item: dict[str, Any], tier: Tier, lang_default: str) -> FetchedItem:
    md = _metadata_dict(item.get("metadata"))
    return FetchedItem(
        title=str(md.get("dc.title") or ""),
        source_tier=tier,
        authors=tuple(_authors(md)),
        year=_safe_year(md.get("dc.date.issued")),
        doi=_str_or_none(md.get("dc.identifier.doi")),
        language=_str_or_none(md.get("dc.language.iso")) or lang_default,
        is_oa=True,
        publication_type=_str_or_none(md.get("dc.type")),
    )


def _metadata_dict(metadata: object) -> dict[str, str]:
    if not isinstance(metadata, list):
        return {}
    out: dict[str, str] = {}
    for entry in metadata:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        value = entry.get("value")
        if isinstance(key, str) and isinstance(value, str):
            out[key] = value
    return out


def _authors(md: dict[str, str]) -> list[str]:
    author = md.get("dc.contributor.author")
    return [author] if author else []


def _safe_year(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    head = value[:4]
    return int(head) if head.isdigit() else None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _within_year(item: FetchedItem, query: SearchQuery) -> bool:
    if query.year_start is None and query.year_end is None:
        return True
    if item.year is None:
        return True
    if query.year_start is not None and item.year < query.year_start:
        return False
    return not (query.year_end is not None and item.year > query.year_end)
