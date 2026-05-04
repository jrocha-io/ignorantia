"""``DoajAdapter`` — concrete :class:`AdapterPort` for DOAJ.

DOAJ (Directory of Open Access Journals) is a Tier-1 source: every
record is open access by definition. Migrated from v2 ``search_doaj.py``.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import quote

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class DoajAdapter(AdapterPort):
    """Adapter for DOAJ's ``/api/search/articles`` endpoint."""

    source_id = "doaj"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://doaj.org/api/search/articles"
    _PAGE_SIZE_CAP: ClassVar[int] = 100

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from DOAJ in a single request (no pagination here)."""
        url = self._build_url(query)
        body = self._http.get(url)
        raw_items = _parse_payload(body, self._max_results)
        items = tuple(_normalise(raw) for raw in raw_items)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        page_size = min(self._max_results, self._PAGE_SIZE_CAP)
        return f"{self._API_URL}/{quote(_lucene_query(query))}?pageSize={page_size}"


def _lucene_query(query: SearchQuery) -> str:
    parts = [query.text]
    if query.year_start is not None and query.year_end is not None:
        parts.append(f"bibjson.year:[{query.year_start} TO {query.year_end}]")
    return " AND ".join(f"({p})" for p in parts if p)


def _parse_payload(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw_results = payload.get("results") or []
    return [item for item in raw_results[:limit] if isinstance(item, dict)]


def _normalise(raw: dict[str, Any]) -> FetchedItem:
    bibjson = raw.get("bibjson", {}) if isinstance(raw.get("bibjson"), dict) else {}
    return FetchedItem(
        title=str(bibjson.get("title") or ""),
        source_tier=Tier.TIER1,
        authors=tuple(_authors(bibjson)),
        year=_safe_int(bibjson.get("year")),
        doi=_doi(bibjson),
        venue=_venue(bibjson),
        language=_language(bibjson),
        is_oa=True,
        url=_fulltext_url(bibjson),
    )


def _authors(bibjson: dict[str, Any]) -> list[str]:
    raw = bibjson.get("author") or []
    return [str(a.get("name")) for a in raw if isinstance(a, dict) and a.get("name")]


def _doi(bibjson: dict[str, Any]) -> str | None:
    for ident in bibjson.get("identifier") or []:
        if isinstance(ident, dict) and ident.get("type") == "doi" and ident.get("id"):
            return str(ident["id"])
    return None


def _venue(bibjson: dict[str, Any]) -> str | None:
    journal = bibjson.get("journal")
    if isinstance(journal, dict) and journal.get("title"):
        return str(journal["title"])
    return None


def _language(bibjson: dict[str, Any]) -> str:
    journal = bibjson.get("journal")
    if not isinstance(journal, dict):
        return "en"
    lang = journal.get("language")
    if isinstance(lang, list) and lang:
        return str(lang[0])
    if isinstance(lang, str) and lang:
        return lang
    return "en"


def _fulltext_url(bibjson: dict[str, Any]) -> str | None:
    for link in bibjson.get("link") or []:
        if isinstance(link, dict) and link.get("type") == "fulltext" and link.get("url"):
            return str(link["url"])
    return None


def _safe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
