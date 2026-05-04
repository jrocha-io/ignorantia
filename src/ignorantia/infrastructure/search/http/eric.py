"""``EricAdapter`` — Education Resources Information Center (ERIC).

Tier-1 source for education research; the API exposes a Solr-shaped JSON
endpoint and ERIC hosts full-text PDFs at ``files.eric.ed.gov`` for
peer-reviewed records.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient

_FIELDS = (
    "title,author,publicationdateyear,publicationtype,description,source,peerreviewed,id,url,issn"
)


class EricAdapter(AdapterPort):
    """Adapter for ERIC's ``api.ies.ed.gov/eric/`` endpoint."""

    source_id = "eric"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://api.ies.ed.gov/eric/"
    _PAGE_CAP: ClassVar[int] = 200

    def __init__(self, http: HttpClient, *, max_results: int = 200) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from ERIC (single request)."""
        url = self._build_url(query)
        body = self._http.get(url)
        docs = _parse_docs(body, self._max_results)
        items = tuple(_normalise(d, self.source_tier) for d in docs)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        search_q = query.text
        if query.year_start is not None and query.year_end is not None:
            search_q += f' AND publicationdateyear:["{query.year_start}" TO "{query.year_end}"]'
        params: dict[str, str] = {
            "search": search_q,
            "format": "json",
            "rows": str(min(self._max_results, self._PAGE_CAP)),
            "start": "0",
            "fields": _FIELDS,
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_docs(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    response = payload.get("response")
    if not isinstance(response, dict):
        return []
    docs = response.get("docs") or []
    return [d for d in docs[:limit] if isinstance(d, dict)]


def _normalise(doc: dict[str, Any], tier: Tier) -> FetchedItem:
    eric_id = str(doc.get("id") or "")
    is_oa = doc.get("peerreviewed") == "T"
    return FetchedItem(
        title=str(doc.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(doc)),
        year=_safe_int(doc.get("publicationdateyear")),
        venue=_first_or_none(doc.get("source")),
        language="en",
        is_oa=is_oa,
        url=f"https://eric.ed.gov/?id={eric_id}" if eric_id else None,
        url_for_pdf=f"https://files.eric.ed.gov/fulltext/{eric_id}.pdf" if eric_id else None,
        abstract=str(doc.get("description") or "")[:500],
        publication_type=_str_or_none(doc.get("publicationtype")),
    )


def _authors(doc: dict[str, Any]) -> list[str]:
    raw = doc.get("author")
    if isinstance(raw, list):
        return [str(a) for a in raw if a]
    if isinstance(raw, str) and raw:
        return [raw]
    return []


def _first_or_none(value: object) -> str | None:
    if isinstance(value, list) and value:
        head = value[0]
        return str(head) if head else None
    if isinstance(value, str) and value:
        return value
    return None


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
