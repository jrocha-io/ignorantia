"""``EmbaseAdapter`` — Embase via Elsevier Embase API.

Tier-2 paywall. The Elsevier Embase API requires a key with an active
Embase subscription — separate from the Scopus/ScienceDirect license.
The adapter passes the key via ``X-ELS-APIKey`` and uses Emtree query
syntax with ``[year_start-year_end]/py`` for date filtering.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class EmbaseAdapter(_PaywallAdapter):
    """Adapter for Elsevier's ``api.elsevier.com/embase/article``."""

    source_id = "embase"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.elsevier.com/embase/article"
    _PAGE_CAP: ClassVar[int] = 25

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        url = self._build_url(query)
        body = self._http.get(
            url,
            headers={
                "X-ELS-APIKey": self._api_key or "",
                "Accept": "application/json",
            },
        )
        entries = _parse_entries(body, self._max_results)
        return tuple(_normalise(e, self.source_tier) for e in entries)

    def _build_url(self, query: SearchQuery) -> str:
        emtree = query.text
        if query.year_start is not None and query.year_end is not None:
            emtree = f"({query.text}) AND [{query.year_start}-{query.year_end}]/py"
        params: dict[str, str] = {
            "query": emtree,
            "count": str(min(self._max_results, self._PAGE_CAP)),
        }
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_entries(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    results = payload.get("results")
    raw = (results.get("article") or []) if isinstance(results, dict) else []
    return [e for e in raw[:limit] if isinstance(e, dict)]


def _normalise(entry: dict[str, Any], tier: Tier) -> FetchedItem:
    title_block = entry.get("titleAndAuthor")
    title = ""
    if isinstance(title_block, dict):
        title = str(title_block.get("title") or "")
    source = entry.get("source")
    src_d: dict[str, Any] = source if isinstance(source, dict) else {}
    return FetchedItem(
        title=title,
        source_tier=tier,
        authors=tuple(_authors(entry))[:10],
        year=_safe_int(entry.get("publicationYear")),
        doi=_str_or_none(entry.get("doi")),
        issn=_str_or_none(src_d.get("issn")),
        venue=_str_or_none(src_d.get("title")),
        language="en",
        is_oa=False,
        publication_type=_str_or_none(entry.get("publicationType")),
    )


def _authors(entry: dict[str, Any]) -> list[str]:
    raw = entry.get("authors") or []
    out: list[str] = []
    for a in raw:
        if isinstance(a, dict) and a.get("name"):
            out.append(str(a["name"]))
    return out


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
