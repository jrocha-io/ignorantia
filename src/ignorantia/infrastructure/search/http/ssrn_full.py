"""``SsrnFullAdapter`` — SSRN preprint metadata via OpenAlex.

SSRN has no public REST search API; full-text downloads require an
SSRN login. Metadata, however, is freely discoverable via OpenAlex
filtered by the SSRN source identifier ``S4306400573``. This adapter
delegates to OpenAlex with that fixed filter and tags results as
``Tier.TIER2`` because retrieving the actual papers still requires
manual download from SSRN.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class SsrnFullAdapter(AdapterPort):
    """Adapter for SSRN preprint metadata via OpenAlex source filter."""

    source_id = "ssrn_full"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.openalex.org/works"
    _SSRN_SOURCE_ID: ClassVar[str] = "S4306400573"
    _PAGE_CAP: ClassVar[int] = 100

    def __init__(self, http: HttpClient, *, max_results: int = 100) -> None:
        """Wire the adapter and cap the page size."""
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from OpenAlex restricted to SSRN-hosted works."""
        url = self._build_url(query)
        body = self._http.get(url)
        records = _parse_results(body, self._max_results)
        items = tuple(_normalise(r, self.source_tier) for r in records)
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=items,
        )

    def _build_url(self, query: SearchQuery) -> str:
        filter_value = f"primary_location.source.id:{self._SSRN_SOURCE_ID}"
        if query.year_start is not None and query.year_end is not None:
            filter_value += (
                f",from_publication_date:{query.year_start:04d}-01-01"
                f",to_publication_date:{query.year_end:04d}-12-31"
            )
        params: dict[str, str] = {
            "search": query.text,
            "filter": filter_value,
            "per-page": str(min(self._max_results, self._PAGE_CAP)),
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_results(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("results") or []
    return [r for r in raw[:limit] if isinstance(r, dict)]


def _normalise(record: dict[str, Any], tier: Tier) -> FetchedItem:
    primary = record.get("primary_location")
    primary_d: dict[str, Any] = primary if isinstance(primary, dict) else {}
    source = primary_d.get("source")
    source_d: dict[str, Any] = source if isinstance(source, dict) else {}
    open_access = record.get("open_access")
    oa_d: dict[str, Any] = open_access if isinstance(open_access, dict) else {}
    return FetchedItem(
        title=str(record.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(record))[:10],
        year=_safe_int(record.get("publication_year")),
        doi=_strip_doi_prefix(record.get("doi")),
        venue=_str_or_none(source_d.get("display_name")),
        language=_str_or_none(record.get("language")) or "en",
        is_oa=bool(oa_d.get("is_oa", False)),
        url=_str_or_none(record.get("doi")) or _str_or_none(record.get("id")),
        url_for_pdf=_str_or_none(primary_d.get("pdf_url")),
        publication_type=_str_or_none(record.get("type")),
    )


def _authors(record: dict[str, Any]) -> list[str]:
    raw = record.get("authorships") or []
    out: list[str] = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        author = a.get("author")
        if isinstance(author, dict) and author.get("display_name"):
            out.append(str(author["display_name"]))
    return out


def _strip_doi_prefix(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.removeprefix("https://doi.org/") or None


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
