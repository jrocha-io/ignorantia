"""``HalAdapter`` — French open-access archive HAL.

HAL (Hyper-Articles en Ligne) hosts French research output. The API is a
Solr endpoint with field-suffix conventions (``_s`` string, ``_i`` int,
``Y_i`` year integer). Migrated from v2 ``search_hal.py``.
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
    "title_s,authFullName_s,producedDateY_i,doiId_s,halId_s,"
    "uri_s,fileMain_s,journalTitle_s,docType_s,abstract_s,language_s"
)


class HalAdapter(AdapterPort):
    """Adapter for HAL's Solr ``/search/`` endpoint."""

    source_id = "hal"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://api.archives-ouvertes.fr/search/"

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from HAL (single request)."""
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
        params: dict[str, str | list[str]] = {
            "q": query.text,
            "wt": "json",
            "rows": str(min(self._max_results, 100)),
            "fl": _FIELDS,
        }
        if query.year_start is not None and query.year_end is not None:
            params["fq"] = [f"producedDateY_i:[{query.year_start} TO {query.year_end}]"]
        return f"{self._API_URL}?{urlencode(params, doseq=True)}"


def _parse_docs(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    response = payload.get("response")
    if not isinstance(response, dict):
        return []
    docs = response.get("docs") or []
    return [d for d in docs[:limit] if isinstance(d, dict)]


def _normalise(doc: dict[str, Any], tier: Tier) -> FetchedItem:
    pdf_url = _str_or_none(doc.get("fileMain_s"))
    return FetchedItem(
        title=_first(doc.get("title_s")),
        source_tier=tier,
        authors=tuple(_to_list(doc.get("authFullName_s"))),
        year=_safe_int(doc.get("producedDateY_i")),
        doi=_str_or_none(doc.get("doiId_s")),
        venue=_first_or_none(doc.get("journalTitle_s")),
        language=_first(doc.get("language_s")) or "fr",
        is_oa=pdf_url is not None,
        url=_str_or_none(doc.get("uri_s")),
        url_for_pdf=pdf_url,
        abstract=_first(doc.get("abstract_s"))[:500],
        publication_type=_str_or_none(doc.get("docType_s")),
    )


def _to_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str) and value:
        return [value]
    return []


def _first(value: object) -> str:
    if isinstance(value, list) and value:
        head = value[0]
        return str(head) if head else ""
    if isinstance(value, str):
        return value
    return ""


def _first_or_none(value: object) -> str | None:
    out = _first(value)
    return out or None


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
