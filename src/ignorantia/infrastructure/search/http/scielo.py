"""``ScieloAdapter`` — SciELO via the search.scielo.org JSON endpoint.

SciELO aggregates open-access scholarly publications from Latin America,
the Caribbean and Iberian Peninsula. Migrated from v2 ``search_scielo.py``.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class ScieloAdapter(AdapterPort):
    """Adapter for SciELO's ``search.scielo.org`` endpoint."""

    source_id = "scielo"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://search.scielo.org/"

    def __init__(
        self,
        http: HttpClient,
        *,
        max_per_page: int = 50,
        max_results: int = 200,
        language: str = "pt",
    ) -> None:
        """Wire the adapter and configure pagination."""
        if max_per_page <= 0:
            raise ValueError("max_per_page must be > 0")
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_per_page = max_per_page
        self._max_results = max_results
        self._language = language

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from SciELO with paginated GETs."""
        items: list[FetchedItem] = []
        page = 1
        while len(items) < self._max_results:
            url = self._build_url(query, page)
            body = self._http.get(url)
            docs = _parse_docs(body)
            if not docs:
                break
            for raw in docs:
                if len(items) >= self._max_results:
                    break
                items.append(_normalise(raw))
            if len(docs) < self._max_per_page:
                break
            page += 1
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=tuple(items),
        )

    def _build_url(self, query: SearchQuery, page: int) -> str:
        params: dict[str, str] = {
            "q": query.text,
            "lang": self._language,
            "count": str(self._max_per_page),
            "from": str((page - 1) * self._max_per_page + 1),
            "output": "site",
            "format": "json",
            "page": str(page),
        }
        if query.year_start is not None and query.year_end is not None:
            years = " OR ".join(f'"{y}"' for y in range(query.year_start, query.year_end + 1))
            params["fq"] = f"in:({years})"
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_docs(body: bytes) -> list[dict[str, Any]]:
    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return []
    response = payload.get("response")
    if not isinstance(response, dict):
        return []
    docs = response.get("docs") or []
    return [d for d in docs if isinstance(d, dict)]


def _normalise(doc: dict[str, Any]) -> FetchedItem:
    return FetchedItem(
        title=str(doc.get("title") or ""),
        source_tier=Tier.TIER1,
        authors=tuple(_authors(doc)),
        year=_safe_int(doc.get("year")),
        doi=_str_or_none(doc.get("doi")),
        issn=_str_or_none(doc.get("issn")),
        venue=_venue(doc),
        language=str(doc.get("language") or "pt"),
        is_oa=True,
        url=_str_or_none(doc.get("url")),
        abstract=str(doc.get("abstract") or "")[:500],
    )


def _authors(doc: dict[str, Any]) -> list[str]:
    raw = doc.get("author")
    if isinstance(raw, list):
        return [str(a) for a in raw if a]
    if isinstance(raw, str) and raw:
        return [raw]
    return []


def _venue(doc: dict[str, Any]) -> str | None:
    return _str_or_none(doc.get("source")) or _str_or_none(doc.get("journal_title"))


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
