"""``ScienceDirectFullAdapter`` — Elsevier ScienceDirect via the API.

Tier-2 paywall. Uses the same Elsevier API key as
:class:`~ignorantia.infrastructure.search.http.scopus_full.ScopusFullAdapter`
(``ELSEVIER_API_KEY``) but a different endpoint and date-filter syntax.
The shared response shape (``search-results.entry``) means the parsing
helpers are duplicated between Scopus and ScienceDirect today; an
``_elsevier`` private base will be extracted when a third Elsevier
adapter (e.g. Embase) joins the registry.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from ignorantia.domain.search.entities import FetchedItem, SearchQuery
from ignorantia.domain.search.value_objects import Tier
from ignorantia.infrastructure.search.http._paywall import _PaywallAdapter


class ScienceDirectFullAdapter(_PaywallAdapter):
    """Adapter for Elsevier's ``api.elsevier.com/content/search/sciencedirect``."""

    source_id = "sciencedirect_full"
    source_tier = Tier.TIER2

    _API_URL: ClassVar[str] = "https://api.elsevier.com/content/search/sciencedirect"
    _PAGE_CAP: ClassVar[int] = 25

    def _key_search(self, query: SearchQuery) -> tuple[FetchedItem, ...]:
        url = self._build_url(query)
        body = self._http.get(url, headers={"X-ELS-APIKey": self._api_key or ""})
        entries = _parse_entries(body, self._max_results)
        return tuple(_normalise(e, self.source_tier) for e in entries)

    def _build_url(self, query: SearchQuery) -> str:
        params: dict[str, str] = {
            "query": query.text,
            "count": str(min(self._max_results, self._PAGE_CAP)),
        }
        if query.year_start is not None and query.year_end is not None:
            params["date"] = f"{query.year_start:04d}-{query.year_end:04d}"
        return f"{self._API_URL}?{urlencode(params)}"


def _parse_entries(body: bytes, limit: int) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    block = payload.get("search-results")
    if not isinstance(block, dict):
        return []
    raw = block.get("entry") or []
    return [e for e in raw[:limit] if isinstance(e, dict)]


def _normalise(entry: dict[str, Any], tier: Tier) -> FetchedItem:
    creator = entry.get("dc:creator")
    authors = (str(creator),) if isinstance(creator, str) and creator else ()
    return FetchedItem(
        title=str(entry.get("dc:title") or ""),
        source_tier=tier,
        authors=authors,
        year=_year_from_iso(entry.get("prism:coverDate")),
        doi=_str_or_none(entry.get("prism:doi")),
        issn=_str_or_none(entry.get("prism:issn")),
        venue=_str_or_none(entry.get("prism:publicationName")),
        language="en",
        is_oa=entry.get("openaccess") in {"1", 1},
        publication_type=_str_or_none(entry.get("pii")),
    )


def _year_from_iso(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
