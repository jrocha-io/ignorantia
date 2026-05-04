"""``CrossrefAdapter`` — concrete :class:`AdapterPort` for Crossref.

Crossref is a Tier-2 metadata source (free metadata, full text varies by
publisher). This adapter migrates the v2 ``search_crossref.py`` script.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery, SearchResult
from ignorantia.domain.search.ports.adapter_port import AdapterPort
from ignorantia.domain.search.value_objects import Method, Tier
from ignorantia.infrastructure.http_client import HttpClient


class CrossrefAdapter(AdapterPort):
    """Adapter for Crossref's public ``/works`` endpoint."""

    source_id = "crossref"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.crossref.org/works"

    def __init__(
        self,
        http: HttpClient,
        *,
        max_per_page: int = 100,
        max_results: int = 500,
    ) -> None:
        """Wire the adapter and configure pagination."""
        if max_per_page <= 0:
            raise ValueError("max_per_page must be > 0")
        if max_results <= 0:
            raise ValueError("max_results must be > 0")
        self._http = http
        self._max_per_page = max_per_page
        self._max_results = max_results

    def fetch(self, query: SearchQuery) -> SearchResult:
        """Fetch ``query`` from Crossref with paginated GETs."""
        items: list[FetchedItem] = []
        offset = 0
        while offset < self._max_results:
            url = self._build_url(query, offset)
            body = self._http.get(url)
            page = _parse_page(body)
            if not page:
                break
            for raw in page:
                if len(items) >= self._max_results:
                    break
                items.append(_normalise(raw))
            if len(items) >= self._max_results:
                break
            if len(page) < self._max_per_page:
                break
            offset += self._max_per_page
        return SearchResult(
            source=self.source_id,
            source_tier=self.source_tier,
            method=Method.REAL,
            query=query,
            items=tuple(items),
        )

    def _build_url(self, query: SearchQuery, offset: int) -> str:
        params: dict[str, str] = {
            "query": query.text,
            "rows": str(self._max_per_page),
            "offset": str(offset),
        }
        if query.year_start is not None and query.year_end is not None:
            params["filter"] = (
                f"from-pub-date:{query.year_start:04d}-01-01,"
                f"until-pub-date:{query.year_end:04d}-12-31"
            )
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_page(body: bytes) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    message: dict[str, Any] = payload.get("message", {}) or {}
    items_raw = message.get("items") or []
    return [item for item in items_raw if isinstance(item, dict)]


def _normalise(raw: dict[str, Any]) -> FetchedItem:
    return FetchedItem(
        title=_first_or_empty(raw.get("title")),
        source_tier=Tier.TIER2,
        authors=tuple(_join_author(a) for a in (raw.get("author") or []) if _join_author(a)),
        year=_year_from_issued(raw.get("issued")),
        doi=raw.get("DOI") or None,
        venue=_first_or_none(raw.get("container-title")),
        language=(raw.get("language") or "en").lower()[:2] or "en",
        is_oa=_has_creative_commons_license(raw.get("license") or []),
        url=raw.get("URL") or None,
        abstract=raw.get("abstract") or "",
        publication_type=raw.get("type") or None,
    )


def _first_or_empty(value: object) -> str:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, str):
            return first
    return ""


def _first_or_none(value: object) -> str | None:
    first = _first_or_empty(value)
    return first or None


def _join_author(author: object) -> str:
    if not isinstance(author, dict):
        return ""
    given = str(author.get("given") or "")
    family = str(author.get("family") or "")
    return " ".join(part for part in (given, family) if part).strip()


def _year_from_issued(issued: object) -> int | None:
    if not isinstance(issued, dict):
        return None
    parts = issued.get("date-parts")
    if not isinstance(parts, list) or not parts:
        return None
    first = parts[0]
    if not isinstance(first, list) or not first:
        return None
    head = first[0]
    return int(head) if isinstance(head, int) else None


def _has_creative_commons_license(licenses: list[Any]) -> bool:
    for lic in licenses:
        if not isinstance(lic, dict):
            continue
        url = str(lic.get("URL") or "").lower()
        if "creativecommons" in url:
            return True
    return False
