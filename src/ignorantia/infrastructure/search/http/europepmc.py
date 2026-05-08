"""``EuropePmcAdapter`` — Europe PMC RESTful API.

Tier-1 source: most records expose full text via PMC. The API uses
Lucene-style queries with ``PUB_YEAR`` for date filtering.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class EuropePmcAdapter(AdapterPort):
    """Adapter for Europe PMC's ``/search`` endpoint."""

    source_id = "europepmc"
    source_tier = Tier.TIER1

    _API_URL: ClassVar[str] = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from Europe PMC (single request)."""
        url = self._build_url(query)
        body = self._http.get(url)
        records = _parse(body, self._max_results)
        items = tuple(_normalise(r, self.source_tier) for r in records)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        q_text = query.text
        if query.year_start is not None and query.year_end is not None:
            q_text = f"({q_text}) AND PUB_YEAR:[{query.year_start} TO {query.year_end}]"
        params: dict[str, str] = {
            "query": q_text,
            "format": "json",
            "pageSize": str(min(self._max_results, self._PAGE_CAP)),
            "resultType": "core",
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    result_list = payload.get("resultList")
    if not isinstance(result_list, dict):
        return []
    raw = result_list.get("result") or []
    return [r for r in raw[:limit] if isinstance(r, dict)]


def _normalise(record: dict[str, Any], tier: Tier) -> FetchedItem:
    pmcid = _str_or_none(record.get("pmcid"))
    pmid = _str_or_none(record.get("pmid"))
    return FetchedItem(
        title=str(record.get("title") or ""),
        source_tier=tier,
        authors=tuple(_split_authors(record.get("authorString"))),
        year=_safe_year(record.get("pubYear")),
        doi=_str_or_none(record.get("doi")),
        venue=_str_or_none(record.get("journalTitle")),
        language="en",
        is_oa=record.get("isOpenAccess") == "Y",
        url=_canonical_url(pmcid, pmid),
        url_for_pdf=_pdf_url(pmcid, pmid),
        abstract=str(record.get("abstractText") or "")[:500],
    )


def _split_authors(value: object) -> list[str]:
    if not isinstance(value, str):
        return []
    return [chunk.strip() for chunk in value.split(",") if chunk.strip()]


def _safe_year(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _canonical_url(pmcid: str | None, pmid: str | None) -> str | None:
    if pmcid:
        return f"https://europepmc.org/article/PMC/{pmcid}"
    if pmid:
        return f"https://europepmc.org/article/MED/{pmid}"
    return None


def _pdf_url(pmcid: str | None, pmid: str | None) -> str | None:
    return _canonical_url(pmcid, pmid)


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
