"""``IeeeFullAdapter`` — IEEE Xplore Search API (paywall, tier 2).

Migrated from v2 ``search_ieee_full.py``. Inherits the KEY → PROXY
cascade from :class:`_PaywallAdapter`; PROXY mode is intentionally
unsupported (the institutional proxy returns HTML).
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class IeeeFullAdapter(_PaywallAdapter):
    """Adapter for IEEE Xplore's ``ieeexploreapi.ieee.org`` search endpoint."""

    source_id = "ieee_full"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
    _PAGE_CAP: ClassVar[int] = 200

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        url = self._build_url(query)
        body = self._http.get(url)
        articles = _parse_articles(body, self._max_results)
        return tuple(_normalise(a, self.source_tier) for a in articles)

    def _build_url(self, query: SearchQuery) -> str:
        params: dict[str, str] = {
            "querytext": query.text,
            "max_records": str(min(self._max_results, self._PAGE_CAP)),
            "format": "json",
            "apikey": self._api_key or "",
        }
        if query.year_start is not None:
            params["start_year"] = str(query.year_start)
        if query.year_end is not None:
            params["end_year"] = str(query.year_end)
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_articles(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    raw = payload.get("articles") or []
    return [a for a in raw[:limit] if isinstance(a, dict)]


def _normalise(article: dict[str, Any], tier: Tier) -> FetchedItem:
    is_oa = article.get("access_type") == "OPEN_ACCESS"
    return FetchedItem(
        title=str(article.get("title") or ""),
        source_tier=tier,
        authors=tuple(_authors(article)),
        year=_safe_int(article.get("publication_year")),
        doi=_str_or_none(article.get("doi")),
        issn=_str_or_none(article.get("issn")) or _str_or_none(article.get("isbn")),
        isbn=_str_or_none(article.get("isbn")),
        venue=_str_or_none(article.get("publication_title")),
        language="en",
        is_oa=is_oa,
        url=_str_or_none(article.get("html_url")),
        url_for_pdf=_str_or_none(article.get("pdf_url")),
        abstract=str(article.get("abstract") or "")[:500],
        publication_type=_str_or_none(article.get("content_type")),
    )


def _authors(article: dict[str, Any]) -> list[str]:
    block = article.get("authors")
    if not isinstance(block, dict):
        return []
    raw = block.get("authors") or []
    return [str(a.get("full_name")) for a in raw if isinstance(a, dict) and a.get("full_name")][:10]


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
